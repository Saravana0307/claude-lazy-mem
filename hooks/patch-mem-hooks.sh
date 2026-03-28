#!/usr/bin/env bash
# patch-mem-hooks.sh
# Re-applies the hooks.json patch after claude-mem plugin updates.
# Safe to run multiple times (idempotent).

set -e

if python3 "$HOME/.claude-lazy-mem/scripts/patch-hooks-json.py" --check 2>/dev/null; then
  echo "hooks.json already patched — nothing to do."
  exit 0
fi

python3 "$HOME/.claude-lazy-mem/scripts/patch-hooks-json.py" --patch
