import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional
from fubon_common_contracts.models.portfolio import (
    AccountSnapshot,
    Position,
    SnapshotDiff,
    SnapshotPositionDiff,
)
from fubon_common_contracts.storage.db import DatabaseManager
from .portfolio_service import PortfolioService


class SnapshotService:
    """富邦帳戶 SQLite 本機快照管理服務"""

    def __init__(self, db: Optional[DatabaseManager] = None, portfolio_service: Optional[PortfolioService] = None):
        self.db = db or DatabaseManager()
        self.portfolio_service = portfolio_service or PortfolioService()

    def save_snapshot(self, note: Optional[str] = None, account_ref: Optional[str] = None) -> AccountSnapshot:
        summary = self.portfolio_service.get_portfolio_summary(account_ref=account_ref)
        snapshot_id = f"snap_{uuid.uuid4().hex[:12]}"
        created_at = datetime.now(timezone.utc).isoformat()

        with self.db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO portfolio_snapshots (
                    snapshot_id, account_ref, total_market_value, total_cost,
                    unrealized_pnl, unrealized_pnl_percent, position_count, note, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    snapshot_id,
                    summary.account_ref,
                    summary.total_market_value,
                    summary.total_cost,
                    summary.total_unrealized_pnl,
                    summary.total_unrealized_pnl_percent,
                    summary.position_count,
                    note,
                    created_at,
                ),
            )

            for pos in summary.positions:
                conn.execute(
                    """
                    INSERT INTO portfolio_positions (
                        snapshot_id, symbol, display_name, quantity_shares,
                        average_price, current_price, market_value, total_cost,
                        unrealized_pnl, unrealized_pnl_percent, weight_percent, position_type
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        snapshot_id,
                        pos.symbol,
                        pos.display_name,
                        pos.quantity_shares,
                        pos.average_price,
                        pos.current_price,
                        pos.market_value,
                        pos.total_cost,
                        pos.unrealized_pnl,
                        pos.unrealized_pnl_percent,
                        pos.weight_percent,
                        getattr(pos.position_type, "value", "STOCK"),
                    ),
                )
            conn.commit()

        return AccountSnapshot(
            snapshot_id=snapshot_id,
            account_ref=summary.account_ref,
            total_market_value=summary.total_market_value,
            total_cost=summary.total_cost,
            unrealized_pnl=summary.total_unrealized_pnl,
            unrealized_pnl_percent=summary.total_unrealized_pnl_percent,
            position_count=summary.position_count,
            note=note,
            positions=summary.positions,
            created_at=created_at,
        )

    def list_snapshots(self, limit: int = 10) -> List[Dict[str, Any]]:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT snapshot_id, account_ref, total_market_value, total_cost,
                       unrealized_pnl, unrealized_pnl_percent, position_count, note, created_at
                FROM portfolio_snapshots
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_snapshot(self, snapshot_id: str) -> Optional[AccountSnapshot]:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT snapshot_id, account_ref, total_market_value, total_cost,
                       unrealized_pnl, unrealized_pnl_percent, position_count, note, created_at
                FROM portfolio_snapshots
                WHERE snapshot_id = ?
                """,
                (snapshot_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None

            cursor.execute(
                """
                SELECT symbol, display_name, quantity_shares, average_price, current_price,
                       market_value, total_cost, unrealized_pnl, unrealized_pnl_percent, weight_percent
                FROM portfolio_positions
                WHERE snapshot_id = ?
                """,
                (snapshot_id,),
            )
            pos_rows = cursor.fetchall()
            positions = [
                Position(
                    symbol=r["symbol"],
                    display_name=r["display_name"] or r["symbol"],
                    quantity_shares=r["quantity_shares"],
                    available_shares=r["quantity_shares"],
                    average_price=r["average_price"],
                    current_price=r["current_price"],
                    market_value=r["market_value"],
                    total_cost=r["total_cost"],
                    unrealized_pnl=r["unrealized_pnl"],
                    unrealized_pnl_percent=r["unrealized_pnl_percent"],
                    weight_percent=r["weight_percent"],
                )
                for r in pos_rows
            ]

            return AccountSnapshot(
                snapshot_id=row["snapshot_id"],
                account_ref=row["account_ref"],
                total_market_value=row["total_market_value"],
                total_cost=row["total_cost"],
                unrealized_pnl=row["unrealized_pnl"],
                unrealized_pnl_percent=row["unrealized_pnl_percent"],
                position_count=row["position_count"],
                note=row["note"],
                positions=positions,
                created_at=row["created_at"],
            )

    def compare_snapshots(self, base_snapshot_id: str, target_snapshot_id: Optional[str] = None) -> SnapshotDiff:
        base = self.get_snapshot(base_snapshot_id)
        if not base:
            raise ValueError(f"Base snapshot '{base_snapshot_id}' not found")

        if target_snapshot_id:
            target = self.get_snapshot(target_snapshot_id)
            if not target:
                raise ValueError(f"Target snapshot '{target_snapshot_id}' not found")
        else:
            # 與當前即時帳戶比較
            cur_summary = self.portfolio_service.get_portfolio_summary()
            target = AccountSnapshot(
                snapshot_id="current_live",
                account_ref=cur_summary.account_ref,
                total_market_value=cur_summary.total_market_value,
                total_cost=cur_summary.total_cost,
                unrealized_pnl=cur_summary.total_unrealized_pnl,
                unrealized_pnl_percent=cur_summary.total_unrealized_pnl_percent,
                position_count=cur_summary.position_count,
                note="Current Live",
                positions=cur_summary.positions,
                created_at=datetime.now(timezone.utc).isoformat(),
            )

        base_map = {p.symbol: p for p in base.positions}
        target_map = {p.symbol: p for p in target.positions}
        all_symbols = sorted(set(base_map.keys()) | set(target_map.keys()))

        pos_diffs: List[SnapshotPositionDiff] = []
        for sym in all_symbols:
            b_pos = base_map.get(sym)
            t_pos = target_map.get(sym)
            name = (t_pos or b_pos).display_name
            b_qty = b_pos.quantity_shares if b_pos else 0
            t_qty = t_pos.quantity_shares if t_pos else 0
            b_pnl = Decimal(b_pos.unrealized_pnl) if b_pos else Decimal("0.00")
            t_pnl = Decimal(t_pos.unrealized_pnl) if t_pos else Decimal("0.00")

            pos_diffs.append(
                SnapshotPositionDiff(
                    symbol=sym,
                    name=name,
                    base_shares=b_qty,
                    target_shares=t_qty,
                    delta_shares=t_qty - b_qty,
                    base_unrealized_pnl=f"{b_pnl:.2f}",
                    target_unrealized_pnl=f"{t_pnl:.2f}",
                    delta_unrealized_pnl=f"{(t_pnl - b_pnl):.2f}",
                )
            )

        delta_mkt = Decimal(target.total_market_value) - Decimal(base.total_market_value)
        delta_cost = Decimal(target.total_cost) - Decimal(base.total_cost)
        delta_pnl = Decimal(target.unrealized_pnl) - Decimal(base.unrealized_pnl)

        return SnapshotDiff(
            base_snapshot_id=base.snapshot_id,
            target_snapshot_id=target.snapshot_id,
            base_created_at=base.created_at,
            target_created_at=target.created_at,
            delta_market_value=f"{delta_mkt:.2f}",
            delta_cost=f"{delta_cost:.2f}",
            delta_unrealized_pnl=f"{delta_pnl:.2f}",
            position_diffs=pos_diffs,
        )
