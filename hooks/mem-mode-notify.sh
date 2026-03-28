#!/usr/bin/env bash
# mem-mode-notify.sh
# Runs at SessionStart. Logs session to DB. Emits ~25-token mode status for Claude.

MODE=$(cat "$HOME/.claude/mem-mode" 2>/dev/null | tr -d '[:space:]')
[ "$MODE" != "full" ] && MODE="lazy"

# Claude Code passes hook data via stdin as JSON
HOOK_DATA=$(cat 2>/dev/null)

SESSION_ID=$(echo "$HOOK_DATA" | python3 -c \
  "import sys,json; d=json.load(sys.stdin); print(d.get('session_id', d.get('sessionId','unknown')))" 2>/dev/null || echo "unknown")
CWD=$(echo "$HOOK_DATA" | python3 -c \
  "import sys,json; d=json.load(sys.stdin); print(d.get('cwd',''))" 2>/dev/null || echo "")
PROJECT=$(basename "${CWD:-$(pwd)}")

# Log session to DB (background, non-blocking — pass args directly, not stdin)
python3 "$HOME/.claude-lazy-mem/scripts/db.py" log-session \
  --session-id "$SESSION_ID" --project "$PROJECT" --mode "$MODE" 2>/dev/null &

# Emit mode status for Claude context
if [ "$MODE" = "lazy" ]; then
  echo "[lazy-mem] LAZY MODE — memory context NOT loaded. On your first response, ask the user: 'Load memory context for this session? (y/n)'"
else
  echo "[lazy-mem] FULL MODE — memory context auto-loaded."
fi

# Patch-check: warn if hooks.json was overwritten by a plugin update
if ! python3 "$HOME/.claude-lazy-mem/scripts/patch-hooks-json.py" --check 2>/dev/null; then
  echo "[lazy-mem] WARNING: claude-mem hooks.json patch is missing. Run: lazy-mem doctor"
fi
