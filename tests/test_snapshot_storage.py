import gc
import os
import tempfile
import pytest
from fubon_common_contracts.storage.db import DatabaseManager
from fubon_account_mcp.adapters.mock import MockAccountAdapter
from fubon_account_mcp.services.portfolio_service import PortfolioService
from fubon_account_mcp.services.snapshot_service import SnapshotService


@pytest.fixture
def temp_db():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        db_path = os.path.join(tmpdir, "test_fubon.db")
        db = DatabaseManager(db_path=db_path)
        yield db
        gc.collect()


def test_snapshot_save_and_compare(temp_db):
    mock_adapter = MockAccountAdapter()
    portfolio_service = PortfolioService(adapter=mock_adapter)
    snapshot_service = SnapshotService(db=temp_db, portfolio_service=portfolio_service)

    # 1. 建立第一個快照
    snap1 = snapshot_service.save_snapshot(note="初次備份")
    assert snap1.snapshot_id is not None
    assert snap1.position_count == 3
    assert float(snap1.total_market_value) > 0

    # 2. 列出快照
    snaps = snapshot_service.list_snapshots()
    assert len(snaps) == 1
    assert snaps[0]["note"] == "初次備份"

    # 3. 取得單一快照
    snap_loaded = snapshot_service.get_snapshot(snap1.snapshot_id)
    assert snap_loaded is not None
    assert len(snap_loaded.positions) == 3

    # 4. 快照比對
    diff = snapshot_service.compare_snapshots(base_snapshot_id=snap1.snapshot_id)
    assert diff.base_snapshot_id == snap1.snapshot_id
    assert diff.target_snapshot_id == "current_live"
    assert len(diff.position_diffs) == 3
