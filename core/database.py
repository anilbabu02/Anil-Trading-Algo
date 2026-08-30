import sqlite3
import os
import json
from pathlib import Path
from datetime import datetime, date
from typing import List, Optional, Dict, Any
from core.models import TradeRecord

class DatabaseLedger:
    def __init__(self, db_path: str = "data/ledger.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA cache_size=-64000;")
        conn.execute("PRAGMA temp_store=MEMORY;")
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id TEXT PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    strategy TEXT NOT NULL,
                    direction TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    entry_time TEXT NOT NULL,
                    exit_time TEXT NOT NULL,
                    entry_price REAL NOT NULL,
                    exit_price REAL NOT NULL,
                    exit_reason TEXT NOT NULL,
                    gross_pnl REAL NOT NULL,
                    charges REAL NOT NULL,
                    net_pnl REAL NOT NULL,
                    duration_minutes REAL NOT NULL,
                    broker TEXT NOT NULL
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS daily_pnl (
                    date TEXT PRIMARY KEY,
                    realized_pnl REAL NOT NULL DEFAULT 0.0,
                    trade_count INTEGER NOT NULL DEFAULT 0,
                    circuit_breaker_tripped INTEGER NOT NULL DEFAULT 0,
                    closing_capital REAL NOT NULL
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS audit_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    message TEXT NOT NULL,
                    details TEXT
                )
            """)

            # Performance Indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_exit_time ON trades(exit_time DESC);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_daily_pnl_date ON daily_pnl(date DESC);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_events(timestamp DESC);")
            conn.commit()

    def record_trade(self, trade: TradeRecord):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO trades (
                    id, symbol, strategy, direction, quantity,
                    entry_time, exit_time, entry_price, exit_price,
                    exit_reason, gross_pnl, charges, net_pnl,
                    duration_minutes, broker
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                trade.id,
                trade.symbol,
                trade.strategy.value if hasattr(trade.strategy, "value") else str(trade.strategy),
                trade.direction.value if hasattr(trade.direction, "value") else str(trade.direction),
                trade.quantity,
                trade.entry_time.isoformat(),
                trade.exit_time.isoformat(),
                trade.entry_price,
                trade.exit_price,
                trade.exit_reason,
                trade.gross_pnl,
                trade.charges,
                trade.net_pnl,
                trade.duration_minutes,
                trade.broker
            ))
            conn.commit()

    def get_all_trades(self, limit: int = 100) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM trades ORDER BY exit_time DESC LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_trades_by_date(self, date_str: str) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM trades WHERE substr(exit_time, 1, 10) = ? ORDER BY exit_time ASC
            """, (date_str,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_today_stats(self, target_date: Optional[date] = None) -> Dict[str, Any]:
        d_str = (target_date or date.today()).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    COUNT(*) as trade_count,
                    COALESCE(SUM(gross_pnl), 0.0) as gross_pnl,
                    COALESCE(SUM(charges), 0.0) as total_charges,
                    COALESCE(SUM(net_pnl), 0.0) as net_pnl,
                    COALESCE(SUM(CASE WHEN net_pnl > 0 THEN 1 ELSE 0 END), 0) as win_count
                FROM trades 
                WHERE substr(exit_time, 1, 10) = ?
            """, (d_str,))
            row = cursor.fetchone()
            stats = dict(row)
            stats["date"] = d_str
            return stats

    def log_event(self, event_type: str, message: str, details: Optional[Dict[str, Any]] = None):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO audit_events (timestamp, event_type, message, details)
                VALUES (?, ?, ?, ?)
            """, (
                datetime.now().isoformat(),
                event_type,
                message,
                json.dumps(details) if details else None
            ))
            conn.commit()

    def get_recent_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM audit_events ORDER BY id DESC LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
