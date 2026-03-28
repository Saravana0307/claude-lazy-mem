#!/usr/bin/env bash
# install.sh — Install claude-lazy-mem
# Usage: bash install.sh [--dry-run]

set -e

DRY_RUN=false
[ "$1" = "--dry-run" ] && DRY_RUN=true

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="$HOME/.claude-lazy-mem"
CLAUDE_HOOKS_DIR="$HOME/.claude/hooks"
CLAUDE_SKILLS_DIR="$HOME/.claude/skills"
MODE_FILE="$HOME/.claude/mem-mode"

if $DRY_RUN; then
  echo "=== claude-lazy-mem dry-run ==="
  python3 "$REPO_DIR/scripts/patch-hooks-json.py" --dry-run
  exit 0
fi

echo "Installing claude-lazy-mem..."

# 1. Create install directory
mkdir -p "$INSTALL_DIR/hooks" "$INSTALL_DIR/bin" "$INSTALL_DIR/scripts" "$INSTALL_DIR/ui" "$INSTALL_DIR/skills"

# 2. Copy files
cp -r "$REPO_DIR/hooks/"*.sh   "$INSTALL_DIR/hooks/"
cp    "$REPO_DIR/bin/"*        "$INSTALL_DIR/bin/"
cp    "$REPO_DIR/scripts/"*.py "$INSTALL_DIR/scripts/"
cp -r "$REPO_DIR/ui/"          "$INSTALL_DIR/"
cp -r "$REPO_DIR/skills/"*.md  "$INSTALL_DIR/skills/"
chmod +x "$INSTALL_DIR/hooks/"*.sh "$INSTALL_DIR/bin/"*

# 3. Symlink hook scripts into ~/.claude/hooks/
mkdir -p "$CLAUDE_HOOKS_DIR"
ln -sf "$INSTALL_DIR/hooks/mem-context-conditional.sh" "$CLAUDE_HOOKS_DIR/mem-context-conditional.sh"
ln -sf "$INSTALL_DIR/hooks/mem-mode-notify.sh"         "$CLAUDE_HOOKS_DIR/mem-mode-notify.sh"
ln -sf "$INSTALL_DIR/hooks/mem-mode-toggle.sh"         "$CLAUDE_HOOKS_DIR/mem-mode-toggle.sh"
ln -sf "$INSTALL_DIR/hooks/patch-mem-hooks.sh"         "$CLAUDE_HOOKS_DIR/patch-mem-hooks.sh"

# 4. Install skills into ~/.claude/skills/
mkdir -p "$CLAUDE_SKILLS_DIR"
for skill in "$INSTALL_DIR/skills/"*.md; do
  ln -sf "$skill" "$CLAUDE_SKILLS_DIR/$(basename "$skill")"
done

# 5. Create flag file (default: lazy) — don't overwrite existing preference
[ -f "$MODE_FILE" ] || echo "lazy" > "$MODE_FILE"

# 6. Patch claude-mem's hooks.json
python3 "$INSTALL_DIR/scripts/patch-hooks-json.py" --patch

# 7. Inject notify hook into ~/.claude/settings.json
python3 "$INSTALL_DIR/scripts/patch-hooks-json.py" --settings

# 8. Append memory mode protocol to ~/.claude/CLAUDE.md
python3 "$INSTALL_DIR/scripts/patch-hooks-json.py" --claude-md

# 9. Initialize the SQLite database
python3 "$INSTALL_DIR/scripts/db.py" summary > /dev/null 2>&1 || true

# 10. Symlink CLI to somewhere on PATH
if [ -d "$HOME/.local/bin" ]; then
  ln -sf "$INSTALL_DIR/bin/lazy-mem" "$HOME/.local/bin/lazy-mem"
  echo "  Linked: lazy-mem → $HOME/.local/bin/lazy-mem"
elif [ -d "/usr/local/bin" ] && [ -w "/usr/local/bin" ]; then
  ln -sf "$INSTALL_DIR/bin/lazy-mem" "/usr/local/bin/lazy-mem"
  echo "  Linked: lazy-mem → /usr/local/bin/lazy-mem"
else
  echo "  Add to PATH manually: export PATH=\"\$PATH:$INSTALL_DIR/bin\""
fi

echo ""
echo "claude-lazy-mem installed successfully!"
echo ""
echo "  Current mode : $(cat "$MODE_FILE")"
echo "  Status       : lazy-mem status"
echo "  Dashboard    : lazy-mem web"
echo "  Doctor check : lazy-mem doctor"
echo "  Skill        : /mem-toggle (mid-session mode switch)"
echo ""
echo "Start a new Claude Code session to activate lazy mode."
