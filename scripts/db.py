#!/usr/bin/env python3
"""
db.py — SQLite helper for claude-lazy-mem
Usage:
  db.py log-session --session-id ID --project NAME --mode lazy|full
  db.py update-session --session-id ID --input N --output N --cache-read N --cache-write N --model M --cost F
  db.py log-context-load --session-id ID --trigger user_requested|auto
  db.py calibrate
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
CONFIG_PATH = os.path.expanduser("~/.claude-lazy-mem/config.json")
DEFAULT_CONTEXT_TOKENS = 25000


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


def load_config():
    try:
        with open(CONFIG_PATH) as f:
            return json.load(f)
    except Exception:
        return {}


def save_config(data):
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def get_context_load_tokens():
    """Return calibrated context load size, or default estimate."""
    return load_config().get("context_load_tokens", DEFAULT_CONTEXT_TOKENS)


def cmd_calibrate(args):
    """Run worker-service context hook, measure output, store token estimate."""
    import subprocess
    plugin = os.path.expanduser("~/.claude/plugins/marketplaces/thedotmack/plugin")
    bun_runner = os.path.join(plugin, "scripts", "bun-runner.js")
    worker = os.path.join(plugin, "scripts", "worker-service.cjs")

    if not os.path.isfile(worker):
        print(f"ERROR: worker-service.cjs not found at {worker}", file=sys.stderr)
        sys.exit(1)

    print("Running context load to measure size (may take a few seconds)...")
    try:
        result = subprocess.run(
            ["node", bun_runner, worker, "hook", "claude-code", "context"],
            capture_output=True, text=True, timeout=30
        )
        output = result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        print("Timed out — using default estimate of 25,000 tokens.")
        output = ""

    # Rough estimate: ~4 chars per token
    token_estimate = max(1000, len(output) // 4)

    config = load_config()
    config["context_load_tokens"] = token_estimate
    config["calibrated_at"] = datetime.now(timezone.utc).isoformat()
    save_config(config)

    print(f"Calibrated: context load ≈ {token_estimate:,} tokens ({len(output):,} chars)")
    print(f"Saved to: {CONFIG_PATH}")


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
            SUM(CASE WHEN mode='full' THEN 1 ELSE 0 END) as full_count
        FROM sessions
    """).fetchone()

    total = row["total"] or 0
    lazy = row["lazy_count"] or 0
    full = row["full_count"] or 0
    ctx_tokens = get_context_load_tokens()

    tokens_saved = lazy * ctx_tokens
    cost_saved = tokens_saved * 0.30 / 1_000_000

    result = {
        "total": total,
        "lazy": lazy,
        "full": full,
        "lazy_pct": round(lazy / total * 100, 1) if total else 0,
        "estimated_context_size": ctx_tokens,
        "tokens_saved": tokens_saved,
        "cost_saved": round(cost_saved, 4),
        "calibrated": "context_load_tokens" in load_config(),
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
    ctx_tokens = get_context_load_tokens()

    rows = conn.execute("""
        SELECT
            project,
            COUNT(*) as total,
            SUM(CASE WHEN mode='lazy' THEN 1 ELSE 0 END) as lazy_count,
            SUM(CASE WHEN mode='full' THEN 1 ELSE 0 END) as full_count
        FROM sessions
        GROUP BY project
        ORDER BY total DESC
    """).fetchall()

    result = []
    for r in rows:
        lazy = r["lazy_count"] or 0
        tokens_saved = lazy * ctx_tokens
        result.append({
            "project": r["project"],
            "total": r["total"],
            "lazy": lazy,
            "full": r["full_count"] or 0,
            "avg_context_size": ctx_tokens,
            "tokens_saved": tokens_saved,
            "cost_saved": round(tokens_saved * 0.30 / 1_000_000, 4),
        })
    print(json.dumps(result))
    conn.close()


def main():
    parser = argparse.ArgumentParser(description="claude-lazy-mem database helper")
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("calibrate")

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

    sub.add_parser("summary")

    p = sub.add_parser("sessions")
    p.add_argument("--days", type=int, default=30)
    p.add_argument("--csv", action="store_true")

    p = sub.add_parser("daily")
    p.add_argument("--days", type=int, default=30)

    sub.add_parser("projects")

    args = parser.parse_args()
    if not args.cmd:
        parser.print_help()
        sys.exit(1)

    dispatch = {
        "calibrate": cmd_calibrate,
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
