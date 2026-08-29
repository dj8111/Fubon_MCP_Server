from typing import Any, Dict, List, Optional
from ..adapters.research_data_source import ResearchDataSource
from ..models.research_fact import (
    CompanyAnnouncement,
    CompanyNews,
    FinancialReport,
    PortfolioEventAnalysis,
    ScenarioImpact,
)


class ResearchService:
    """富邦公開研究與風險分析服務層"""

    def __init__(self, data_source: Optional[ResearchDataSource] = None):
        self.data_source = data_source or ResearchDataSource()

    def search_announcements(self, symbol: str, limit: int = 5) -> List[CompanyAnnouncement]:
        return self.data_source.search_announcements(symbol=symbol, limit=limit)

    def get_financial_report(self, symbol: str) -> Optional[FinancialReport]:
        return self.data_source.get_financial_report(symbol=symbol)

    def search_news(self, symbol: str, limit: int = 5) -> List[CompanyNews]:
        return self.data_source.search_news(symbol=symbol, limit=limit)

    def analyze_portfolio_events(self, symbols: List[str]) -> Dict[str, Any]:
        analysis = self.data_source.analyze_portfolio_events(symbols=symbols)
        return analysis.model_dump()

    def run_portfolio_scenario(self, scenario_type: str, symbols: List[str]) -> ScenarioImpact:
        return self.data_source.run_portfolio_scenario(scenario_type=scenario_type, symbols=symbols)

    def generate_research_report(self, symbol: str) -> Dict[str, Any]:
        ann = self.search_announcements(symbol=symbol, limit=3)
        fin = self.get_financial_report(symbol=symbol)
        news = self.search_news(symbol=symbol, limit=3)

        return {
            "symbol": symbol,
            "target_name": fin.company_name if fin else symbol,
            "announcements": [a.model_dump() for a in ann],
            "financials": fin.model_dump() if fin else None,
            "news": [n.model_dump() for n in news],
            "disclaimer": "【合規免責宣告】本報告僅供投資決策參考，不構成任何買賣有價證券之邀約或投資建議。投資人應獨立判斷並自負投資盈虧與風險。",
        }
