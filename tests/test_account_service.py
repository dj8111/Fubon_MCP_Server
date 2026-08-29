from decimal import Decimal
import pytest
from fubon_account_mcp.adapters.mock import MockAccountAdapter
from fubon_account_mcp.services.portfolio_service import PortfolioService


def test_portfolio_service_mock():
    adapter = MockAccountAdapter()
    service = PortfolioService(adapter=adapter)

    # 1. 查詢庫存部位
    positions = service.get_positions()
    assert len(positions) == 3
    fubon_gold = [p for p in positions if p.symbol == "2881"][0]
    assert fubon_gold.display_name == "富邦金"
    assert fubon_gold.quantity_shares == 5000

    # 2. 未實現損益
    unrealized = service.get_unrealized_pnl()
    assert float(unrealized.total_unrealized_profit) > 0
    assert len(unrealized.details) == 3

    # 3. 交割款
    settle = service.get_settlements()
    assert float(settle.total_pending_payable) == 68200.00

    # 4. 銀行餘額與維持率
    bank = service.get_bank_balance()
    assert float(bank.available_balance) == 350000.00
    maint = service.get_maintenance_ratio()
    assert maint.is_safe is True

    # 5. 總覽與實質購買力
    summary = service.get_portfolio_summary()
    assert float(summary.total_market_value) > 900000.00
    # 購買力 = 350,000 - 68,200 = 281,800.00
    assert summary.buying_power == "281800.00"
