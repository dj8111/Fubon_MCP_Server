from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional
from fubon_common_contracts.models.enums import PositionType
from fubon_common_contracts.models.portfolio import (
    BankBalance,
    MaintenanceRatio,
    PortfolioSummary,
    Position,
    RealizedPnL,
    SettlementInfo,
    SettlementItem,
    UnrealizedPnL,
)
from .base import AccountAdapter


class MockAccountAdapter(AccountAdapter):
    """富邦帳務高真模擬配接器 (適用於展示與離線模式)"""

    def __init__(self, account_ref: str = "9800***123"):
        self.default_account_ref = account_ref
        self._positions = [
            Position(
                symbol="2881",
                display_name="富邦金",
                quantity_shares=5000,
                available_shares=5000,
                average_price="68.20",
                current_price="72.50",
                market_value="362500.00",
                total_cost="341000.00",
                unrealized_pnl="21500.00",
                unrealized_pnl_percent="6.30",
                weight_percent="38.77",
                position_type=PositionType.STOCK,
            ),
            Position(
                symbol="2330",
                display_name="台積電",
                quantity_shares=500,
                available_shares=500,
                average_price="980.00",
                current_price="1015.00",
                market_value="507500.00",
                total_cost="490000.00",
                unrealized_pnl="17500.00",
                unrealized_pnl_percent="3.57",
                weight_percent="54.28",
                position_type=PositionType.STOCK,
            ),
            Position(
                symbol="0050",
                display_name="元大台灣50",
                quantity_shares=400,
                available_shares=400,
                average_price="160.00",
                current_price="162.50",
                market_value="65000.00",
                total_cost="64000.00",
                unrealized_pnl="1000.00",
                unrealized_pnl_percent="1.56",
                weight_percent="6.95",
                position_type=PositionType.STOCK,
            ),
        ]

    def get_positions(self, account_ref: Optional[str] = None, symbol: Optional[str] = None) -> List[Position]:
        if symbol:
            return [p for p in self._positions if p.symbol == symbol]
        return self._positions

    def get_unrealized_pnl(self, account_ref: Optional[str] = None, symbol: Optional[str] = None) -> UnrealizedPnL:
        positions = self.get_positions(account_ref=account_ref, symbol=symbol)
        tot_cost = sum(Decimal(p.total_cost) for p in positions)
        tot_mkt = sum(Decimal(p.market_value) for p in positions)
        tot_pnl = sum(Decimal(p.unrealized_pnl) for p in positions)
        rate = (tot_pnl / tot_cost * Decimal("100")) if tot_cost > 0 else Decimal("0.00")

        details = [
            {
                "symbol": p.symbol,
                "name": p.display_name,
                "quantity": p.quantity_shares,
                "cost_price": p.average_price,
                "last_price": p.current_price,
                "cost_amount": p.total_cost,
                "market_amount": p.market_value,
                "unrealized_profit": p.unrealized_pnl,
                "pnl_rate": p.unrealized_pnl_percent,
            }
            for p in positions
        ]

        return UnrealizedPnL(
            account_ref=account_ref or self.default_account_ref,
            total_cost=f"{tot_cost:.2f}",
            total_market_value=f"{tot_mkt:.2f}",
            total_unrealized_profit=f"{tot_pnl:.2f}",
            total_pnl_rate=f"{rate:.2f}",
            details=details,
        )

    def get_realized_pnl(self, account_ref: Optional[str] = None, days: int = 30) -> RealizedPnL:
        return RealizedPnL(
            account_ref=account_ref or self.default_account_ref,
            start_date="2026-08-01",
            end_date="2026-08-29",
            total_realized_profit="15800.00",
            total_buy_amount="250000.00",
            total_sell_amount="266200.00",
            total_trade_fee="356.00",
            total_trade_tax="798.00",
            details=[
                {
                    "trade_date": "2026-08-15",
                    "symbol": "2454",
                    "name": "聯發科",
                    "buy_sell": "Sell",
                    "quantity": 200,
                    "buy_price": "1200.00",
                    "sell_price": "1280.00",
                    "realized_profit": "15800.00",
                }
            ],
        )

    def get_settlements(self, account_ref: Optional[str] = None) -> SettlementInfo:
        return SettlementInfo(
            account_ref=account_ref or self.default_account_ref,
            t_zero=SettlementItem(
                settle_date="0d (當日)",
                buy_amount="0.00",
                sell_amount="0.00",
                net_amount="0.00",
                description="當日交易尚在撮合彙總",
            ),
            t_one=SettlementItem(
                settle_date="1d (T+1 待扣/收)",
                buy_amount="0.00",
                sell_amount="0.00",
                net_amount="0.00",
                description="無待交割款",
            ),
            t_two=SettlementItem(
                settle_date="2d (T+2 預定扣款)",
                buy_amount="68200.00",
                sell_amount="0.00",
                net_amount="-68200.00",
                description="買進富邦金 1 張應付交割款",
            ),
            total_pending_payable="68200.00",
            total_pending_receivable="0.00",
        )

    def get_bank_balance(self, account_ref: Optional[str] = None) -> BankBalance:
        return BankBalance(
            account_ref=account_ref or self.default_account_ref,
            bank_code="012", # 台北富邦銀行
            bank_account="012-0088998877",
            available_balance="350000.00",
            currency="TWD",
            updated_at=datetime.now(timezone.utc).isoformat(),
        )

    def get_maintenance_ratio(self, account_ref: Optional[str] = None) -> MaintenanceRatio:
        return MaintenanceRatio(
            account_ref=account_ref or self.default_account_ref,
            self_maintenance_ratio="185.50",
            full_maintenance_ratio="185.50",
            margin_buy_amount="0.00",
            short_sell_amount="0.00",
            collateral_value="935000.00",
            is_safe=True,
        )

    def get_portfolio_summary(self, account_ref: Optional[str] = None) -> PortfolioSummary:
        positions = self.get_positions(account_ref=account_ref)
        tot_cost = sum(Decimal(p.total_cost) for p in positions)
        tot_mkt = sum(Decimal(p.market_value) for p in positions)
        tot_pnl = sum(Decimal(p.unrealized_pnl) for p in positions)
        rate = (tot_pnl / tot_cost * Decimal("100")) if tot_cost > 0 else Decimal("0.00")

        bank = self.get_bank_balance(account_ref=account_ref)
        settle = self.get_settlements(account_ref=account_ref)
        maint = self.get_maintenance_ratio(account_ref=account_ref)

        # 購買力 = 銀行餘額 - 待交割應付款
        buying_power = Decimal(bank.available_balance) - Decimal(settle.total_pending_payable)

        return PortfolioSummary(
            account_ref=account_ref or self.default_account_ref,
            total_market_value=f"{tot_mkt:.2f}",
            total_cost=f"{tot_cost:.2f}",
            total_unrealized_pnl=f"{tot_pnl:.2f}",
            total_unrealized_pnl_percent=f"{rate:.2f}",
            realized_pnl_today="0.00",
            bank_balance=bank.available_balance,
            buying_power=f"{buying_power:.2f}",
            pending_settlement_net=f"-{settle.total_pending_payable}",
            maintenance_ratio=f"{maint.full_maintenance_ratio}%",
            position_count=len(positions),
            positions=positions,
            updated_at=datetime.now(timezone.utc).isoformat(),
        )
