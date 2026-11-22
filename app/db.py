import json
import sqlite3
from contextlib import contextmanager

from .config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS clients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    brand TEXT NOT NULL,
    aliases TEXT DEFAULT '',
    domain TEXT NOT NULL,
    industry TEXT DEFAULT '',
    competitors TEXT DEFAULT '',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS prompts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    text TEXT NOT NULL,
    category TEXT DEFAULT 'general',
    active INTEGER DEFAULT 1
);
CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    started_at TEXT DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'running',
    summary TEXT DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    prompt_id INTEGER REFERENCES prompts(id) ON DELETE SET NULL,
    prompt_text TEXT,
    engine TEXT,
    answer TEXT,
    citations TEXT DEFAULT '[]',
    mentioned INTEGER DEFAULT 0,
    cited INTEGER DEFAULT 0,
    position INTEGER,
    sentiment TEXT,
    competitors_mentioned TEXT DEFAULT '[]',
    error TEXT
);
CREATE TABLE IF NOT EXISTS audits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    url TEXT,
    score INTEGER,
    data TEXT,
    ai_plan TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS facts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    question TEXT NOT NULL,
    answer TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS factcheck_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    started_at TEXT DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'running',
    summary TEXT DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS factcheck_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL REFERENCES factcheck_runs(id) ON DELETE CASCADE,
    fact_id INTEGER REFERENCES facts(id) ON DELETE SET NULL,
    question TEXT,
    expected TEXT,
    engine TEXT,
    answer TEXT,
    citations TEXT DEFAULT '[]',
    verdict TEXT,
    explanation TEXT,
    wrong_claims TEXT DEFAULT '[]',
    error TEXT
);
CREATE TABLE IF NOT EXISTS leads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    token TEXT UNIQUE,
    name TEXT DEFAULT '',
    email TEXT NOT NULL,
    website TEXT DEFAULT '',
    message TEXT DEFAULT '',
    source TEXT DEFAULT 'contact',
    score INTEGER,
    audit_data TEXT,
    status TEXT DEFAULT 'new',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
"""


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def get_db():
    conn = connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with get_db() as db:
        db.executescript(SCHEMA)


def split_list(value: str) -> list[str]:
    return [v.strip() for v in (value or "").replace("\n", ",").split(",") if v.strip()]


def loads(value, default):
    try:
        return json.loads(value) if value else default
    except (TypeError, ValueError):
        return default
