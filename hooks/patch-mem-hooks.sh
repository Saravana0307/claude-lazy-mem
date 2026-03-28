#!/usr/bin/env bash
# patch-mem-hooks.sh
# Re-applies the hooks.json patch after claude-mem plugin updates.
# Safe to run multiple times (idempotent).

set -e
python3 "$HOME/.claude-lazy-mem/scripts/patch-hooks-json.py" --patch
