import asyncio
from typing import Any, Dict, List, Optional
from mcp.server import MCPServer
from fubon_common_contracts.models.enums import MarketSession, TriggerOperator
from fubon_common_contracts.models.envelope import StandardEnvelope
from .services.market_service import MarketService

app = MCPServer("fubon-marketdata-mcp")
market_service = MarketService()


@app.resource("fubon://market/quote/{symbol}")
def get_quote_resource(symbol: str) -> str:
    """指定標的之即時行情與買賣五檔報價 (唯讀 Resource)"""
    quote = market_service.get_stock_quote(symbol)
    book = market_service.get_order_book(symbol)
    data = {
        "quote": quote.model_dump(),
        "order_book": book,
    }
    return StandardEnvelope.ok(data).model_dump_json(indent=2)


@app.resource("fubon://market/active-monitors")
def get_active_monitors_resource() -> str:
    """當前本機運行中之價格監測工作清單 (唯讀 Resource)"""
    monitors = market_service.list_active_monitors()
    return StandardEnvelope.ok(monitors).model_dump_json(indent=2)


@app.tool()
def get_stock_quote(
    symbol: str,
    market: str = "TWSE",
) -> str:
    """取得富邦臺股即時行情快照 (最新成交價、開高低、漲跌幅與成交量)"""
    try:
        quote = market_service.get_stock_quote(symbol)
        env = StandardEnvelope.ok(quote.model_dump())
    except Exception as e:
        env = StandardEnvelope.fail("EXECUTION_ERROR", str(e))
    return env.model_dump_json(indent=2)


@app.tool()
def get_order_book(
    symbol: str,
) -> str:
    """查詢即時五檔最佳買進與賣出申報價量 (五檔委託簿)"""
    try:
        book = market_service.get_order_book(symbol)
        env = StandardEnvelope.ok(book)
    except Exception as e:
        env = StandardEnvelope.fail("EXECUTION_ERROR", str(e))
    return env.model_dump_json(indent=2)


@app.tool()
def get_recent_trades(
    symbol: str,
    limit: int = 10,
) -> str:
    """查詢個股近期逐筆成交明細 (成交時間、價格、張數與內外盤註記)"""
    try:
        trades = market_service.get_recent_trades(symbol, limit=limit)
        env = StandardEnvelope.ok(trades)
    except Exception as e:
        env = StandardEnvelope.fail("EXECUTION_ERROR", str(e))
    return env.model_dump_json(indent=2)


@app.tool()
def get_intraday_candles(
    symbol: str,
    timeframe: str = "1",
) -> str:
    """查詢個股即時分 K 線走勢 (1分K/5分K)"""
    try:
        candles = market_service.get_intraday_candles(symbol, timeframe=timeframe)
        env = StandardEnvelope.ok(candles)
    except Exception as e:
        env = StandardEnvelope.fail("EXECUTION_ERROR", str(e))
    return env.model_dump_json(indent=2)


@app.tool()
def get_historical_candles(
    symbol: str,
    from_date: str = "2026-08-01",
    to_date: str = "2026-08-29",
) -> str:
    """查詢個股歷史日 K 線資料"""
    try:
        candles = market_service.get_historical_candles(symbol, from_date=from_date, to_date=to_date)
        env = StandardEnvelope.ok(candles)
    except Exception as e:
        env = StandardEnvelope.fail("EXECUTION_ERROR", str(e))
    return env.model_dump_json(indent=2)


@app.tool()
def create_price_monitor(
    symbol: str,
    operator: str,
    trigger_price: str,
    market_session: str = "REGULAR",
    expires_at: Optional[str] = None,
    cooldown_seconds: int = 60,
) -> str:
    """建立富邦價格條件監測工作 (支援大於等於、小於等於、價格穿越與防抖動冷卻)"""
    try:
        op = TriggerOperator(operator)
        session = MarketSession(market_session)
        monitor = market_service.create_price_monitor(
            symbol=symbol,
            operator=op,
            trigger_price=trigger_price,
            market_session=session,
            expires_at=expires_at,
            cooldown_seconds=cooldown_seconds,
        )
        env = StandardEnvelope.ok(monitor)
    except Exception as e:
        env = StandardEnvelope.fail("EXECUTION_ERROR", str(e))
    return env.model_dump_json(indent=2)


@app.tool()
def pause_price_monitor(
    monitor_id: str,
) -> str:
    """暫停指定之價格監測工作"""
    try:
        res = market_service.pause_price_monitor(monitor_id)
        env = StandardEnvelope.ok(res)
    except Exception as e:
        env = StandardEnvelope.fail("EXECUTION_ERROR", str(e))
    return env.model_dump_json(indent=2)


@app.tool()
def resume_price_monitor(
    monitor_id: str,
) -> str:
    """恢復已暫停之價格監測工作"""
    try:
        res = market_service.resume_price_monitor(monitor_id)
        env = StandardEnvelope.ok(res)
    except Exception as e:
        env = StandardEnvelope.fail("EXECUTION_ERROR", str(e))
    return env.model_dump_json(indent=2)


@app.tool()
def cancel_price_monitor(
    monitor_id: str,
) -> str:
    """取消或關閉指定的價格監測工作"""
    try:
        res = market_service.cancel_price_monitor(monitor_id)
        env = StandardEnvelope.ok(res)
    except Exception as e:
        env = StandardEnvelope.fail("EXECUTION_ERROR", str(e))
    return env.model_dump_json(indent=2)


@app.tool()
def get_trigger_events(
    status: str = "VALIDATED",
    limit: int = 10,
) -> str:
    """查詢富邦已觸發且尚未轉入交易草稿之行情條件事件清單"""
    try:
        events = market_service.get_trigger_events(status=status, limit=limit)
        env = StandardEnvelope.ok(events)
    except Exception as e:
        env = StandardEnvelope.fail("EXECUTION_ERROR", str(e))
    return env.model_dump_json(indent=2)


async def main():
    await app.run_stdio_async()


def run():
    asyncio.run(main())


if __name__ == "__main__":
    run()
