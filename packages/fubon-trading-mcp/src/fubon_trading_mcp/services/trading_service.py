import os
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional
from fubon_common_contracts.models.enums import (
    MarketSession,
    MarketType,
    OrderSide,
    OrderStatus,
    OrderType,
    TimeInForce,
)
from fubon_common_contracts.models.order import (
    OTPChallenge,
    OrderDraft,
    OrderSubmissionResult,
    RiskCheckResult,
)
from fubon_common_contracts.storage.db import DatabaseManager
from fubon_account_mcp.services.portfolio_service import PortfolioService
from fubon_marketdata_mcp.services.market_service import MarketService
from ..adapters.base import TradingAdapter
from ..adapters.fubon_sdk_trading import FubonSdkTradingAdapter
from ..adapters.mock_trading import MockTradingAdapter
from ..risk.risk_engine import RiskEngine
from ..security.challenge import ChallengeManager
from ..security.kill_switch import KillSwitch


class TradingService:
    """富邦交易綜合服務 (嚴格執行硬性風控、6 碼 OTP 挑戰與草稿防竄改機制)"""

    def __init__(
        self,
        trading_adapter: Optional[TradingAdapter] = None,
        risk_engine: Optional[RiskEngine] = None,
        challenge_manager: Optional[ChallengeManager] = None,
        kill_switch: Optional[KillSwitch] = None,
        db: Optional[DatabaseManager] = None,
        portfolio_service: Optional[PortfolioService] = None,
        market_service: Optional[MarketService] = None,
    ):
        if trading_adapter is not None:
            self.adapter = trading_adapter
        else:
            use_real = os.environ.get("FUBON_USE_REAL_SDK", "false").lower() in ("true", "1")
            if use_real:
                try:
                    self.adapter = FubonSdkTradingAdapter()
                except Exception:
                    self.adapter = MockTradingAdapter()
            else:
                self.adapter = MockTradingAdapter()

        self.risk_engine = risk_engine or RiskEngine()
        self.challenge_manager = challenge_manager or ChallengeManager()
        self.kill_switch = kill_switch or KillSwitch()
        self.db = db or DatabaseManager()
        self.portfolio_service = portfolio_service or PortfolioService()
        self.market_service = market_service or MarketService()

    def get_status(self) -> Dict[str, Any]:
        risk_stat = self.risk_engine.get_risk_status()
        return {
            "kill_switch_active": self.kill_switch.is_active,
            "kill_switch_reason": self.kill_switch.reason,
            "kill_switch_activated_at": self.kill_switch.activated_at,
            "system_mode": "READ_ONLY" if self.kill_switch.is_active else "NORMAL_TRADING",
            "risk_engine": risk_stat,
        }

    def get_buying_power(self, account_ref: Optional[str] = None) -> Dict[str, Any]:
        summary = self.portfolio_service.get_portfolio_summary(account_ref=account_ref)
        settle = self.portfolio_service.get_settlements(account_ref=account_ref)
        bank = self.portfolio_service.get_bank_balance(account_ref=account_ref)

        return {
            "account_ref": summary.account_ref,
            "available_bank_balance": bank.available_balance,
            "pending_settlement_payable": settle.total_pending_payable,
            "net_buying_power": summary.buying_power,
            "settlement_details": {
                "t_zero": settle.t_zero.model_dump(),
                "t_one": settle.t_one.model_dump(),
                "t_two": settle.t_two.model_dump(),
            },
        }

    def create_order_draft(
        self,
        symbol: str,
        side: OrderSide,
        quantity_shares: int,
        price_type: OrderType = OrderType.LIMIT,
        limit_price: Optional[str] = None,
        market_session: MarketSession = MarketSession.REGULAR,
        time_in_force: TimeInForce = TimeInForce.ROD,
        trigger_event_id: Optional[str] = None,
        account_ref: str = "9800***123",
        user_def: str = "FubonAI",
    ) -> Dict[str, Any]:
        if self.kill_switch.is_active:
            raise RuntimeError(f"交易熔斷開關已啟動 ({self.kill_switch.reason})，系統目前處於唯讀狀態，禁止建立任何交易草稿")

        # 1. 取得行情資訊以供風控
        quote = self.market_service.get_stock_quote(symbol)
        ref_price = Decimal(quote.reference_price or quote.last_price)

        # 2. 取得現有部位以供賣出充足性檢核
        positions = self.portfolio_service.get_positions(account_ref=account_ref, symbol=symbol)
        avail_shares = positions[0].available_shares if positions else 0

        # 3. 取得目前未成交反向訂單
        open_orders = self.adapter.get_open_orders(account_ref=account_ref)

        # 4. 執行硬性風控
        risk_results = self.risk_engine.validate_order(
            symbol=symbol,
            side=side,
            quantity_shares=quantity_shares,
            price_type=price_type,
            limit_price=limit_price,
            market_session=market_session,
            reference_price=ref_price,
            available_shares=avail_shares,
            open_opposite_orders=open_orders,
        )

        has_rejection = any(r.result == "REJECT" for r in risk_results)
        if has_rejection:
            reject_reasons = [r.message for r in risk_results if r.result == "REJECT"]
            raise ValueError(f"交易風控檢核未通過: {'; '.join(reject_reasons)}")

        # 5. 計算預估金額、手續費與證交稅
        p_val = Decimal(limit_price) if (price_type == OrderType.LIMIT and limit_price) else ref_price
        est_amount = p_val * Decimal(quantity_shares)
        fee = (est_amount * Decimal("0.001425") * Decimal("0.6")).quantize(Decimal("1")) # 富邦 6 折預估
        fee = max(Decimal("20"), fee)
        tax = (est_amount * Decimal("0.003")).quantize(Decimal("1")) if side == OrderSide.SELL else Decimal("0")

        draft_id = f"draft_{uuid.uuid4().hex[:12]}"
        corr_id = str(uuid.uuid4())
        now_str = datetime.now(timezone.utc).isoformat()
        exp_str = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()

        # 計算 Draft Hash
        draft_hash = self.challenge_manager.calculate_draft_hash(
            draft_id=draft_id,
            account_ref=account_ref,
            symbol=symbol,
            side=side.value,
            quantity=quantity_shares,
            price=limit_price,
            session=market_session.value,
        )

        draft = OrderDraft(
            draft_id=draft_id,
            correlation_id=corr_id,
            account_ref=account_ref,
            symbol=symbol,
            symbol_name=quote.name,
            side=side,
            quantity_shares=quantity_shares,
            market_session=market_session,
            price_type=price_type,
            limit_price=limit_price,
            estimated_amount=f"{est_amount:.2f}",
            estimated_fee=f"{fee:.2f}",
            estimated_tax=f"{tax:.2f}",
            time_in_force=time_in_force,
            market_type=MarketType.COMMON if market_session == MarketSession.REGULAR else MarketType.ODD,
            user_def=user_def,
            trigger_event_id=trigger_event_id,
            risk_checks=risk_results,
            draft_hash=draft_hash,
            status=OrderStatus.DRAFT_PENDING_APPROVAL,
            created_at=now_str,
            expires_at=exp_str,
        )

        with self.db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO order_drafts (
                    draft_id, correlation_id, account_ref, symbol, side, quantity_shares,
                    market_session, price_type, limit_price, estimated_amount, time_in_force,
                    draft_hash, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    draft_id,
                    corr_id,
                    account_ref,
                    symbol,
                    side.value,
                    quantity_shares,
                    market_session.value,
                    price_type.value,
                    limit_price,
                    f"{est_amount:.2f}",
                    time_in_force.value,
                    draft_hash,
                    OrderStatus.DRAFT_PENDING_APPROVAL.value,
                    now_str,
                ),
            )
            conn.commit()

        return draft.model_dump()

    def approve_order_draft(self, draft_id: str) -> Dict[str, Any]:
        if self.kill_switch.is_active:
            raise RuntimeError("交易熔斷開關已啟動，禁止核准草稿")

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM order_drafts WHERE draft_id = ?", (draft_id,))
            row = cursor.fetchone()
            if not row:
                raise ValueError(f"查無交易草稿 {draft_id}")

            d = dict(row)
            if d["status"] != OrderStatus.DRAFT_PENDING_APPROVAL.value:
                raise ValueError(f"草稿狀態為 {d['status']}，無法再次發行 OTP 挑戰")

            otp, salt, exp_at = self.challenge_manager.generate_otp_challenge(draft_id, d["draft_hash"])

            conn.execute(
                """
                UPDATE order_drafts
                SET status = ?, otp_salt = ?, otp_hash = ?, otp_expires_at = ?
                WHERE draft_id = ?
                """,
                (
                    OrderStatus.CHALLENGE_ISSUED.value,
                    salt,
                    self.challenge_manager._active_challenges[draft_id]["otp_hash"],
                    exp_at,
                    draft_id,
                ),
            )
            conn.commit()

        # 本機控制台印出 OTP
        print(f"\n=======================================================")
        print(f"🔒 [富邦 AI 安全防護網] 本機 6 碼 OTP 授權挑戰碼")
        print(f"   草稿編號: {draft_id}")
        print(f"   交易內容: {d['side']} {d['symbol']} {d['quantity_shares']} 股 @ {d['limit_price'] or '市價'}")
        print(f"   預估金額: NT$ {Decimal(d['estimated_amount']):,.2f}")
        print(f"   👉 授權驗證碼 (120 秒內有效): 【 {otp} 】 👈")
        print(f"=======================================================\n")

        return {
            "challenge_id": f"chl_{uuid.uuid4().hex[:8]}",
            "draft_id": draft_id,
            "draft_hash": d["draft_hash"],
            "summary": f"{d['side']} {d['symbol']} {d['quantity_shares']} 股 @ {d['limit_price'] or '市價'} (預估 NT${Decimal(d['estimated_amount']):,.2f})",
            "expires_in_seconds": 120,
            "expires_at": exp_at,
            "_test_otp": otp, # 供測試或 GUI 內部讀取
        }

    def submit_confirmed_order(self, draft_id: str, draft_hash: str, user_otp: str) -> Dict[str, Any]:
        if self.kill_switch.is_active:
            raise RuntimeError("交易熔斷開關已啟動，禁止送出委託")

        # 1. 驗證 OTP 與 Hash
        ok, msg = self.challenge_manager.verify_otp(draft_id, draft_hash, user_otp)
        if not ok:
            raise ValueError(f"授權驗證失敗: {msg}")

        # 2. 讀取草稿並鎖定送出
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM order_drafts WHERE draft_id = ?", (draft_id,))
            row = cursor.fetchone()
            if not row:
                raise ValueError(f"查無草稿 {draft_id}")
            d = dict(row)

            # 3. 呼叫券商配接器下單
            sub_res = self.adapter.place_order(
                draft_id=draft_id,
                account_ref=d["account_ref"],
                symbol=d["symbol"],
                side=OrderSide(d["side"]),
                quantity_shares=d["quantity_shares"],
                price_type=OrderType(d["price_type"]),
                limit_price=d["limit_price"],
                market_session=MarketSession(d["market_session"]),
                time_in_force=TimeInForce(d["time_in_force"]),
            )

            now_str = datetime.now(timezone.utc).isoformat()
            conn.execute(
                "UPDATE order_drafts SET status = ?, confirmed_at = ? WHERE draft_id = ?",
                (OrderStatus.SUBMITTED_TO_BROKER.value, now_str, draft_id),
            )

            # 寫入審計日誌
            conn.execute(
                """
                INSERT INTO order_audit_logs (
                    correlation_id, draft_id, client_order_id, broker_order_id,
                    action, state_before, state_after, request_payload_masked, response_payload_masked, recorded_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    d["correlation_id"],
                    draft_id,
                    sub_res.client_order_id,
                    sub_res.broker_order_no,
                    "PLACE_ORDER",
                    OrderStatus.CHALLENGE_ISSUED.value,
                    OrderStatus.SUBMITTED_TO_BROKER.value,
                    f"SYMBOL={d['symbol']},SIDE={d['side']},QTY={d['quantity_shares']}",
                    f"ORDER_NO={sub_res.broker_order_no}",
                    now_str,
                ),
            )
            conn.commit()

        # 累加當日風控紀錄
        self.risk_engine.record_approved_order(Decimal(d["estimated_amount"]))

        return sub_res.model_dump()

    def cancel_order(self, client_order_id: str) -> Dict[str, Any]:
        return self.adapter.cancel_order(client_order_id=client_order_id)

    def reconcile_order(self, client_order_id: str) -> Dict[str, Any]:
        rep = self.adapter.reconcile_order(client_order_id=client_order_id)
        return rep.model_dump()

    def activate_kill_switch(self, reason: str) -> Dict[str, Any]:
        self.kill_switch.activate(reason=reason)
        return {
            "status": "ACTIVATED",
            "reason": reason,
            "activated_at": self.kill_switch.activated_at,
            "message": "富邦交易熔斷已生效，系統強制轉為 READ_ONLY 模式，拒絕所有新委託送單",
        }
