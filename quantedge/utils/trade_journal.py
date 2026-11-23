# utils/trade_journal.py
import os
import sqlite3
from datetime import datetime, timezone

SCHEMA = """
CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    mode TEXT NOT NULL,
    symbol TEXT NOT NULL,
    direction INTEGER NOT NULL,
    entry_price REAL,
    exit_price REAL,
    lot_size REAL,
    position_size_usd REAL,
    confidence REAL,
    regime TEXT,
    news_driven INTEGER DEFAULT 0,
    reason TEXT,
    pnl_usd REAL
);
CREATE INDEX IF NOT EXISTS idx_trades_symbol_ts ON trades(symbol, ts);
"""


class TradeJournal:
    """
    Persistent SQLite trade log (shadow and live modes).

    Replaces ad-hoc JSON session logs: trades accumulate into one queryable
    history with entry conditions attached, so shadow-mode results can be
    analyzed across sessions.
    """

    def __init__(self, db_path: str = "data/journal.db"):
        directory = os.path.dirname(db_path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def log_trade(
        self,
        symbol: str,
        direction: int,
        mode: str = "shadow",
        entry_price: float = None,
        exit_price: float = None,
        lot_size: float = None,
        position_size_usd: float = None,
        confidence: float = None,
        regime: str = None,
        news_driven: bool = False,
        reason: str = None,
    ) -> int:
        cursor = self.conn.execute(
            """
            INSERT INTO trades (
                ts, mode, symbol, direction, entry_price, exit_price,
                lot_size, position_size_usd, confidence, regime,
                news_driven, reason
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.now(timezone.utc).isoformat(),
                mode,
                symbol,
                int(direction),
                entry_price,
                exit_price,
                lot_size,
                position_size_usd,
                confidence,
                regime,
                int(bool(news_driven)),
                reason,
            ),
        )
        self.conn.commit()
        return cursor.lastrowid

    def close_trade(self, trade_id: int, exit_price: float = None, pnl_usd: float = None):
        self.conn.execute(
            """
            UPDATE trades
            SET exit_price = COALESCE(?, exit_price),
                pnl_usd = COALESCE(?, pnl_usd)
            WHERE id = ?
            """,
            (exit_price, pnl_usd, trade_id),
        )
        self.conn.commit()

    def get_trades(self, symbol: str = None, mode: str = None, limit: int = 500):
        query = "SELECT * FROM trades"
        conditions = []
        params = []
        if symbol:
            conditions.append("symbol = ?")
            params.append(symbol)
        if mode:
            conditions.append("mode = ?")
            params.append(mode)
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY ts DESC LIMIT ?"
        params.append(limit)
        cursor = self.conn.execute(query, params)
        columns = [d[0] for d in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def summary(self) -> dict:
        row = self.conn.execute(
            """
            SELECT COUNT(*),
                   AVG(CASE WHEN pnl_usd > 0 THEN 1.0 ELSE 0.0 END),
                   SUM(pnl_usd)
            FROM trades
            WHERE pnl_usd IS NOT NULL
            """
        ).fetchone()
        total = self.conn.execute("SELECT COUNT(*) FROM trades").fetchone()[0]
        return {
            "total_trades": int(total),
            "closed_trades": int(row[0] or 0),
            "win_rate": float(row[1]) if row[1] is not None else None,
            "total_pnl_usd": float(row[2]) if row[2] is not None else 0.0,
        }

    def close(self):
        self.conn.close()
