import asyncio
from typing import Optional
from mcp.server import MCPServer
from fubon_common_contracts.models.enums import (
    MarketSession,
    OrderSide,
    OrderType,
    TimeInForce,
)
from fubon_common_contracts.models.envelope import StandardEnvelope
from .services.trading_service import TradingService

app = MCPServer("fubon-trading-mcp")
trading_service = TradingService()


@app.resource("fubon://trading/status")
def get_trading_status_resource() -> str:
    """富邦交易系統風控狀態、熔斷旗標與當日累計額度 (唯讀 Resource)"""
    status = trading_service.get_status()
    return StandardEnvelope.ok(status).model_dump_json(indent=2)


@app.tool()
def get_trading_status() -> str:
    """查詢富邦交易風控系統狀態 (包含 Kill Switch 與當日委託限額消耗)"""
    try:
        status = trading_service.get_status()
        env = StandardEnvelope.ok(status)
    except Exception as e:
        env = StandardEnvelope.fail("EXECUTION_ERROR", str(e))
    return env.model_dump_json(indent=2)


@app.tool()
def get_buying_power(
    account_ref: Optional[str] = None,
) -> str:
    """查詢當前帳戶之可用買進額度、銀行餘額與待交割款"""
    try:
        power = trading_service.get_buying_power(account_ref=account_ref)
        env = StandardEnvelope.ok(power)
    except Exception as e:
        env = StandardEnvelope.fail("EXECUTION_ERROR", str(e))
    return env.model_dump_json(indent=2)


@app.tool()
def create_order_draft(
    symbol: str,
    side: str,
    quantity_shares: int,
    price_type: str = "LIMIT",
    limit_price: Optional[str] = None,
    market_session: str = "REGULAR",
    time_in_force: str = "ROD",
    trigger_event_id: Optional[str] = None,
    account_ref: str = "9800***123",
) -> str:
    """建立待確認富邦交易草稿 (執行跳動單位、漲跌停、限額與反向自成交檢核)"""
    try:
        draft = trading_service.create_order_draft(
            symbol=symbol,
            side=OrderSide(side),
            quantity_shares=quantity_shares,
            price_type=OrderType(price_type),
            limit_price=limit_price,
            market_session=MarketSession(market_session),
            time_in_force=TimeInForce(time_in_force),
            trigger_event_id=trigger_event_id,
            account_ref=account_ref,
        )
        env = StandardEnvelope.ok(draft)
    except Exception as e:
        env = StandardEnvelope.fail("RISK_CHECK_FAILED", str(e))
    return env.model_dump_json(indent=2)


@app.tool()
def approve_order_draft(
    draft_id: str,
) -> str:
    """核准富邦交易草稿並產生本機 6 碼 OTP 挑戰 (OTP 僅顯示於本機控制台，不回傳 LLM)"""
    try:
        challenge = trading_service.approve_order_draft(draft_id=draft_id)
        # 移除 _test_otp 避免洩漏給 LLM
        safe_data = {k: v for k, v in challenge.items() if k != "_test_otp"}
        env = StandardEnvelope.ok(safe_data)
    except Exception as e:
        env = StandardEnvelope.fail("CHALLENGE_ERROR", str(e))
    return env.model_dump_json(indent=2)


@app.tool()
def submit_confirmed_order(
    draft_id: str,
    draft_hash: str,
    user_otp: str,
) -> str:
    """驗證本機 6 碼 OTP 與 Draft Hash，正式送出委託至富邦證券主機"""
    try:
        order_res = trading_service.submit_confirmed_order(
            draft_id=draft_id,
            draft_hash=draft_hash,
            user_otp=user_otp,
        )
        env = StandardEnvelope.ok(order_res)
    except Exception as e:
        env = StandardEnvelope.fail("SUBMISSION_FAILED", str(e))
    return env.model_dump_json(indent=2)


@app.tool()
def submit_order_cancellation(
    client_order_id: str,
) -> str:
    """送出富邦刪單請求"""
    try:
        res = trading_service.cancel_order(client_order_id=client_order_id)
        env = StandardEnvelope.ok(res)
    except Exception as e:
        env = StandardEnvelope.fail("CANCELLATION_FAILED", str(e))
    return env.model_dump_json(indent=2)


@app.tool()
def reconcile_order(
    client_order_id: str,
) -> str:
    """對單筆未知狀態或待確認之委託單向富邦券商主機執行同步對帳"""
    try:
        res = trading_service.reconcile_order(client_order_id=client_order_id)
        env = StandardEnvelope.ok(res)
    except Exception as e:
        env = StandardEnvelope.fail("RECONCILIATION_ERROR", str(e))
    return env.model_dump_json(indent=2)


@app.tool()
def activate_kill_switch(
    reason: str,
) -> str:
    """緊急啟動富邦交易熔斷開關 (立刻拒絕所有新送單，系統強制轉為 READ_ONLY)"""
    try:
        res = trading_service.activate_kill_switch(reason=reason)
        env = StandardEnvelope.ok(res)
    except Exception as e:
        env = StandardEnvelope.fail("EXECUTION_ERROR", str(e))
    return env.model_dump_json(indent=2)


async def main():
    await app.run_stdio_async()


def run():
    asyncio.run(main())


if __name__ == "__main__":
    run()
