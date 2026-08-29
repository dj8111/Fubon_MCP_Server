from typing import Optional
from pydantic import BaseModel
from .enums import MarketSession, MonitorStatus, TriggerEventStatus, TriggerOperator


class MarketMonitor(BaseModel):
    monitor_id: str
    symbol: str
    operator: TriggerOperator
    trigger_price: str
    market_session: MarketSession = MarketSession.REGULAR
    status: MonitorStatus = MonitorStatus.ACTIVE
    cooldown_seconds: int = 60
    created_at: str
    expires_at: str
    last_triggered_at: Optional[str] = None


class TriggerEvent(BaseModel):
    trigger_event_id: str
    monitor_id: str
    symbol: str
    trigger_price: str
    observed_price: str
    market_time: str
    status: TriggerEventStatus = TriggerEventStatus.VALIDATED
    created_at: str
