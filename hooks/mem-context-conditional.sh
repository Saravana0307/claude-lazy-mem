#!/usr/bin/env bash
# mem-context-conditional.sh
# Replaces: worker-service.cjs hook claude-code context
# Gates claude-mem context loading based on ~/.claude/mem-mode (lazy|full)

MODE=$(cat "$HOME/.claude/mem-mode" 2>/dev/null | tr -d '[:space:]')

# Default to lazy for any unknown/missing value — fail closed
[ "$MODE" != "full" ] && exit 0

# Full mode: delegate to the real hook with same path resolution as the plugin
_R="${CLAUDE_PLUGIN_ROOT}"
[ -z "$_R" ] && _R="$HOME/.claude/plugins/marketplaces/thedotmack/plugin"
exec node "$_R/scripts/bun-runner.js" "$_R/scripts/worker-service.cjs" hook claude-code context
