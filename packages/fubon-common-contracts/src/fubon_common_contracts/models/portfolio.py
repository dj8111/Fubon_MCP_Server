from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from .enums import PositionType


class Position(BaseModel):
    symbol: str
    display_name: str
    quantity_shares: int
    available_shares: int
    average_price: str
    current_price: str
    market_value: str
    total_cost: str
    unrealized_pnl: str
    unrealized_pnl_percent: str
    weight_percent: str
    position_type: PositionType = PositionType.STOCK


class PortfolioSummary(BaseModel):
    account_ref: str
    total_market_value: str
    total_cost: str
    total_unrealized_pnl: str
    total_unrealized_pnl_percent: str
    realized_pnl_today: Optional[str] = "0.00"
    bank_balance: Optional[str] = None
    buying_power: Optional[str] = None
    pending_settlement_net: Optional[str] = None
    maintenance_ratio: Optional[str] = None
    position_count: int
    positions: List[Position] = Field(default_factory=list)
    updated_at: str


class UnrealizedPnL(BaseModel):
    account_ref: str
    total_cost: str
    total_market_value: str
    total_unrealized_profit: str
    total_pnl_rate: str
    details: List[Dict[str, Any]] = Field(default_factory=list)


class RealizedPnL(BaseModel):
    account_ref: str
    start_date: str
    end_date: str
    total_realized_profit: str
    total_buy_amount: str
    total_sell_amount: str
    total_trade_fee: str
    total_trade_tax: str
    details: List[Dict[str, Any]] = Field(default_factory=list)


class SettlementItem(BaseModel):
    settle_date: str # e.g. "0d", "1d", "2d" or ISO date
    buy_amount: str
    sell_amount: str
    net_amount: str # 正值表應收，負值表應付
    description: str


class SettlementInfo(BaseModel):
    account_ref: str
    t_zero: SettlementItem
    t_one: SettlementItem
    t_two: SettlementItem
    total_pending_payable: str # 待扣應付交割款總計
    total_pending_receivable: str # 待收交割款總計


class BankBalance(BaseModel):
    account_ref: str
    bank_code: str
    bank_account: str
    available_balance: str
    currency: str = "TWD"
    updated_at: str


class MaintenanceRatio(BaseModel):
    account_ref: str
    self_maintenance_ratio: str # 自行維持率 %
    full_maintenance_ratio: str # 整體維持率 %
    margin_buy_amount: str
    short_sell_amount: str
    collateral_value: str
    is_safe: bool # >= 130%


class AccountSnapshot(BaseModel):
    snapshot_id: str
    account_ref: str
    total_market_value: str
    total_cost: str
    unrealized_pnl: str
    unrealized_pnl_percent: str
    position_count: int
    note: Optional[str] = None
    positions: List[Position] = Field(default_factory=list)
    created_at: str


class SnapshotPositionDiff(BaseModel):
    symbol: str
    name: str
    base_shares: int
    target_shares: int
    delta_shares: int
    base_unrealized_pnl: str
    target_unrealized_pnl: str
    delta_unrealized_pnl: str


class SnapshotDiff(BaseModel):
    base_snapshot_id: str
    target_snapshot_id: str
    base_created_at: str
    target_created_at: str
    delta_market_value: str
    delta_cost: str
    delta_unrealized_pnl: str
    position_diffs: List[SnapshotPositionDiff]
