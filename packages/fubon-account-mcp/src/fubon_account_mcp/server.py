import asyncio
from typing import Optional
from mcp.server import MCPServer
from fubon_common_contracts.models.envelope import StandardEnvelope
from .services.portfolio_service import PortfolioService
from .services.snapshot_service import SnapshotService

app = MCPServer("fubon-account-mcp")
portfolio_service = PortfolioService()
snapshot_service = SnapshotService(portfolio_service=portfolio_service)


@app.resource("fubon://portfolio/summary")
def get_portfolio_summary_resource() -> str:
    """富邦帳戶當前持股部位、總成本、市值與損益快照摘要 (唯讀 Resource)"""
    summary = portfolio_service.get_portfolio_summary()
    return summary.model_dump_json(indent=2)


@app.tool()
def get_account_positions(
    account_ref: Optional[str] = None,
    symbol: Optional[str] = None,
) -> str:
    """查詢富邦帳戶庫存持股明細與即時損益"""
    try:
        positions = portfolio_service.get_positions(account_ref=account_ref, symbol=symbol)
        env = StandardEnvelope.ok([p.model_dump() for p in positions])
    except Exception as e:
        env = StandardEnvelope.fail("EXECUTION_ERROR", str(e))
    return env.model_dump_json(indent=2)


@app.tool()
def get_unrealized_profit_loss(
    account_ref: Optional[str] = None,
    symbol: Optional[str] = None,
) -> str:
    """查詢富邦帳戶或個股之未實現損益統計"""
    try:
        pnl = portfolio_service.get_unrealized_pnl(account_ref=account_ref, symbol=symbol)
        env = StandardEnvelope.ok(pnl.model_dump())
    except Exception as e:
        env = StandardEnvelope.fail("EXECUTION_ERROR", str(e))
    return env.model_dump_json(indent=2)


@app.tool()
def get_realized_profit_loss(
    account_ref: Optional[str] = None,
    days: int = 30,
) -> str:
    """查詢富邦帳戶歷史已實現損益統計"""
    try:
        pnl = portfolio_service.get_realized_pnl(account_ref=account_ref, days=days)
        env = StandardEnvelope.ok(pnl.model_dump())
    except Exception as e:
        env = StandardEnvelope.fail("EXECUTION_ERROR", str(e))
    return env.model_dump_json(indent=2)


@app.tool()
def get_settlement_query(
    account_ref: Optional[str] = None,
) -> str:
    """查詢富邦證券 T+0 / T+1 / T+2 待交割款與淨額明細"""
    try:
        settle = portfolio_service.get_settlements(account_ref=account_ref)
        env = StandardEnvelope.ok(settle.model_dump())
    except Exception as e:
        env = StandardEnvelope.fail("EXECUTION_ERROR", str(e))
    return env.model_dump_json(indent=2)


@app.tool()
def get_bank_balance(
    account_ref: Optional[str] = None,
) -> str:
    """查詢台北富邦銀行交割帳戶之可用餘額"""
    try:
        bal = portfolio_service.get_bank_balance(account_ref=account_ref)
        env = StandardEnvelope.ok(bal.model_dump())
    except Exception as e:
        env = StandardEnvelope.fail("EXECUTION_ERROR", str(e))
    return env.model_dump_json(indent=2)


@app.tool()
def get_maintenance_ratio(
    account_ref: Optional[str] = None,
) -> str:
    """查詢富邦信用交易與融資券維持率"""
    try:
        maint = portfolio_service.get_maintenance_ratio(account_ref=account_ref)
        env = StandardEnvelope.ok(maint.model_dump())
    except Exception as e:
        env = StandardEnvelope.fail("EXECUTION_ERROR", str(e))
    return env.model_dump_json(indent=2)


@app.tool()
def get_portfolio_summary(
    account_ref: Optional[str] = None,
) -> str:
    """查詢富邦投資組合資產總值、實質購買力、權重占比與整體損益"""
    try:
        summary = portfolio_service.get_portfolio_summary(account_ref=account_ref)
        env = StandardEnvelope.ok(summary.model_dump())
    except Exception as e:
        env = StandardEnvelope.fail("EXECUTION_ERROR", str(e))
    return env.model_dump_json(indent=2)


@app.tool()
def save_account_snapshot(
    note: Optional[str] = None,
    account_ref: Optional[str] = None,
) -> str:
    """將當前富邦帳戶庫存與損益存為本機 SQLite 快照"""
    try:
        snapshot = snapshot_service.save_snapshot(note=note, account_ref=account_ref)
        env = StandardEnvelope.ok(snapshot.model_dump())
    except Exception as e:
        env = StandardEnvelope.fail("EXECUTION_ERROR", str(e))
    return env.model_dump_json(indent=2)


@app.tool()
def compare_account_snapshots(
    base_snapshot_id: str,
    target_snapshot_id: Optional[str] = None,
) -> str:
    """比對兩個時間點之富邦帳戶庫存與未實現損益差異"""
    try:
        diff = snapshot_service.compare_snapshots(
            base_snapshot_id=base_snapshot_id,
            target_snapshot_id=target_snapshot_id,
        )
        env = StandardEnvelope.ok(diff.model_dump())
    except Exception as e:
        env = StandardEnvelope.fail("EXECUTION_ERROR", str(e))
    return env.model_dump_json(indent=2)


async def main():
    await app.run_stdio_async()


def run():
    asyncio.run(main())


if __name__ == "__main__":
    run()
