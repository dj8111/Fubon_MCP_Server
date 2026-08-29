import json
import pytest
from fubon_account_mcp.server import (
    get_account_positions,
    get_bank_balance,
    get_portfolio_summary,
    get_settlement_query,
)
from fubon_marketdata_mcp.server import (
    get_order_book,
    get_stock_quote,
)
from fubon_trading_mcp.server import (
    approve_order_draft,
    create_order_draft,
    get_buying_power,
    get_trading_status,
)
from fubon_research_mcp.server import (
    get_latest_financial_reports,
    search_company_announcements,
)


def test_mcp_account_tools():
    res = json.loads(get_account_positions())
    assert res["success"] is True
    assert len(res["data"]) == 3

    res_sum = json.loads(get_portfolio_summary())
    assert res_sum["success"] is True
    assert float(res_sum["data"]["total_market_value"]) > 0

    res_settle = json.loads(get_settlement_query())
    assert res_settle["success"] is True

    res_bank = json.loads(get_bank_balance())
    assert res_bank["success"] is True


def test_mcp_marketdata_tools():
    res = json.loads(get_stock_quote(symbol="2881"))
    assert res["success"] is True
    assert res["data"]["symbol"] == "2881"

    res_book = json.loads(get_order_book(symbol="2881"))
    assert res_book["success"] is True
    assert len(res_book["data"]["bids"]) == 5


def test_mcp_trading_tools():
    stat = json.loads(get_trading_status())
    assert stat["success"] is True
    assert stat["data"]["system_mode"] == "NORMAL_TRADING"

    pwr = json.loads(get_buying_power())
    assert pwr["success"] is True

    # 建立草稿
    draft_res = json.loads(create_order_draft(
        symbol="2881",
        side="BUY",
        quantity_shares=1000,
        limit_price="72.50",
    ))
    assert draft_res["success"] is True
    draft_id = draft_res["data"]["draft_id"]

    # 核准草稿 (驗證已移除 _test_otp 避免洩漏給 LLM)
    app_res = json.loads(approve_order_draft(draft_id=draft_id))
    assert app_res["success"] is True
    assert "_test_otp" not in app_res["data"]


def test_mcp_research_tools():
    ann = json.loads(search_company_announcements(symbol="2881"))
    assert ann["success"] is True
    assert len(ann["data"]) > 0

    fin = json.loads(get_latest_financial_reports(symbol="2881"))
    assert fin["success"] is True
    assert fin["data"]["symbol"] == "2881"
