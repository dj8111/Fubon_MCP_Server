from typing import Any, Dict, List, Optional
from fubon_common_contracts.models.enums import MarketSession, TriggerOperator
from fubon_common_contracts.models.market import MarketMonitor
from fubon_common_contracts.models.symbol import (
    Candle,
    OrderBook,
    RecentTrade,
    StockQuote,
)
from ..adapters.quote_provider import QuoteProvider
from .monitor_engine import MonitorEngine


class MarketService:
    """富邦即時行情與監測綜合服務層"""

    def __init__(self, quote_provider: Optional[QuoteProvider] = None, monitor_engine: Optional[MonitorEngine] = None):
        self.quote_provider = quote_provider or QuoteProvider()
        self.monitor_engine = monitor_engine or MonitorEngine(quote_provider=self.quote_provider)

    def get_stock_quote(self, symbol: str) -> StockQuote:
        return self.quote_provider.get_stock_quote(symbol)

    def get_order_book(self, symbol: str) -> Dict[str, Any]:
        book = self.quote_provider.get_order_book(symbol)
        return book.model_dump()

    def get_recent_trades(self, symbol: str, limit: int = 10) -> List[Dict[str, Any]]:
        trades = self.quote_provider.get_recent_trades(symbol, limit=limit)
        return [t.model_dump() for t in trades]

    def get_intraday_candles(self, symbol: str, timeframe: str = "1") -> List[Dict[str, Any]]:
        candles = self.quote_provider.get_intraday_candles(symbol, timeframe=timeframe)
        return [c.model_dump() for c in candles]

    def get_historical_candles(self, symbol: str, from_date: str, to_date: str) -> List[Dict[str, Any]]:
        candles = self.quote_provider.get_historical_candles(symbol, from_date=from_date, to_date=to_date)
        return [c.model_dump() for c in candles]

    def create_price_monitor(
        self,
        symbol: str,
        operator: TriggerOperator,
        trigger_price: str,
        market_session: MarketSession = MarketSession.REGULAR,
        expires_at: Optional[str] = None,
        cooldown_seconds: int = 60,
    ) -> Dict[str, Any]:
        mon = self.monitor_engine.create_monitor(
            symbol=symbol,
            operator=operator,
            trigger_price=trigger_price,
            market_session=market_session,
            expires_at=expires_at,
            cooldown_seconds=cooldown_seconds,
        )
        return mon.model_dump()

    def pause_price_monitor(self, monitor_id: str) -> Dict[str, Any]:
        return self.monitor_engine.pause_monitor(monitor_id)

    def resume_price_monitor(self, monitor_id: str) -> Dict[str, Any]:
        return self.monitor_engine.resume_monitor(monitor_id)

    def cancel_price_monitor(self, monitor_id: str) -> Dict[str, Any]:
        return self.monitor_engine.cancel_monitor(monitor_id)

    def list_active_monitors(self) -> List[Dict[str, Any]]:
        return self.monitor_engine.list_active_monitors()

    def list_all_monitors(self) -> List[Dict[str, Any]]:
        return self.monitor_engine.list_all_monitors()

    def get_trigger_events(self, status: str = "VALIDATED", limit: int = 10) -> List[Dict[str, Any]]:
        return self.monitor_engine.get_trigger_events(status=status, limit=limit)
