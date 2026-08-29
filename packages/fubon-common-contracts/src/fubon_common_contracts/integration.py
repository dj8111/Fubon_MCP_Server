import sys
import json
from decimal import Decimal
from typing import Any, Dict


def run_integration_health_check() -> Dict[str, Any]:
    """執行富邦 AI 投資助理全系統整合與健康診斷"""
    results = {
        "status": "HEALTHY",
        "system": "Fubon AI Investment Assistant (Fubon Neo API v2.2.9)",
        "checks": {}
    }

    # 1. 資料庫連線與 Schema 檢核
    try:
        from .storage.db import DatabaseManager
        db = DatabaseManager()
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in cursor.fetchall()]
            required = ["portfolio_snapshots", "portfolio_positions", "market_monitors", "trigger_events", "order_drafts", "order_audit_logs"]
            missing = [t for t in required if t not in tables]
            if missing:
                results["checks"]["database"] = {"status": "FAIL", "message": f"Missing tables: {missing}"}
                results["status"] = "DEGRADED"
            else:
                results["checks"]["database"] = {"status": "PASS", "tables": tables}
    except Exception as e:
        results["checks"]["database"] = {"status": "FAIL", "error": str(e)}
        results["status"] = "UNHEALTHY"

    # 2. 資料模型契約驗證
    try:
        from .models.enums import MarketSession, OrderSide, OrderType, TimeInForce
        from .models.envelope import StandardEnvelope
        from .models.portfolio import Position, PortfolioSummary
        from .models.symbol import StockQuote

        pos = Position(
            symbol="2881",
            display_name="富邦金",
            quantity_shares=2000,
            available_shares=2000,
            average_price="65.00",
            current_price="66.50",
            market_value="133000.00",
            total_cost="130000.00",
            unrealized_pnl="3000.00",
            unrealized_pnl_percent="2.31",
            weight_percent="100.00"
        )
        summary = PortfolioSummary(
            account_ref="9800***123",
            total_market_value="133000.00",
            total_cost="130000.00",
            total_unrealized_pnl="3000.00",
            total_unrealized_pnl_percent="2.31",
            position_count=1,
            positions=[pos],
            updated_at="2026-08-29T10:00:00Z"
        )
        env = StandardEnvelope.ok(summary.model_dump())
        results["checks"]["contracts"] = {"status": "PASS", "correlation_id": env.correlation_id}
    except Exception as e:
        results["checks"]["contracts"] = {"status": "FAIL", "error": str(e)}
        results["status"] = "UNHEALTHY"

    return results


def main():
    report = run_integration_health_check()
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if report["status"] == "UNHEALTHY":
        sys.exit(1)


if __name__ == "__main__":
    main()
