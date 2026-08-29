import asyncio
from typing import List, Optional
from mcp.server import MCPServer
from fubon_common_contracts.models.envelope import StandardEnvelope
from .services.research_service import ResearchService

app = MCPServer("fubon-research-mcp")
research_service = ResearchService()


@app.prompt()
def analyze_stock_risk(symbol: str) -> str:
    """產生個股風險與重大訊息分析之標準 Prompt 模板"""
    return (
        f"請針對臺股標的 {symbol}，整合公開資訊觀測站之最新公告、富邦投顧財報獲利能力與財經新聞，"
        f"進行結構化風險剖析。請務必列出所有資料來源與可靠度評級，並嚴格遵循富邦證券合規免責宣告。"
    )


@app.tool()
def search_company_announcements(
    symbol: str,
    limit: int = 5,
) -> str:
    """查詢公開資訊觀測站 (MOPS) 之公司重大訊息與法定公告"""
    try:
        items = research_service.search_announcements(symbol=symbol, limit=limit)
        env = StandardEnvelope.ok([i.model_dump() for i in items])
    except Exception as e:
        env = StandardEnvelope.fail("EXECUTION_ERROR", str(e))
    return env.model_dump_json(indent=2)


@app.tool()
def get_latest_financial_reports(
    symbol: str,
) -> str:
    """查詢個股最新季報財務比率、毛利率、淨利率與每股盈餘 (EPS)"""
    try:
        report = research_service.get_financial_report(symbol=symbol)
        if report:
            env = StandardEnvelope.ok(report.model_dump())
        else:
            env = StandardEnvelope.fail("NOT_FOUND", f"查無 {symbol} 之最新財報資訊")
    except Exception as e:
        env = StandardEnvelope.fail("EXECUTION_ERROR", str(e))
    return env.model_dump_json(indent=2)


@app.tool()
def search_company_news(
    symbol: str,
    limit: int = 5,
) -> str:
    """查詢核准財經來源之個股最新新聞與市場情緒摘要 (經清洗過濾)"""
    try:
        news = research_service.search_news(symbol=symbol, limit=limit)
        env = StandardEnvelope.ok([n.model_dump() for n in news])
    except Exception as e:
        env = StandardEnvelope.fail("EXECUTION_ERROR", str(e))
    return env.model_dump_json(indent=2)


@app.tool()
def analyze_portfolio_events(
    symbols: List[str],
) -> str:
    """分析多檔持股近期是否有重大公告、除權息或事件集中度風險"""
    try:
        analysis = research_service.analyze_portfolio_events(symbols=symbols)
        env = StandardEnvelope.ok(analysis)
    except Exception as e:
        env = StandardEnvelope.fail("EXECUTION_ERROR", str(e))
    return env.model_dump_json(indent=2)


@app.tool()
def run_portfolio_scenario(
    scenario_type: str,
    symbols: Optional[List[str]] = None,
) -> str:
    """執行總體經濟或產業情境模擬 (如升息、全球科技資本支出擴張等)"""
    try:
        impact = research_service.run_portfolio_scenario(
            scenario_type=scenario_type,
            symbols=symbols or ["2881", "2330"],
        )
        env = StandardEnvelope.ok(impact.model_dump())
    except Exception as e:
        env = StandardEnvelope.fail("EXECUTION_ERROR", str(e))
    return env.model_dump_json(indent=2)


@app.tool()
def generate_portfolio_research_report(
    symbol: str,
) -> str:
    """產生包含官方公告、財報比率與富邦合規免責警語之完整研究報告"""
    try:
        report = research_service.generate_research_report(symbol=symbol)
        env = StandardEnvelope.ok(report)
    except Exception as e:
        env = StandardEnvelope.fail("EXECUTION_ERROR", str(e))
    return env.model_dump_json(indent=2)


async def main():
    await app.run_stdio_async()


def run():
    asyncio.run(main())


if __name__ == "__main__":
    run()
