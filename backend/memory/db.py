"""
Agent-0 Database
SQLite database for structured knowledge storage.
"""

import sqlite3
import threading
from pathlib import Path


class Database:
    """SQLite database manager for Agent-0. Thread-safe with per-thread connections."""

    def __init__(self, db_path: Path):
        self.db_path = str(db_path)
        self._local = threading.local()

    @property
    def conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=30)
            self._local.conn.row_factory = sqlite3.Row
            self._local.conn.execute("PRAGMA journal_mode=WAL")
            self._local.conn.execute("PRAGMA foreign_keys=ON")
            self._local.conn.execute("PRAGMA busy_timeout=30000")
        return self._local.conn

    def initialize(self):
        """Create all tables if they don't exist."""
        cursor = self.conn.cursor()

        cursor.executescript("""
            -- Every change observed
            CREATE TABLE IF NOT EXISTS changes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL DEFAULT (datetime('now')),
                files_changed TEXT NOT NULL,
                diff_summary TEXT,
                category TEXT,
                phase_id INTEGER,
                session_id INTEGER
            );

            -- Phase tracking
            CREATE TABLE IF NOT EXISTS phases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                goal TEXT,
                status TEXT DEFAULT 'open',
                opened TEXT DEFAULT (datetime('now')),
                closed TEXT,
                summary TEXT
            );

            -- Gospel rules
            CREATE TABLE IF NOT EXISTS gospels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rule TEXT NOT NULL,
                reason TEXT,
                category TEXT,
                scope TEXT DEFAULT 'global',
                created_by TEXT DEFAULT 'human',
                confidence TEXT DEFAULT 'high',
                status TEXT DEFAULT 'active',
                created TEXT DEFAULT (datetime('now')),
                last_validated TEXT,
                false_alerts INTEGER DEFAULT 0,
                confirmed_alerts INTEGER DEFAULT 0
            );

            -- Open items (bugs, debt, untested things)
            CREATE TABLE IF NOT EXISTS open_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                description TEXT NOT NULL,
                type TEXT,
                status TEXT DEFAULT 'open',
                linked_phase INTEGER,
                created TEXT DEFAULT (datetime('now')),
                resolved TEXT
            );

            -- Session tracking
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL DEFAULT (date('now')),
                intent TEXT,
                actual_outcome TEXT,
                drift_score REAL,
                started TEXT DEFAULT (datetime('now')),
                ended TEXT
            );

            -- Alerts sent
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL DEFAULT (datetime('now')),
                message TEXT NOT NULL,
                type TEXT,
                severity TEXT DEFAULT 'medium',
                dismissed INTEGER DEFAULT 0,
                response TEXT
            );

            -- Onboarding progress
            CREATE TABLE IF NOT EXISTS onboarding_progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                phase TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                started TEXT,
                completed TEXT,
                notes TEXT
            );

            -- Agent connections (track who's querying and when)
            CREATE TABLE IF NOT EXISTS connections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                first_seen TEXT DEFAULT (datetime('now')),
                last_query_at TEXT DEFAULT (datetime('now')),
                queries_count INTEGER DEFAULT 0,
                brief_delivered INTEGER DEFAULT 0
            );

            -- Pending pings (reminders to deliver to working agents)
            CREATE TABLE IF NOT EXISTS pending_pings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created TEXT DEFAULT (datetime('now')),
                message TEXT NOT NULL,
                type TEXT DEFAULT 'reminder',
                delivered INTEGER DEFAULT 0
            );

            -- File snapshots (persisted for catch-up across restarts)
            CREATE TABLE IF NOT EXISTS file_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT NOT NULL UNIQUE,
                hash TEXT NOT NULL,
                size INTEGER,
                lines INTEGER,
                last_seen TEXT DEFAULT (datetime('now'))
            );

            -- Pending triggers (queued when API is down)
            CREATE TABLE IF NOT EXISTS pending_triggers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL DEFAULT (datetime('now')),
                trigger_type TEXT,
                data TEXT,
                processed INTEGER DEFAULT 0
            );

            -- Memory index for vector + FTS search
            CREATE TABLE IF NOT EXISTS memory_index (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_file TEXT NOT NULL,
                chunk TEXT NOT NULL,
                embedding BLOB,
                updated TEXT DEFAULT (datetime('now'))
            );
        """)

        # Create FTS5 virtual table for keyword search
        try:
            cursor.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts
                USING fts5(source_file, chunk, content=memory_index, content_rowid=id)
            """)
        except sqlite3.OperationalError:
            pass  # FTS5 table already exists

        self.conn.commit()

    def execute(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        """Execute a query and return cursor."""
        return self.conn.execute(query, params)

    def executemany(self, query: str, params_list: list) -> sqlite3.Cursor:
        """Execute a query with multiple parameter sets."""
        return self.conn.executemany(query, params_list)

    def fetchone(self, query: str, params: tuple = ()) -> dict | None:
        """Execute query and return one row as dict."""
        cursor = self.execute(query, params)
        row = cursor.fetchone()
        return dict(row) if row else None

    def fetchall(self, query: str, params: tuple = ()) -> list[dict]:
        """Execute query and return all rows as list of dicts."""
        cursor = self.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    def insert(self, table: str, data: dict) -> int:
        """Insert a row and return the row ID."""
        cols = ", ".join(data.keys())
        placeholders = ", ".join(["?"] * len(data))
        query = f"INSERT INTO {table} ({cols}) VALUES ({placeholders})"
        cursor = self.execute(query, tuple(data.values()))
        self.conn.commit()
        return cursor.lastrowid

    def update(self, table: str, data: dict, where: str, params: tuple = ()):
        """Update rows matching where clause."""
        sets = ", ".join([f"{k} = ?" for k in data.keys()])
        query = f"UPDATE {table} SET {sets} WHERE {where}"
        self.execute(query, tuple(data.values()) + params)
        self.conn.commit()

    def close(self):
        """Close the database connection for the current thread."""
        if hasattr(self._local, 'conn') and self._local.conn:
            self._local.conn.close()
            self._local.conn = None
