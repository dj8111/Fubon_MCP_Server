import os
from decimal import Decimal
from typing import Any, Dict, List, Optional
from fubon_common_contracts.models.portfolio import (
    BankBalance,
    MaintenanceRatio,
    PortfolioSummary,
    Position,
    RealizedPnL,
    SettlementInfo,
    UnrealizedPnL,
)
from ..adapters.base import AccountAdapter
from ..adapters.fubon_sdk import FubonSdkAccountAdapter
from ..adapters.mock import MockAccountAdapter


class PortfolioService:
    """富邦帳務資產服務層 (支援正式 SDK 與 Mock 雙模式切換)"""

    def __init__(self, adapter: Optional[AccountAdapter] = None):
        if adapter is not None:
            self.adapter = adapter
        else:
            use_real = os.environ.get("FUBON_USE_REAL_SDK", "false").lower() in ("true", "1")
            if use_real:
                try:
                    self.adapter = FubonSdkAccountAdapter()
                except Exception:
                    self.adapter = MockAccountAdapter()
            else:
                self.adapter = MockAccountAdapter()

    def get_positions(self, account_ref: Optional[str] = None, symbol: Optional[str] = None) -> List[Position]:
        return self.adapter.get_positions(account_ref=account_ref, symbol=symbol)

    def get_unrealized_pnl(self, account_ref: Optional[str] = None, symbol: Optional[str] = None) -> UnrealizedPnL:
        return self.adapter.get_unrealized_pnl(account_ref=account_ref, symbol=symbol)

    def get_realized_pnl(self, account_ref: Optional[str] = None, days: int = 30) -> RealizedPnL:
        return self.adapter.get_realized_pnl(account_ref=account_ref, days=days)

    def get_settlements(self, account_ref: Optional[str] = None) -> SettlementInfo:
        return self.adapter.get_settlements(account_ref=account_ref)

    def get_bank_balance(self, account_ref: Optional[str] = None) -> BankBalance:
        return self.adapter.get_bank_balance(account_ref=account_ref)

    def get_maintenance_ratio(self, account_ref: Optional[str] = None) -> MaintenanceRatio:
        return self.adapter.get_maintenance_ratio(account_ref=account_ref)

    def get_portfolio_summary(self, account_ref: Optional[str] = None) -> PortfolioSummary:
        return self.adapter.get_portfolio_summary(account_ref=account_ref)
