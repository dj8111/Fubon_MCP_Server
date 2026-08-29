import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fubon_common_contracts.models.enums import (
    MarketSession,
    OrderSide,
    OrderStatus,
    OrderType,
    TimeInForce,
)
from fubon_common_contracts.models.order import ExecutionReport, OrderSubmissionResult
from .base import TradingAdapter


class MockTradingAdapter(TradingAdapter):
    """富邦交易高真模擬執行配接器"""

    def __init__(self):
        self._orders: Dict[str, Dict[str, Any]] = {}

    def place_order(
        self,
        draft_id: str,
        account_ref: str,
        symbol: str,
        side: OrderSide,
        quantity_shares: int,
        price_type: OrderType,
        limit_price: Optional[str],
        market_session: MarketSession,
        time_in_force: TimeInForce,
        user_def: Optional[str] = "FubonAI",
    ) -> OrderSubmissionResult:
        client_order_id = f"fubon_cli_{uuid.uuid4().hex[:10]}"
        broker_order_no = f"f{secrets_order_no()}"
        seq_no = f"0000{len(self._orders) + 1:07d}"
        now_str = datetime.now(timezone.utc).isoformat()

        order_data = {
            "client_order_id": client_order_id,
            "draft_id": draft_id,
            "broker_order_no": broker_order_no,
            "seq_no": seq_no,
            "account_ref": account_ref,
            "symbol": symbol,
            "side": side.value,
            "quantity_shares": quantity_shares,
            "price_type": price_type.value,
            "limit_price": limit_price,
            "market_session": market_session.value,
            "time_in_force": time_in_force.value,
            "user_def": user_def,
            "status": OrderStatus.SUBMITTED_TO_BROKER.value,
            "submitted_at": now_str,
            "filled_quantity": 0,
            "filled_price": None,
        }
        self._orders[client_order_id] = order_data

        return OrderSubmissionResult(
            client_order_id=client_order_id,
            draft_id=draft_id,
            broker_order_no=broker_order_no,
            seq_no=seq_no,
            status=OrderStatus.SUBMITTED_TO_BROKER,
            submitted_at=now_str,
            raw_response={"message": "富邦模擬撮合主機收單成功", "code": "000000"},
        )

    def cancel_order(self, client_order_id: str) -> Dict[str, Any]:
        if client_order_id not in self._orders:
            raise ValueError(f"委託單 {client_order_id} 不存在")
        order = self._orders[client_order_id]
        if order["status"] in (OrderStatus.FILLED.value, OrderStatus.CANCELLED.value):
            raise ValueError(f"委託單狀態為 {order['status']}，無法取消")

        order["status"] = OrderStatus.CANCELLED.value
        return {
            "client_order_id": client_order_id,
            "broker_order_no": order["broker_order_no"],
            "status": OrderStatus.CANCELLED.value,
            "message": "富邦證券主機已確認成功刪單",
        }

    def reconcile_order(self, client_order_id: str) -> ExecutionReport:
        if client_order_id not in self._orders:
            raise ValueError(f"委託單 {client_order_id} 不存在")
        order = self._orders[client_order_id]
        return ExecutionReport(
            broker_order_no=order["broker_order_no"],
            symbol=order["symbol"],
            side=OrderSide(order["side"]),
            order_price=order["limit_price"] or "市價",
            order_quantity=order["quantity_shares"],
            filled_quantity=order["filled_quantity"],
            filled_price=order["filled_price"],
            status=OrderStatus(order["status"]),
            order_time=order["submitted_at"],
            updated_time=datetime.now(timezone.utc).isoformat(),
        )

    def get_open_orders(self, account_ref: Optional[str] = None) -> List[Dict[str, Any]]:
        return [
            o for o in self._orders.values()
            if o["status"] in (OrderStatus.SUBMITTED_TO_BROKER.value, OrderStatus.ACKNOWLEDGED.value, OrderStatus.PARTIALLY_FILLED.value)
        ]


def secrets_order_no() -> str:
    import secrets
    chars = "ABCDEFGHJKLMNPQRSTUVWXYZ"
    return f"{secrets.choice(chars)}{secrets.randbelow(9000) + 1000}"
