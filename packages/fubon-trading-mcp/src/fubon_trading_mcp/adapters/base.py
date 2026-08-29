from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from fubon_common_contracts.models.enums import MarketSession, OrderSide, OrderType, TimeInForce
from fubon_common_contracts.models.order import ExecutionReport, OrderSubmissionResult


class TradingAdapter(ABC):
    """富邦交易執行抽象介面"""

    @abstractmethod
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
        pass

    @abstractmethod
    def cancel_order(self, client_order_id: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    def reconcile_order(self, client_order_id: str) -> ExecutionReport:
        pass

    @abstractmethod
    def get_open_orders(self, account_ref: Optional[str] = None) -> List[Dict[str, Any]]:
        pass
