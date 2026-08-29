import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional
from fubon_common_contracts.models.enums import MarketSession, MonitorStatus, TriggerEventStatus, TriggerOperator
from fubon_common_contracts.models.market import MarketMonitor, TriggerEvent
from fubon_common_contracts.storage.db import DatabaseManager
from ..adapters.quote_provider import QuoteProvider


class MonitorEngine:
    """富邦價格穿越與條件監測引擎 (支援防抖動冷卻與自動過期檢核)"""

    def __init__(self, db: Optional[DatabaseManager] = None, quote_provider: Optional[QuoteProvider] = None):
        self.db = db or DatabaseManager()
        self.quote_provider = quote_provider or QuoteProvider()
        self._cooldowns: Dict[str, datetime] = {}

    def create_monitor(
        self,
        symbol: str,
        operator: TriggerOperator,
        trigger_price: str,
        market_session: MarketSession = MarketSession.REGULAR,
        expires_at: Optional[str] = None,
        cooldown_seconds: int = 60,
    ) -> MarketMonitor:
        monitor_id = f"mon_{uuid.uuid4().hex[:10]}"
        now_utc = datetime.now(timezone.utc)
        created_at = now_utc.isoformat()
        if not expires_at:
            expires_at = (now_utc + timedelta(days=1)).isoformat()

        with self.db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO market_monitors (
                    monitor_id, symbol, operator, trigger_price, market_session,
                    status, cooldown_seconds, created_at, expires_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    monitor_id,
                    symbol,
                    operator.value,
                    trigger_price,
                    market_session.value,
                    MonitorStatus.ACTIVE.value,
                    cooldown_seconds,
                    created_at,
                    expires_at,
                ),
            )
            conn.commit()

        return MarketMonitor(
            monitor_id=monitor_id,
            symbol=symbol,
            operator=operator,
            trigger_price=trigger_price,
            market_session=market_session,
            status=MonitorStatus.ACTIVE,
            cooldown_seconds=cooldown_seconds,
            created_at=created_at,
            expires_at=expires_at,
        )

    def set_monitor_status(self, monitor_id: str, status: str) -> Dict[str, Any]:
        with self.db.get_connection() as conn:
            conn.execute(
                "UPDATE market_monitors SET status = ? WHERE monitor_id = ?",
                (status, monitor_id),
            )
            conn.commit()
        return {"monitor_id": monitor_id, "status": status}

    def pause_monitor(self, monitor_id: str) -> Dict[str, Any]:
        return self.set_monitor_status(monitor_id, MonitorStatus.PAUSED.value)

    def resume_monitor(self, monitor_id: str) -> Dict[str, Any]:
        return self.set_monitor_status(monitor_id, MonitorStatus.ACTIVE.value)

    def cancel_monitor(self, monitor_id: str) -> Dict[str, Any]:
        return self.set_monitor_status(monitor_id, MonitorStatus.CANCELLED.value)

    def list_active_monitors(self) -> List[Dict[str, Any]]:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM market_monitors WHERE status = ? ORDER BY created_at DESC",
                (MonitorStatus.ACTIVE.value,),
            )
            return [dict(row) for row in cursor.fetchall()]

    def list_all_monitors(self) -> List[Dict[str, Any]]:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM market_monitors ORDER BY created_at DESC")
            return [dict(row) for row in cursor.fetchall()]

    def check_monitors(self) -> List[TriggerEvent]:
        """輪詢檢查當前所有運行中監測條件是否觸發 (含過期與防抖動機制)"""
        active = self.list_active_monitors()
        triggered_events: List[TriggerEvent] = []
        now_dt = datetime.now(timezone.utc)

        for mon in active:
            monitor_id = mon["monitor_id"]
            expires_at_str = mon.get("expires_at")
            cooldown_sec = mon.get("cooldown_seconds") or 60

            # 檢核是否已逾期失效
            if expires_at_str:
                try:
                    exp_dt = datetime.fromisoformat(expires_at_str)
                    if exp_dt.tzinfo is None:
                        exp_dt = exp_dt.replace(tzinfo=timezone.utc)
                    if now_dt > exp_dt:
                        self.set_monitor_status(monitor_id, MonitorStatus.EXPIRED.value)
                        continue
                except Exception:
                    pass

            # 防抖動冷卻檢查
            if monitor_id in self._cooldowns and now_dt < self._cooldowns[monitor_id]:
                continue  # 仍在冷卻期內，防抖動阻擋

            sym = mon["symbol"]
            quote = self.quote_provider.get_stock_quote(sym)
            cur_p = Decimal(quote.last_price)
            target_p = Decimal(mon["trigger_price"])
            op = mon["operator"]

            is_triggered = False
            if op in (
                TriggerOperator.GREATER_THAN_OR_EQUAL.value,
                TriggerOperator.CROSS_ABOVE.value,
                "GREATER_THAN_OR_EQUAL",
                "CROSS_ABOVE",
                "PRICE_CROSS_UP",
            ) and cur_p >= target_p:
                is_triggered = True
            elif op in (
                TriggerOperator.LESS_THAN_OR_EQUAL.value,
                TriggerOperator.CROSS_BELOW.value,
                "LESS_THAN_OR_EQUAL",
                "CROSS_BELOW",
                "PRICE_CROSS_DOWN",
            ) and cur_p <= target_p:
                is_triggered = True

            if is_triggered:
                event_id = f"trg_{uuid.uuid4().hex[:10]}"
                now_str = now_dt.isoformat()
                event = TriggerEvent(
                    trigger_event_id=event_id,
                    monitor_id=monitor_id,
                    symbol=sym,
                    trigger_price=str(target_p),
                    observed_price=str(cur_p),
                    market_time=quote.updated_at,
                    status=TriggerEventStatus.VALIDATED,
                    created_at=now_str,
                )

                with self.db.get_connection() as conn:
                    conn.execute(
                        """
                        INSERT INTO trigger_events (
                            trigger_event_id, monitor_id, symbol, trigger_price,
                            observed_price, market_time, status, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            event_id,
                            monitor_id,
                            sym,
                            str(target_p),
                            str(cur_p),
                            quote.updated_at,
                            TriggerEventStatus.VALIDATED.value,
                            now_str,
                        ),
                    )
                    conn.execute(
                        "UPDATE market_monitors SET status = ?, last_triggered_at = ? WHERE monitor_id = ?",
                        (MonitorStatus.TRIGGERED.value, now_str, monitor_id),
                    )
                    conn.commit()

                # 設定冷卻時間
                self._cooldowns[monitor_id] = now_dt + timedelta(seconds=cooldown_sec)
                triggered_events.append(event)

        return triggered_events

    def get_trigger_events(self, status: str = "VALIDATED", limit: int = 10) -> List[Dict[str, Any]]:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM trigger_events WHERE status = ? ORDER BY created_at DESC LIMIT ?",
                (status, limit),
            )
            return [dict(row) for row in cursor.fetchall()]
