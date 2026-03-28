#!/usr/bin/env bash
# uninstall.sh — Remove claude-lazy-mem

set -e

INSTALL_DIR="$HOME/.claude-lazy-mem"
CLAUDE_HOOKS_DIR="$HOME/.claude/hooks"

echo "Uninstalling claude-lazy-mem..."

# 1. Restore hooks.json
python3 "$INSTALL_DIR/scripts/patch-hooks-json.py" --unpatch 2>/dev/null || true

# 2. Remove settings.json hooks
python3 "$INSTALL_DIR/scripts/patch-hooks-json.py" --unsettings 2>/dev/null || true

# 3. Remove CLAUDE.md section
python3 "$INSTALL_DIR/scripts/patch-hooks-json.py" --unclaudemd 2>/dev/null || true

# 4. Remove symlinks from ~/.claude/hooks/
rm -f "$CLAUDE_HOOKS_DIR/mem-context-conditional.sh"
rm -f "$CLAUDE_HOOKS_DIR/mem-mode-notify.sh"
rm -f "$CLAUDE_HOOKS_DIR/mem-mode-toggle.sh"
rm -f "$CLAUDE_HOOKS_DIR/patch-mem-hooks.sh"

# 5. Remove CLI symlinks
rm -f "$HOME/.local/bin/lazy-mem" 2>/dev/null || true
rm -f "/usr/local/bin/lazy-mem" 2>/dev/null || true

# 6. Remove install directory (ask first)
if [ -d "$INSTALL_DIR" ]; then
  read -r -p "Remove $INSTALL_DIR (includes session database)? [y/N] " confirm
  if [[ "$confirm" =~ ^[Yy]$ ]]; then
    rm -rf "$INSTALL_DIR"
    echo "Removed: $INSTALL_DIR"
  else
    echo "Kept: $INSTALL_DIR (data preserved)"
  fi
fi

# 7. Optionally remove mode file
MODE_FILE="$HOME/.claude/mem-mode"
if [ -f "$MODE_FILE" ]; then
  read -r -p "Remove $MODE_FILE? [y/N] " confirm
  [[ "$confirm" =~ ^[Yy]$ ]] && rm -f "$MODE_FILE" && echo "Removed: $MODE_FILE"
fi

echo ""
echo "claude-lazy-mem uninstalled."
echo "Start a new Claude Code session for changes to take effect."
