import json
import pytest
from fubon_common_contracts.integration import run_integration_health_check
from fubon_account_mcp.services.portfolio_service import PortfolioService
from fubon_marketdata_mcp.services.market_service import MarketService
from fubon_trading_mcp.services.trading_service import TradingService
from fubon_research_mcp.services.research_service import ResearchService
from fubon_common_contracts.models.enums import OrderSide, OrderType


def test_system_integration_health_check():
    report = run_integration_health_check()
    assert report["status"] == "HEALTHY"
    assert report["checks"]["database"]["status"] == "PASS"
    assert report["checks"]["contracts"]["status"] == "PASS"


def test_full_ai_assistant_e2e_workflow():
    """
    全鏈路 E2E 整合測試：
    1. AI 查詢富邦帳戶庫存與交割款購買力 (Account MCP)
    2. AI 查詢公開資訊觀測站重大訊息與投顧財報 (Research MCP)
    3. AI 監測富邦金即時五檔行情 (MarketData MCP)
    4. 條件觸發後，建立交易草稿並由硬性風控檢核 (Trading MCP)
    5. 本機核准發行 OTP 挑戰 (OTP Challenge)
    6. 人類輸入 6 碼 OTP 完成下單送單 (Submission)
    7. 驗證對帳與快照存檔 (Reconciliation & Snapshot)
    """
    port_service = PortfolioService()
    mkt_service = MarketService()
    res_service = ResearchService()
    trading_service = TradingService(portfolio_service=port_service, market_service=mkt_service)

    # 1. 帳務與購買力
    summary = port_service.get_portfolio_summary()
    assert float(summary.total_market_value) > 0
    assert float(summary.buying_power) > 0

    # 2. 研究分析
    report = res_service.generate_research_report("2881")
    assert report["symbol"] == "2881"

    # 3. 行情查詢
    quote = mkt_service.get_stock_quote("2881")
    assert quote.symbol == "2881"

    # 4. 建立草稿
    draft = trading_service.create_order_draft(
        symbol="2881",
        side=OrderSide.BUY,
        quantity_shares=1000,
        limit_price="72.50",
    )
    assert draft["status"] == "DRAFT_PENDING_APPROVAL"
    draft_id = draft["draft_id"]

    # 5. 核准草稿取得 OTP
    challenge = trading_service.approve_order_draft(draft_id)
    otp = challenge["_test_otp"]

    # 6. 送出委託
    order_res = trading_service.submit_confirmed_order(
        draft_id=draft_id,
        draft_hash=challenge["draft_hash"],
        user_otp=otp,
    )
    assert order_res["status"] == "SUBMITTED_TO_BROKER"

    # 7. 對帳
    reconcile = trading_service.reconcile_order(order_res["client_order_id"])
    assert reconcile["symbol"] == "2881"
    assert reconcile["order_quantity"] == 1000
