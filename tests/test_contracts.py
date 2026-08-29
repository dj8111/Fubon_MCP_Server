import pytest
from decimal import Decimal
from fubon_common_contracts.models.enums import (
    MarketSession,
    OrderSide,
    OrderStatus,
    OrderType,
    PositionType,
    TimeInForce,
    TriggerOperator,
)
from fubon_common_contracts.models.envelope import StandardEnvelope
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
from fubon_common_contracts.models.symbol import OrderBook, OrderBookLevel, StockQuote


def test_standard_envelope_ok():
    data = {"hello": "fubon"}
    env = StandardEnvelope.ok(data)
    assert env.success is True
    assert env.data == data
    assert env.error_code is None
    assert env.correlation_id is not None
    assert env.timestamp is not None


def test_standard_envelope_fail():
    env = StandardEnvelope.fail("ERR_CODE", "Something went wrong")
    assert env.success is False
    assert env.error_code == "ERR_CODE"
    assert env.error_message == "Something went wrong"
    assert env.data is None


def test_position_model():
    pos = Position(
        symbol="2881",
        display_name="富邦金",
        quantity_shares=2000,
        available_shares=2000,
        average_price="68.00",
        current_price="72.00",
        market_value="144000.00",
        total_cost="136000.00",
        unrealized_pnl="8000.00",
        unrealized_pnl_percent="5.88",
        weight_percent="100.00",
        position_type=PositionType.STOCK,
    )
    assert pos.symbol == "2881"
    assert pos.quantity_shares == 2000
    assert pos.unrealized_pnl == "8000.00"


def test_settlement_info_model():
    s = SettlementInfo(
        account_ref="9800***123",
        t_zero=SettlementItem(settle_date="0d", buy_amount="0", sell_amount="0", net_amount="0", description=""),
        t_one=SettlementItem(settle_date="1d", buy_amount="0", sell_amount="0", net_amount="0", description=""),
        t_two=SettlementItem(settle_date="2d", buy_amount="50000", sell_amount="0", net_amount="-50000", description=""),
        total_pending_payable="50000.00",
        total_pending_receivable="0.00",
    )
    assert s.total_pending_payable == "50000.00"
    assert s.t_two.net_amount == "-50000"
