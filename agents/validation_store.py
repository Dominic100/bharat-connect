import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any


class ValidationStore:
    """Simple SQLite-backed store for validation reports."""

    def __init__(self, db_path: str = "./data/validation_history.db"):
        self.db_file = Path(db_path)
        self.db_file.parent.mkdir(parents=True, exist_ok=True)
        # Use check_same_thread=False so different threads can share if needed
        self.conn = sqlite3.connect(str(self.db_file), timeout=30, check_same_thread=False)
        # Use WAL for safer concurrent reads/writes
        try:
            self.conn.execute("PRAGMA journal_mode=WAL;")
        except Exception:
            pass
        self._init_db()

    def _init_db(self):
        cur = self.conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS validations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                source TEXT NOT NULL,
                validator TEXT NOT NULL,
                valid INTEGER NOT NULL,
                quality_score REAL,
                run_id TEXT,
                report TEXT NOT NULL
            );
            """
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_validations_url ON validations(url);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_validations_ts ON validations(timestamp);")
        self.conn.commit()

    def save_report(self,
                    url: str,
                    source: str,
                    validator: str,
                    valid: bool,
                    report: Dict[str, Any],
                    quality_score: Optional[float] = None,
                    run_id: Optional[str] = None) -> int:
        ts = datetime.utcnow().isoformat()
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO validations (url, timestamp, source, validator, valid, quality_score, run_id, report) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (url, ts, source, validator, int(bool(valid)), quality_score, run_id, json.dumps(report, ensure_ascii=False))
        )
        self.conn.commit()
        return cur.lastrowid

    def fetch_recent(self, limit: int = 100):
        cur = self.conn.cursor()
        cur.execute("SELECT id, url, timestamp, source, validator, valid, quality_score, run_id, report FROM validations ORDER BY timestamp DESC LIMIT ?", (limit,))
        rows = cur.fetchall()
        results = []
        for r in rows:
            try:
                rep = json.loads(r[8])
            except Exception:
                rep = {}
            results.append({
                "id": r[0],
                "url": r[1],
                "timestamp": r[2],
                "source": r[3],
                "validator": r[4],
                "valid": bool(r[5]),
                "quality_score": r[6],
                "run_id": r[7],
                "report": rep
            })
        return results
