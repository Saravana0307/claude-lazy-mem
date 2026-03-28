#!/usr/bin/env python3
"""
server.py — claude-lazy-mem web dashboard
Serves on port 7124 (configurable via --port)
No external dependencies — stdlib only.
"""
import argparse
import json
import os
import sqlite3
import sys
import threading
import urllib.parse
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer

# Add scripts directory to path for db.py helpers
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

DB_PATH = os.path.expanduser("~/.claude-lazy-mem/sessions.db")
MODE_FILE = os.path.expanduser("~/.claude/mem-mode")
TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")


def get_db():
    if not os.path.isfile(DB_PATH):
        return None
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_mode():
    try:
        with open(MODE_FILE) as f:
            m = f.read().strip()
        return m if m in ("lazy", "full") else "lazy"
    except Exception:
        return "lazy"


def set_mode(mode):
    if mode not in ("lazy", "full"):
        return False
    os.makedirs(os.path.dirname(MODE_FILE), exist_ok=True)
    with open(MODE_FILE, "w") as f:
        f.write(mode)
    return True


def api_summary():
    conn = get_db()
    if not conn:
        return {"total": 0, "lazy": 0, "full": 0, "lazy_pct": 0,
                "tokens_saved": 0, "cost_saved": 0, "estimated_context_size": 25000}
    try:
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
        avg_full = int(row["avg_full_input"] or 25000)
        tokens_saved = lazy * avg_full
        cost_saved = round(tokens_saved * 0.30 / 1_000_000, 4)
        return {
            "total": total, "lazy": lazy, "full": full,
            "lazy_pct": round(lazy / total * 100, 1) if total else 0,
            "tokens_saved": tokens_saved, "cost_saved": cost_saved,
            "estimated_context_size": avg_full,
        }
    finally:
        conn.close()


def api_sessions(days=30):
    conn = get_db()
    if not conn:
        return []
    try:
        rows = conn.execute("""
            SELECT id, project, mode, started_at, input_tokens, output_tokens, cache_read, cache_write, model, cost
            FROM sessions
            WHERE started_at >= datetime('now', ? || ' days')
            ORDER BY started_at DESC LIMIT 200
        """, (f"-{days}",)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def api_daily(days=30):
    conn = get_db()
    if not conn:
        return []
    try:
        rows = conn.execute("""
            SELECT
                date(started_at) as date,
                SUM(CASE WHEN mode='lazy' THEN 1 ELSE 0 END) as lazy_count,
                SUM(CASE WHEN mode='full' THEN 1 ELSE 0 END) as full_count
            FROM sessions
            WHERE started_at >= datetime('now', ? || ' days')
            GROUP BY date(started_at) ORDER BY date
        """, (f"-{days}",)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def api_projects():
    conn = get_db()
    if not conn:
        return []
    try:
        rows = conn.execute("""
            SELECT project,
                COUNT(*) as total,
                SUM(CASE WHEN mode='lazy' THEN 1 ELSE 0 END) as lazy_count,
                SUM(CASE WHEN mode='full' THEN 1 ELSE 0 END) as full_count,
                AVG(CASE WHEN mode='full' AND input_tokens IS NOT NULL THEN input_tokens END) as avg_full
            FROM sessions GROUP BY project ORDER BY total DESC
        """).fetchall()
        result = []
        for r in rows:
            avg = int(r["avg_full"] or 25000)
            lazy = r["lazy_count"] or 0
            ts = lazy * avg
            result.append({
                "project": r["project"], "total": r["total"],
                "lazy": lazy, "full": r["full_count"] or 0,
                "avg_context_size": avg, "tokens_saved": ts,
                "cost_saved": round(ts * 0.30 / 1_000_000, 4),
            })
        return result
    finally:
        conn.close()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # Suppress access logs

    def send_json(self, data, status=200):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def send_file(self, path, content_type):
        try:
            with open(path, "rb") as f:
                body = f.read()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", len(body))
            self.end_headers()
            self.wfile.write(body)
        except FileNotFoundError:
            self.send_response(404)
            self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(parsed.query)
        path = parsed.path

        if path == "/" or path == "/index.html":
            self.send_file(os.path.join(TEMPLATE_DIR, "index.html"), "text/html; charset=utf-8")
        elif path.startswith("/static/"):
            fname = path[len("/static/"):]
            ext = fname.rsplit(".", 1)[-1] if "." in fname else ""
            mime = {"js": "application/javascript", "css": "text/css"}.get(ext, "text/plain")
            self.send_file(os.path.join(STATIC_DIR, fname), mime)
        elif path == "/api/mode":
            self.send_json({"mode": get_mode()})
        elif path == "/api/summary":
            self.send_json(api_summary())
        elif path == "/api/sessions":
            days = int(qs.get("days", ["30"])[0])
            self.send_json(api_sessions(days))
        elif path == "/api/daily":
            days = int(qs.get("days", ["30"])[0])
            self.send_json(api_daily(days))
        elif path == "/api/projects":
            self.send_json(api_projects())
        elif path == "/api/health":
            import subprocess
            patched = subprocess.run(
                ["python3", os.path.join(os.path.dirname(__file__), "..", "scripts", "patch-hooks-json.py"), "--check"],
                capture_output=True
            ).returncode == 0
            self.send_json({"patched": patched, "db_path": DB_PATH, "version": "1.0.0"})
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == "/api/mode":
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))
            mode = body.get("mode", "")
            if set_mode(mode):
                self.send_json({"mode": mode, "ok": True})
            else:
                self.send_json({"error": "invalid mode"}, 400)
        else:
            self.send_response(404)
            self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=7124)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()

    server = HTTPServer((args.host, args.port), Handler)
    print(f"claude-lazy-mem dashboard running at http://{args.host}:{args.port}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
