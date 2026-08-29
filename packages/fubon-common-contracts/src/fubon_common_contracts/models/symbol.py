from typing import List, Optional
from pydantic import BaseModel, Field


class SymbolInfo(BaseModel):
    symbol: str
    name: str
    market: str = "TWSE" # TWSE, OTC, TAIFEX
    industry: Optional[str] = None
    reference_price: Optional[str] = None
    limit_up_price: Optional[str] = None
    limit_down_price: Optional[str] = None
    is_trading_day: bool = True


class OrderBookLevel(BaseModel):
    price: str
    size: int


class OrderBook(BaseModel):
    symbol: str
    bids: List[OrderBookLevel] = Field(default_factory=list) # 買進五檔
    asks: List[OrderBookLevel] = Field(default_factory=list) # 賣出五檔
    updated_at: str


class Candle(BaseModel):
    time: str
    open: str
    high: str
    low: str
    close: str
    volume: int


class RecentTrade(BaseModel):
    time: str
    price: str
    size: int
    trade_type: str # 內盤: "IN", 外盤: "OUT"


class StockQuote(BaseModel):
    symbol: str
    name: str
    last_price: str
    change: str
    change_percent: str
    open: str
    high: str
    low: str
    volume: int
    turnover: Optional[str] = None
    bid_price_1: Optional[str] = None
    bid_size_1: Optional[int] = None
    ask_price_1: Optional[str] = None
    ask_size_1: Optional[int] = None
    limit_up: Optional[str] = None
    limit_down: Optional[str] = None
    reference_price: Optional[str] = None
    updated_at: str
