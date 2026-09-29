"""SQLite WAL store with explicit transactions and read-only query connections."""

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_version (version INTEGER PRIMARY KEY);
INSERT OR IGNORE INTO schema_version VALUES (1);
CREATE TABLE IF NOT EXISTS datasets (id TEXT PRIMARY KEY, created_at TEXT NOT NULL, payload TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, created_at TEXT NOT NULL, task TEXT NOT NULL, stage TEXT NOT NULL, payload TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS deployments (task TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES runs(id), updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS events (id TEXT PRIMARY KEY, created_at TEXT NOT NULL, kind TEXT NOT NULL, payload TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, created_at TEXT NOT NULL, status TEXT NOT NULL, payload TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS schedules (id TEXT PRIMARY KEY, created_at TEXT NOT NULL, payload TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS monitors (id TEXT PRIMARY KEY, created_at TEXT NOT NULL, payload TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS predictions (id TEXT PRIMARY KEY, created_at TEXT NOT NULL, payload TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS idempotency (key TEXT PRIMARY KEY, fingerprint TEXT NOT NULL, response TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS ix_runs_task ON runs(task, created_at);
CREATE INDEX IF NOT EXISTS ix_jobs_status ON jobs(status, created_at);
"""
TABLES = {"datasets", "runs", "events", "jobs", "schedules", "monitors", "predictions"}


def encode(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), allow_nan=False)


class Store:
    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "operations.sqlite3"
        with self.connect() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.executescript(SCHEMA)

    def connect(self, readonly=False):
        db = sqlite3.connect(
            f"file:{self.path}?mode=ro" if readonly else self.path, uri=readonly, timeout=30
        )
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        if readonly:
            db.execute("PRAGMA query_only=ON")
        return db

    @contextmanager
    def transaction(self):
        db = self.connect()
        try:
            db.execute("BEGIN IMMEDIATE")
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def rows(self, table):
        assert table in TABLES
        with self.connect(True) as db:
            return [
                json.loads(r["payload"])
                for r in db.execute(
                    f"SELECT payload FROM {table} ORDER BY created_at DESC, id DESC"
                )
            ]

    def get(self, table, ident, db=None):
        assert table in TABLES
        if db is None:
            with self.connect(True) as conn:
                return self.get(table, ident, conn)
        row = db.execute(f"SELECT payload FROM {table} WHERE id=?", (ident,)).fetchone()
        return json.loads(row["payload"]) if row else None

    def put(self, db, table, value):
        assert table in TABLES
        columns = ["id", "created_at"]
        if table == "runs":
            columns += ["task", "stage"]
        if table == "events":
            columns += ["kind"]
        if table == "jobs":
            columns += ["status"]
        vals = [value[c] for c in columns] + [encode(value)]
        columns += ["payload"]
        db.execute(
            f"INSERT INTO {table} ({','.join(columns)}) VALUES ({','.join('?' for _ in columns)}) ON CONFLICT(id) DO UPDATE SET "
            + ",".join(f"{c}=excluded.{c}" for c in columns[1:]),
            vals,
        )
