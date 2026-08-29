import gc
import os
import tempfile
import pytest
from decimal import Decimal
from fubon_common_contracts.models.enums import (
    MarketSession,
    OrderSide,
    OrderStatus,
    OrderType,
    TimeInForce,
)
from fubon_common_contracts.storage.db import DatabaseManager
from fubon_account_mcp.adapters.mock import MockAccountAdapter
from fubon_account_mcp.services.portfolio_service import PortfolioService
from fubon_marketdata_mcp.adapters.quote_provider import QuoteProvider
from fubon_marketdata_mcp.services.market_service import MarketService
from fubon_trading_mcp.adapters.mock_trading import MockTradingAdapter
from fubon_trading_mcp.risk.risk_engine import RiskEngine
from fubon_trading_mcp.security.challenge import ChallengeManager
from fubon_trading_mcp.security.kill_switch import KillSwitch
from fubon_trading_mcp.services.trading_service import TradingService


@pytest.fixture
def test_setup():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        db_path = os.path.join(tmpdir, "test_trading.db")
        db = DatabaseManager(db_path=db_path)
        mock_acc = MockAccountAdapter()
        port_service = PortfolioService(adapter=mock_acc)
        mkt_provider = QuoteProvider()
        mkt_service = MarketService(quote_provider=mkt_provider)
        trading_adapter = MockTradingAdapter()
        risk_engine = RiskEngine()
        challenge_manager = ChallengeManager(expires_in_seconds=120)
        kill_switch = KillSwitch()
        kill_switch.reset()

        service = TradingService(
            trading_adapter=trading_adapter,
            risk_engine=risk_engine,
            challenge_manager=challenge_manager,
            kill_switch=kill_switch,
            db=db,
            portfolio_service=port_service,
            market_service=mkt_service,
        )
        yield service, kill_switch, challenge_manager
        gc.collect()


def test_full_order_flow_with_otp(test_setup):
    service, kill_switch, challenge_manager = test_setup

    # 1. 建立委託草稿: 買進富邦金 1 張 (1,000 股) 限價 72.50
    draft = service.create_order_draft(
        symbol="2881",
        side=OrderSide.BUY,
        quantity_shares=1000,
        price_type=OrderType.LIMIT,
        limit_price="72.50",
        market_session=MarketSession.REGULAR,
        time_in_force=TimeInForce.ROD,
    )
    assert draft["draft_id"] is not None
    assert draft["status"] == OrderStatus.DRAFT_PENDING_APPROVAL.value
    assert draft["symbol"] == "2881"

    # 2. 核准草稿並產生 OTP 挑戰
    challenge = service.approve_order_draft(draft["draft_id"])
    assert challenge["draft_id"] == draft["draft_id"]
    otp = challenge["_test_otp"]
    assert len(otp) == 6

    # 3. 送出確認委託 (驗證 OTP 與 Hash)
    order_res = service.submit_confirmed_order(
        draft_id=draft["draft_id"],
        draft_hash=challenge["draft_hash"],
        user_otp=otp,
    )
    assert order_res["status"] == OrderStatus.SUBMITTED_TO_BROKER.value
    assert order_res["broker_order_no"] is not None

    # 4. 委託同步對帳
    reconcile = service.reconcile_order(order_res["client_order_id"])
    assert reconcile["symbol"] == "2881"
    assert reconcile["order_quantity"] == 1000


def test_risk_rejection_tick_size(test_setup):
    service, _, _ = test_setup

    # 測試跳動單位錯誤 (72.50 元跳動為 0.10，不可為 72.55)
    with pytest.raises(ValueError, match="風控檢核未通過"):
        service.create_order_draft(
            symbol="2881",
            side=OrderSide.BUY,
            quantity_shares=1000,
            price_type=OrderType.LIMIT,
            limit_price="72.55", # 錯誤跳動單位
        )


def test_kill_switch_blocking(test_setup):
    service, kill_switch, _ = test_setup

    # 啟動熔斷
    service.activate_kill_switch(reason="行情異常波動緊急熔斷")
    assert kill_switch.is_active is True

    # 嘗試下單草稿應被攔截
    with pytest.raises(RuntimeError, match="交易熔斷開關已啟動"):
        service.create_order_draft(
            symbol="2881",
            side=OrderSide.BUY,
            quantity_shares=1000,
            price_type=OrderType.LIMIT,
            limit_price="72.50",
        )
