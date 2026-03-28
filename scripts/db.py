#!/usr/bin/env python3
"""
db.py — SQLite helper for claude-lazy-mem
Usage:
  db.py log-session --session-id ID --project NAME --mode lazy|full
  db.py update-session --session-id ID --input N --output N --cache-read N --cache-write N --model M --cost F
  db.py log-context-load --session-id ID --trigger user_requested|auto
  db.py summary
  db.py sessions [--days N] [--csv]
  db.py daily [--days N]
  db.py projects
"""
import argparse
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone

DB_PATH = os.path.expanduser("~/.claude-lazy-mem/sessions.db")


def get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS sessions (
            id            TEXT PRIMARY KEY,
            project       TEXT,
            started_at    TIMESTAMP,
            mode          TEXT,
            input_tokens  INTEGER,
            output_tokens INTEGER,
            cache_read    INTEGER,
            cache_write   INTEGER,
            model         TEXT,
            cost          REAL
        );

        CREATE TABLE IF NOT EXISTS context_loads (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id  TEXT REFERENCES sessions(id),
            loaded_at   TIMESTAMP,
            trigger     TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_sessions_project ON sessions(project);
        CREATE INDEX IF NOT EXISTS idx_sessions_started ON sessions(started_at);
    """)
    conn.commit()


def cmd_log_session(args):
    conn = get_conn()
    init_db(conn)
    ts = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT OR IGNORE INTO sessions (id, project, started_at, mode) VALUES (?, ?, ?, ?)",
        (args.session_id, args.project, ts, args.mode)
    )
    conn.commit()
    conn.close()


def cmd_update_session(args):
    conn = get_conn()
    init_db(conn)
    conn.execute("""
        UPDATE sessions
        SET input_tokens=?, output_tokens=?, cache_read=?, cache_write=?, model=?, cost=?
        WHERE id=?
    """, (args.input, args.output, args.cache_read, args.cache_write, args.model, args.cost, args.session_id))
    conn.commit()
    conn.close()


def cmd_log_context_load(args):
    conn = get_conn()
    init_db(conn)
    ts = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO context_loads (session_id, loaded_at, trigger) VALUES (?, ?, ?)",
        (args.session_id, ts, args.trigger)
    )
    conn.commit()
    conn.close()


def cmd_summary(args):
    conn = get_conn()
    init_db(conn)

    row = conn.execute("""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN mode='lazy' THEN 1 ELSE 0 END) as lazy_count,
            SUM(CASE WHEN mode='full' THEN 1 ELSE 0 END) as full_count,
            AVG(CASE WHEN mode='full' AND input_tokens IS NOT NULL THEN input_tokens END) as avg_full_input
        FROM sessions
    """).fetchone()

    total = row["total"] or 0
    lazy = row["lazy_count"] or 0
    full = row["full_count"] or 0
    avg_full = row["avg_full_input"] or 25000  # default estimate

    estimated_savings = lazy * int(avg_full)
    # Use approximate cache_read price for claude-sonnet: $0.30/1M
    cost_saved = estimated_savings * 0.30 / 1_000_000

    result = {
        "total": total,
        "lazy": lazy,
        "full": full,
        "lazy_pct": round(lazy / total * 100, 1) if total else 0,
        "estimated_context_size": int(avg_full),
        "tokens_saved": estimated_savings,
        "cost_saved": round(cost_saved, 4),
    }
    print(json.dumps(result))
    conn.close()


def cmd_sessions(args):
    conn = get_conn()
    init_db(conn)

    days = getattr(args, 'days', 30)
    rows = conn.execute("""
        SELECT id, project, mode, started_at, input_tokens, output_tokens, cache_read, cache_write, model, cost
        FROM sessions
        WHERE started_at >= datetime('now', ? || ' days')
        ORDER BY started_at DESC
        LIMIT 500
    """, (f"-{days}",)).fetchall()

    data = [dict(r) for r in rows]

    if getattr(args, 'csv', False):
        import csv, io
        out = io.StringIO()
        if data:
            w = csv.DictWriter(out, fieldnames=data[0].keys())
            w.writeheader()
            w.writerows(data)
        print(out.getvalue())
    else:
        print(json.dumps(data))
    conn.close()


def cmd_daily(args):
    conn = get_conn()
    init_db(conn)

    days = getattr(args, 'days', 30)
    rows = conn.execute("""
        SELECT
            date(started_at) as date,
            SUM(CASE WHEN mode='lazy' THEN 1 ELSE 0 END) as lazy_count,
            SUM(CASE WHEN mode='full' THEN 1 ELSE 0 END) as full_count
        FROM sessions
        WHERE started_at >= datetime('now', ? || ' days')
        GROUP BY date(started_at)
        ORDER BY date
    """, (f"-{days}",)).fetchall()

    print(json.dumps([dict(r) for r in rows]))
    conn.close()


def cmd_projects(args):
    conn = get_conn()
    init_db(conn)

    rows = conn.execute("""
        SELECT
            project,
            COUNT(*) as total,
            SUM(CASE WHEN mode='lazy' THEN 1 ELSE 0 END) as lazy_count,
            SUM(CASE WHEN mode='full' THEN 1 ELSE 0 END) as full_count,
            AVG(CASE WHEN mode='full' AND input_tokens IS NOT NULL THEN input_tokens END) as avg_full_input
        FROM sessions
        GROUP BY project
        ORDER BY total DESC
    """).fetchall()

    result = []
    for r in rows:
        avg_full = r["avg_full_input"] or 25000
        lazy = r["lazy_count"] or 0
        tokens_saved = lazy * int(avg_full)
        result.append({
            "project": r["project"],
            "total": r["total"],
            "lazy": lazy,
            "full": r["full_count"] or 0,
            "avg_context_size": int(avg_full),
            "tokens_saved": tokens_saved,
            "cost_saved": round(tokens_saved * 0.30 / 1_000_000, 4),
        })
    print(json.dumps(result))
    conn.close()


def main():
    parser = argparse.ArgumentParser(description="claude-lazy-mem database helper")
    sub = parser.add_subparsers(dest="cmd")

    p = sub.add_parser("log-session")
    p.add_argument("--session-id", required=True)
    p.add_argument("--project", required=True)
    p.add_argument("--mode", required=True, choices=["lazy", "full"])

    p = sub.add_parser("update-session")
    p.add_argument("--session-id", required=True)
    p.add_argument("--input", type=int, default=0)
    p.add_argument("--output", type=int, default=0)
    p.add_argument("--cache-read", type=int, default=0)
    p.add_argument("--cache-write", type=int, default=0)
    p.add_argument("--model", default="")
    p.add_argument("--cost", type=float, default=0.0)

    p = sub.add_parser("log-context-load")
    p.add_argument("--session-id", required=True)
    p.add_argument("--trigger", default="user_requested")

    p = sub.add_parser("summary")

    p = sub.add_parser("sessions")
    p.add_argument("--days", type=int, default=30)
    p.add_argument("--csv", action="store_true")

    p = sub.add_parser("daily")
    p.add_argument("--days", type=int, default=30)

    p = sub.add_parser("projects")

    args = parser.parse_args()
    if not args.cmd:
        parser.print_help()
        sys.exit(1)

    dispatch = {
        "log-session": cmd_log_session,
        "update-session": cmd_update_session,
        "log-context-load": cmd_log_context_load,
        "summary": cmd_summary,
        "sessions": cmd_sessions,
        "daily": cmd_daily,
        "projects": cmd_projects,
    }
    dispatch[args.cmd](args)


if __name__ == "__main__":
    main()
