from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class CompanyAnnouncement(BaseModel):
    symbol: str
    company_name: str
    date: str
    title: str
    content: str
    source: str = "公開資訊觀測站 (MOPS)"
    reliability_level: str = "HIGH"


class FinancialReport(BaseModel):
    symbol: str
    company_name: str
    period: str # e.g. "2026-Q2"
    eps: str
    gross_margin: str
    operating_margin: str
    net_margin: str
    roe: str
    debt_ratio: str
    revenue_yoy: str
    source: str = "富邦證券投顧與公開財報"


class CompanyNews(BaseModel):
    symbol: str
    title: str
    source: str
    published_at: str
    snippet: str
    sentiment: str # "POSITIVE" / "NEUTRAL" / "NEGATIVE"
    risk_factor: Optional[str] = None


class PortfolioEventAnalysis(BaseModel):
    symbols: List[str]
    has_dividend_coming: List[str]
    has_earnings_release: List[str]
    has_major_dispute: List[str]
    risk_summary: str


class ScenarioImpact(BaseModel):
    scenario_type: str # "RATE_HIKE", "TECH_CAPEX_EXPANSION", "GEOPOLITICAL_TENSION"
    symbols_impact: Dict[str, str]
    overall_recommendation: str
