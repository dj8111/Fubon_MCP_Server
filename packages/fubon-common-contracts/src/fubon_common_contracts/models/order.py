from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from .enums import MarketSession, MarketType, OrderSide, OrderStatus, OrderType, TimeInForce


class RiskCheckResult(BaseModel):
    check_code: str
    result: str # "PASS" / "REJECT" / "WARNING"
    message: str


class OrderDraft(BaseModel):
    draft_id: str
    correlation_id: str
    account_ref: str
    symbol: str
    symbol_name: Optional[str] = None
    side: OrderSide
    quantity_shares: int
    market_session: MarketSession = MarketSession.REGULAR
    price_type: OrderType = OrderType.LIMIT
    limit_price: Optional[str] = None
    estimated_amount: str
    estimated_fee: str
    estimated_tax: str
    time_in_force: TimeInForce = TimeInForce.ROD
    market_type: MarketType = MarketType.COMMON
    user_def: Optional[str] = "FubonAI"
    trigger_event_id: Optional[str] = None
    risk_checks: List[RiskCheckResult] = Field(default_factory=list)
    draft_hash: str
    status: OrderStatus = OrderStatus.DRAFT_PENDING_APPROVAL
    created_at: str
    expires_at: str


class OTPChallenge(BaseModel):
    challenge_id: str
    draft_id: str
    draft_hash: str
    summary: str
    expires_in_seconds: int = 120
    expires_at: str
    _test_otp: Optional[str] = None # 僅供本機展示/除錯，MCP 回傳時需剃除


class OrderSubmissionResult(BaseModel):
    client_order_id: str
    draft_id: str
    broker_order_no: Optional[str] = None
    seq_no: Optional[str] = None
    status: OrderStatus
    submitted_at: str
    raw_response: Optional[Dict[str, Any]] = None


class ExecutionReport(BaseModel):
    broker_order_no: str
    symbol: str
    side: OrderSide
    order_price: str
    order_quantity: int
    filled_quantity: int
    filled_price: Optional[str] = None
    status: OrderStatus
    order_time: str
    updated_time: str
