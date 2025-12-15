from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from flask import current_app, g, request


def _connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = _connect(current_app.config["DB_PATH"])
    return g.db


def close_db(_exc: BaseException | None = None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def init_db(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = _connect(str(db_path))
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              username TEXT NOT NULL UNIQUE,
              password_hash TEXT NOT NULL,
              is_admin INTEGER NOT NULL DEFAULT 0,
              display_name TEXT NOT NULL DEFAULT '',
              description TEXT NOT NULL DEFAULT '',
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS audit_logs (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              user_id INTEGER,
              action TEXT NOT NULL,
              detail TEXT NOT NULL DEFAULT '',
              ip TEXT NOT NULL DEFAULT '',
              ua TEXT NOT NULL DEFAULT '',
              created_at TEXT NOT NULL,
              FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS images (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              user_id INTEGER NOT NULL,
              original_name TEXT NOT NULL,
              stored_name TEXT NOT NULL,
              watermarked_name TEXT NOT NULL,
              watermark_text TEXT NOT NULL DEFAULT '',
              created_at TEXT NOT NULL,
              FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            -- 仅用于 SQL 注入实验（作业二-攻防实验）
            CREATE TABLE IF NOT EXISTS notes (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              title TEXT NOT NULL,
              content TEXT NOT NULL
            );
            """
        )
        conn.commit()

        # lightweight migration for old DB files
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(users)").fetchall()}
        if "is_admin" not in cols:
            conn.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER NOT NULL DEFAULT 0;")
            conn.commit()

        cur = conn.execute("SELECT COUNT(1) AS c FROM notes")
        if int(cur.fetchone()["c"]) == 0:
            conn.executemany(
                "INSERT INTO notes (title, content) VALUES (?, ?)",
                [
                    ("Welcome", "This table is used for SQL injection lab."),
                    ("Todo", "Try: %' OR 1=1 --  (in the insecure search)"),
                    ("Defense", "Use parameterized queries to prevent injection."),
                ],
            )
            conn.commit()
    finally:
        conn.close()


def init_db_if_missing(db_path: Path) -> None:
    # keep the old name but always ensure schema is ready (create + migrate)
    init_db(db_path)


def log_action(user_id: int | None, action: str, detail: str = "") -> None:
    ip = request.remote_addr or ""
    ua = request.headers.get("User-Agent", "")
    get_db().execute(
        """
        INSERT INTO audit_logs (user_id, action, detail, ip, ua, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (user_id, action, detail, ip, ua, _now_iso()),
    )
    get_db().commit()


def fetch_many(sql: str, params: tuple = ()) -> list[dict]:
    cur = get_db().execute(sql, params)
    rows = cur.fetchall()
    return [dict(r) for r in rows]


def fetch_one(sql: str, params: tuple = ()) -> dict | None:
    cur = get_db().execute(sql, params)
    row = cur.fetchone()
    return dict(row) if row else None
