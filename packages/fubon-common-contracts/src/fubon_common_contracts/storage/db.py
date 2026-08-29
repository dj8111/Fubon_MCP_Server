import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional

SCHEMA_SQL = """
PRAGMA journal_mode = WAL;
PRAGMA busy_timeout = 5000;
PRAGMA synchronous = NORMAL;
PRAGMA foreign_keys = ON;

-- 帳務快照主表
CREATE TABLE IF NOT EXISTS portfolio_snapshots (
    snapshot_id TEXT PRIMARY KEY,
    account_ref TEXT NOT NULL,
    total_market_value TEXT NOT NULL,
    total_cost TEXT NOT NULL,
    unrealized_pnl TEXT NOT NULL,
    unrealized_pnl_percent TEXT NOT NULL,
    position_count INTEGER NOT NULL,
    note TEXT,
    created_at TEXT NOT NULL
);

-- 帳務持股部位明細表
CREATE TABLE IF NOT EXISTS portfolio_positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    display_name TEXT,
    quantity_shares INTEGER NOT NULL,
    average_price TEXT NOT NULL,
    current_price TEXT NOT NULL,
    market_value TEXT NOT NULL,
    total_cost TEXT NOT NULL,
    unrealized_pnl TEXT NOT NULL,
    unrealized_pnl_percent TEXT NOT NULL,
    weight_percent TEXT NOT NULL,
    position_type TEXT DEFAULT 'STOCK',
    FOREIGN KEY(snapshot_id) REFERENCES portfolio_snapshots(snapshot_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_pos_symbol ON portfolio_positions(symbol);
CREATE INDEX IF NOT EXISTS idx_pos_snapshot ON portfolio_positions(snapshot_id);

-- 行情條件監測表
CREATE TABLE IF NOT EXISTS market_monitors (
    monitor_id TEXT PRIMARY KEY,
    symbol TEXT NOT NULL,
    operator TEXT NOT NULL,
    trigger_price TEXT NOT NULL,
    market_session TEXT NOT NULL,
    status TEXT NOT NULL,
    cooldown_seconds INTEGER DEFAULT 60,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    last_triggered_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_mon_active ON market_monitors(symbol, status);

-- 條件觸發事件表記錄
CREATE TABLE IF NOT EXISTS trigger_events (
    trigger_event_id TEXT PRIMARY KEY,
    monitor_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    trigger_price TEXT NOT NULL,
    observed_price TEXT NOT NULL,
    market_time TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(monitor_id) REFERENCES market_monitors(monitor_id)
);

-- 交易草稿與確認紀錄
CREATE TABLE IF NOT EXISTS order_drafts (
    draft_id TEXT PRIMARY KEY,
    correlation_id TEXT NOT NULL,
    account_ref TEXT NOT NULL,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,
    quantity_shares INTEGER NOT NULL,
    market_session TEXT NOT NULL,
    price_type TEXT NOT NULL,
    limit_price TEXT,
    estimated_amount TEXT NOT NULL,
    time_in_force TEXT NOT NULL,
    draft_hash TEXT NOT NULL,
    otp_salt TEXT,
    otp_hash TEXT,
    otp_expires_at TEXT,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    confirmed_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_draft_corr ON order_drafts(correlation_id);

-- 委託執行與稽核日誌表
CREATE TABLE IF NOT EXISTS order_audit_logs (
    audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
    correlation_id TEXT NOT NULL,
    draft_id TEXT,
    client_order_id TEXT NOT NULL,
    broker_order_id TEXT,
    action TEXT NOT NULL,
    state_before TEXT,
    state_after TEXT NOT NULL,
    request_payload_masked TEXT,
    response_payload_masked TEXT,
    recorded_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_audit_order ON order_audit_logs(client_order_id);
"""


class DatabaseManager:
    """富邦 SQLite 本機資料庫管理器"""

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            default_dir = Path(os.environ.get("FUBON_DATA_DIR", "data"))
            default_dir.mkdir(parents=True, exist_ok=True)
            self.db_path = str(default_dir / "fubon_assistant.db")
        else:
            self.db_path = db_path
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        try:
            conn.executescript(SCHEMA_SQL)
            conn.commit()
        finally:
            conn.close()

    @contextmanager
    def get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(self.db_path, timeout=5.0)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
