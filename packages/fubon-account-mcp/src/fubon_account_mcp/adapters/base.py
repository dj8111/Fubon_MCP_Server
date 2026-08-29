from abc import ABC, abstractmethod
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


class AccountAdapter(ABC):
    """富邦帳務資料來源抽象介面"""

    @abstractmethod
    def get_positions(self, account_ref: Optional[str] = None, symbol: Optional[str] = None) -> List[Position]:
        pass

    @abstractmethod
    def get_unrealized_pnl(self, account_ref: Optional[str] = None, symbol: Optional[str] = None) -> UnrealizedPnL:
        pass

    @abstractmethod
    def get_realized_pnl(self, account_ref: Optional[str] = None, days: int = 30) -> RealizedPnL:
        pass

    @abstractmethod
    def get_settlements(self, account_ref: Optional[str] = None) -> SettlementInfo:
        pass

    @abstractmethod
    def get_bank_balance(self, account_ref: Optional[str] = None) -> BankBalance:
        pass

    @abstractmethod
    def get_maintenance_ratio(self, account_ref: Optional[str] = None) -> MaintenanceRatio:
        pass

    @abstractmethod
    def get_portfolio_summary(self, account_ref: Optional[str] = None) -> PortfolioSummary:
        pass
