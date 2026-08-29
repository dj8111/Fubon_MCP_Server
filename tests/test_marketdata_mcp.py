import gc
import os
import tempfile
import pytest
from fubon_common_contracts.models.enums import TriggerOperator
from fubon_common_contracts.storage.db import DatabaseManager
from fubon_marketdata_mcp.adapters.quote_provider import QuoteProvider
from fubon_marketdata_mcp.services.market_service import MarketService
from fubon_marketdata_mcp.services.monitor_engine import MonitorEngine


@pytest.fixture
def temp_db():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        db_path = os.path.join(tmpdir, "test_fubon_mkt.db")
        db = DatabaseManager(db_path=db_path)
        yield db
        gc.collect()


def test_marketdata_quote_and_book():
    provider = QuoteProvider()
    service = MarketService(quote_provider=provider)

    # 1. 查詢富邦金報價
    quote = service.get_stock_quote("2881")
    assert quote.symbol == "2881"
    assert quote.name == "富邦金"
    assert float(quote.last_price) > 0

    # 2. 查詢五檔
    book = service.get_order_book("2881")
    assert book["symbol"] == "2881"
    assert len(book["bids"]) == 5
    assert len(book["asks"]) == 5

    # 3. 查詢分 K 與逐筆
    trades = service.get_recent_trades("2881", limit=5)
    assert len(trades) == 5
    candles = service.get_intraday_candles("2881")
    assert len(candles) > 0


def test_monitor_engine_and_trigger(temp_db):
    provider = QuoteProvider()
    engine = MonitorEngine(db=temp_db, quote_provider=provider)
    service = MarketService(quote_provider=provider, monitor_engine=engine)

    # 1. 建立監測條件: 富邦金 >= 70.00 (當前價格 72.50)
    mon = service.create_price_monitor(
        symbol="2881",
        operator=TriggerOperator.GREATER_THAN_OR_EQUAL,
        trigger_price="70.00",
    )
    assert mon["status"] == "ACTIVE"
    assert mon["symbol"] == "2881"

    # 輪詢檢核是否觸發 (Mock 報價 72.50 >= 70.00)
    events = engine.check_monitors()
    assert len(events) == 1
    assert events[0].symbol == "2881"
    assert events[0].trigger_price == "70.00"

    # 2. 測試 CROSS_BELOW 跌破條件 (現價 72.50 元，設定跌破 75.00 元應觸發，跌破 60.00 元不應觸發)
    cross_down_mon = service.create_price_monitor(
        symbol="2881",
        operator=TriggerOperator.CROSS_BELOW,
        trigger_price="75.00",
    )
    down_events = engine.check_monitors()
    assert any(e.monitor_id == cross_down_mon["monitor_id"] for e in down_events)

    not_down_mon = service.create_price_monitor(
        symbol="2881",
        operator=TriggerOperator.CROSS_BELOW,
        trigger_price="60.00",
    )
    no_events = engine.check_monitors()
    assert not any(e.monitor_id == not_down_mon["monitor_id"] for e in no_events)

    # 查詢事件清單
    events_list = service.get_trigger_events()
    assert len(events_list) >= 2
