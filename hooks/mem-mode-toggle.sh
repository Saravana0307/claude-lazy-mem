#!/usr/bin/env bash
# mem-mode-toggle.sh
# Usage:
#   mem-mode-toggle.sh           → toggle current mode
#   mem-mode-toggle.sh lazy      → set lazy mode
#   mem-mode-toggle.sh full      → set full mode

MODE_FILE="$HOME/.claude/mem-mode"

CURRENT=$(cat "$MODE_FILE" 2>/dev/null | tr -d '[:space:]')
[ "$CURRENT" != "full" ] && CURRENT="lazy"

if [ -n "$1" ]; then
  NEW="$1"
else
  [ "$CURRENT" = "lazy" ] && NEW="full" || NEW="lazy"
fi

if [ "$NEW" != "lazy" ] && [ "$NEW" != "full" ]; then
  echo "ERROR: unknown mode '$NEW'. Use 'lazy' or 'full'." >&2
  exit 1
fi

echo "$NEW" > "$MODE_FILE"
echo "Memory mode: $CURRENT → $NEW"

if [ "$NEW" = "full" ]; then
  echo "  Full context will auto-load at next session start."
  echo "  To load immediately: use the mem-search skill."
else
  echo "  No context will auto-load. Use mem-search skill on demand."
fi
