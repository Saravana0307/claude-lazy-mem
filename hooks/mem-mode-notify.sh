#!/usr/bin/env bash
# mem-mode-notify.sh
# Runs at SessionStart. Logs session to DB. Emits ~20-token mode status for Claude.

MODE=$(cat "$HOME/.claude/mem-mode" 2>/dev/null | tr -d '[:space:]')
[ "$MODE" != "full" ] && MODE="lazy"

# Parse session ID and project from hook input (passed via stdin as JSON)
if [ -n "$HOOK_INPUT" ]; then
  SESSION_ID=$(echo "$HOOK_INPUT" | python3 -c \
    "import sys,json; d=json.load(sys.stdin); print(d.get('session_id', d.get('sessionId','')))" 2>/dev/null)
  CWD=$(echo "$HOOK_INPUT" | python3 -c \
    "import sys,json; d=json.load(sys.stdin); print(d.get('cwd',''))" 2>/dev/null)
fi
SESSION_ID="${SESSION_ID:-unknown}"
PROJECT=$(basename "${CWD:-$(pwd)}")

# Log session to DB (background, non-blocking)
python3 "$HOME/.claude-lazy-mem/scripts/db.py" log-session \
  --session-id "$SESSION_ID" --project "$PROJECT" --mode "$MODE" 2>/dev/null &

# Emit mode status — becomes part of Claude's context (~20-25 tokens)
if [ "$MODE" = "lazy" ]; then
  echo "[lazy-mem] LAZY MODE — memory context NOT loaded. On your first response, ask the user: 'Load memory context for this session? (y/n)'"
else
  echo "[lazy-mem] FULL MODE — memory context auto-loaded."
fi

# Patch-check: warn if hooks.json was overwritten by a plugin update
if ! python3 "$HOME/.claude-lazy-mem/scripts/patch-hooks-json.py" --check 2>/dev/null; then
  echo "[lazy-mem] WARNING: claude-mem hooks.json patch is missing (plugin may have updated). Run: lazy-mem doctor"
fi
