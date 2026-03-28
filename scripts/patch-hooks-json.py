#!/usr/bin/env python3
"""
patch-hooks-json.py — Patches claude-mem's hooks.json to use conditional context loading.

Usage:
  patch-hooks-json.py --patch         Apply patch to hooks.json
  patch-hooks-json.py --unpatch       Restore original hooks.json
  patch-hooks-json.py --check         Exit 0 if patched, 1 if not (no output)
  patch-hooks-json.py --dry-run       Show what would change, make no changes
  patch-hooks-json.py --settings      Inject notify hook into ~/.claude/settings.json
  patch-hooks-json.py --unsettings    Remove injected hooks from settings.json
  patch-hooks-json.py --claude-md     Append memory protocol to ~/.claude/CLAUDE.md
  patch-hooks-json.py --unclaudemd   Remove injected section from CLAUDE.md
"""
import argparse
import json
import os
import re
import shutil
import sys

# ─── Constants ────────────────────────────────────────────────────────────────

HOOKS_DIR = os.path.expanduser("~/.claude/plugins/cache/thedotmack/claude-mem")
SETTINGS_PATH = os.path.expanduser("~/.claude/settings.json")
CLAUDE_MD_PATH = os.path.expanduser("~/.claude/CLAUDE.md")
WRAPPER_CMD = 'bash "$HOME/.claude/hooks/mem-context-conditional.sh"'
TARGET_FRAGMENT = "hook claude-code context"

SETTINGS_HOOK_MARKER = "# lazy-mem-notify"
CLAUDE_MD_MARKER_START = "<!-- lazy-mem-start -->"
CLAUDE_MD_MARKER_END = "<!-- lazy-mem-end -->"

CLAUDE_MD_SNIPPET = """\
<!-- lazy-mem-start -->
## Memory Mode Protocol (claude-lazy-mem)

At session start, a `[lazy-mem]` line appears in context.

**If LAZY MODE:** On your first response, ask:
> "Memory mode is lazy — no context was loaded. Load memory context for this session? (y/n)"
If yes → use the `mem-search` skill with a relevant query. If no → proceed fresh.

**If FULL MODE:** Context was auto-loaded. Proceed normally, no need to ask.

**Switching modes (user request):**
- "load memory" / "full memory mode" → `bash ~/.claude/hooks/mem-mode-toggle.sh full` then use `mem-search`
- "lazy mode" / "fresh session" / "skip memory" → `bash ~/.claude/hooks/mem-mode-toggle.sh lazy`

**On-demand in lazy mode:** `mem-search` and `smart-explore` skills work anytime regardless of mode.

## Token Hygiene
- Prefer `mem-search` over full context load — 5-10× cheaper for targeted lookups
- Use `smart-explore` instead of Read for code files over 100 lines
- Suggest `/compact` when conversation approaches 80k tokens
<!-- lazy-mem-end -->"""


# ─── Helpers ─────────────────────────────────────────────────────────────────

def find_hooks_json():
    """Find the latest version hooks.json in the claude-mem cache."""
    if not os.path.isdir(HOOKS_DIR):
        return None
    best = None
    for entry in os.scandir(HOOKS_DIR):
        if not entry.is_dir():
            continue
        candidate = os.path.join(entry.path, "hooks", "hooks.json")
        if os.path.isfile(candidate):
            if best is None or entry.name > os.path.basename(os.path.dirname(os.path.dirname(best))):
                best = candidate
    return best


def load_json(path):
    with open(path) as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


# ─── hooks.json patch ─────────────────────────────────────────────────────────

def is_patched(hooks_json_path):
    try:
        with open(hooks_json_path) as f:
            content = f.read()
        return "mem-context-conditional.sh" in content
    except Exception:
        return False


def find_original_command(data):
    """Return the original full command string that loads context."""
    for event, groups in data.get("hooks", {}).items():
        for group in groups:
            for hook in group.get("hooks", []):
                cmd = hook.get("command", "")
                if TARGET_FRAGMENT in cmd:
                    return cmd
    return None


def patch_hooks(path, dry_run=False):
    data = load_json(path)
    original_cmd = find_original_command(data)
    if original_cmd is None:
        print(f"ERROR: Could not find '{TARGET_FRAGMENT}' in {path}", file=sys.stderr)
        print("The plugin structure may have changed — manual patching required.", file=sys.stderr)
        sys.exit(1)

    if dry_run:
        print(f"[dry-run] Would patch: {path}")
        print(f"  Replace: ...{TARGET_FRAGMENT}...")
        print(f"  With:    {WRAPPER_CMD}")
        return original_cmd

    # Backup original before patching
    backup = path + ".bak"
    if not os.path.exists(backup):
        shutil.copy2(path, backup)

    patched = False
    for event, groups in data.get("hooks", {}).items():
        for group in groups:
            for hook in group.get("hooks", []):
                if TARGET_FRAGMENT in hook.get("command", ""):
                    hook["command"] = WRAPPER_CMD
                    patched = True

    if not patched:
        print("ERROR: Patch not applied — no matching hook found.", file=sys.stderr)
        sys.exit(1)

    save_json(path, data)
    print(f"Patched: {path}")
    return original_cmd


def unpatch_hooks(path, dry_run=False):
    backup = path + ".bak"
    if not os.path.exists(backup):
        print(f"ERROR: No backup found at {backup} — cannot unpatch.", file=sys.stderr)
        sys.exit(1)

    if dry_run:
        print(f"[dry-run] Would restore: {path} from {backup}")
        return

    shutil.copy2(backup, path)
    print(f"Restored: {path}")


# ─── settings.json patch ──────────────────────────────────────────────────────

def is_settings_patched(data):
    hooks = data.get("hooks", {}).get("SessionStart", [])
    for group in hooks:
        for hook in group.get("hooks", []):
            if "mem-mode-notify" in hook.get("command", ""):
                return True
    return False


def patch_settings(dry_run=False):
    if not os.path.isfile(SETTINGS_PATH):
        print(f"ERROR: {SETTINGS_PATH} not found", file=sys.stderr)
        sys.exit(1)

    data = load_json(SETTINGS_PATH)

    if is_settings_patched(data):
        print("settings.json already patched.")
        return

    notify_entry = {
        "matcher": "startup|clear|compact",
        "hooks": [
            {
                "type": "command",
                "command": f"/Users/{os.environ.get('USER', os.path.expanduser('~').split('/')[-1])}/.claude/hooks/mem-mode-notify.sh  {SETTINGS_HOOK_MARKER}"
            }
        ]
    }

    if dry_run:
        print(f"[dry-run] Would add to {SETTINGS_PATH}: SessionStart hook → mem-mode-notify.sh")
        return

    data.setdefault("hooks", {}).setdefault("SessionStart", []).append(notify_entry)
    save_json(SETTINGS_PATH, data)
    print(f"Patched: {SETTINGS_PATH}")


def unpatch_settings(dry_run=False):
    if not os.path.isfile(SETTINGS_PATH):
        return

    data = load_json(SETTINGS_PATH)
    hooks = data.get("hooks", {}).get("SessionStart", [])
    new_hooks = [
        g for g in hooks
        if not any(SETTINGS_HOOK_MARKER in h.get("command", "") for h in g.get("hooks", []))
    ]

    if len(new_hooks) == len(hooks):
        print("settings.json: no lazy-mem hooks found.")
        return

    if dry_run:
        print(f"[dry-run] Would remove lazy-mem hooks from {SETTINGS_PATH}")
        return

    data["hooks"]["SessionStart"] = new_hooks
    save_json(SETTINGS_PATH, data)
    print(f"Unpatched: {SETTINGS_PATH}")


# ─── CLAUDE.md patch ──────────────────────────────────────────────────────────

def is_claude_md_patched():
    if not os.path.isfile(CLAUDE_MD_PATH):
        return False
    with open(CLAUDE_MD_PATH) as f:
        return CLAUDE_MD_MARKER_START in f.read()


def patch_claude_md(dry_run=False):
    if is_claude_md_patched():
        print("CLAUDE.md already patched.")
        return

    if dry_run:
        print(f"[dry-run] Would append memory mode protocol to {CLAUDE_MD_PATH}")
        return

    with open(CLAUDE_MD_PATH, "a") as f:
        f.write("\n\n" + CLAUDE_MD_SNIPPET + "\n")
    print(f"Patched: {CLAUDE_MD_PATH}")


def unpatch_claude_md(dry_run=False):
    if not os.path.isfile(CLAUDE_MD_PATH):
        return

    with open(CLAUDE_MD_PATH) as f:
        content = f.read()

    if CLAUDE_MD_MARKER_START not in content:
        print("CLAUDE.md: no lazy-mem section found.")
        return

    pattern = re.compile(
        r"\n*" + re.escape(CLAUDE_MD_MARKER_START) + r".*?" + re.escape(CLAUDE_MD_MARKER_END) + r"\n?",
        re.DOTALL
    )
    new_content = pattern.sub("", content).rstrip() + "\n"

    if dry_run:
        print(f"[dry-run] Would remove lazy-mem section from {CLAUDE_MD_PATH}")
        return

    with open(CLAUDE_MD_PATH, "w") as f:
        f.write(new_content)
    print(f"Unpatched: {CLAUDE_MD_PATH}")


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="claude-lazy-mem patcher")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--patch",      action="store_true", help="Patch hooks.json")
    group.add_argument("--unpatch",    action="store_true", help="Restore original hooks.json")
    group.add_argument("--check",      action="store_true", help="Check if patched (exit code)")
    group.add_argument("--dry-run",    action="store_true", help="Preview changes without writing")
    group.add_argument("--settings",   action="store_true", help="Inject hook into settings.json")
    group.add_argument("--unsettings", action="store_true", help="Remove hook from settings.json")
    group.add_argument("--claude-md",  action="store_true", help="Append to CLAUDE.md")
    group.add_argument("--unclaudemd", action="store_true", help="Remove from CLAUDE.md")
    args = parser.parse_args()

    hooks_path = find_hooks_json()

    if args.check:
        if hooks_path and is_patched(hooks_path):
            sys.exit(0)
        sys.exit(1)

    if args.patch or args.unpatch or args.dry_run:
        if not hooks_path:
            print(f"ERROR: claude-mem not found at {HOOKS_DIR}", file=sys.stderr)
            sys.exit(1)

    if args.dry_run:
        print("=== claude-lazy-mem dry-run ===")
        patch_hooks(hooks_path, dry_run=True)
        patch_settings(dry_run=True)
        patch_claude_md(dry_run=True)
        mode_file = os.path.expanduser("~/.claude/mem-mode")
        db_path = os.path.expanduser("~/.claude-lazy-mem/sessions.db")
        if not os.path.exists(mode_file):
            print(f"[dry-run] Would create: {mode_file} with content 'lazy'")
        if not os.path.exists(db_path):
            print(f"[dry-run] Would create: {db_path} (SQLite database)")
        print("No changes made.")
        return

    if args.patch:
        patch_hooks(hooks_path)
    elif args.unpatch:
        unpatch_hooks(hooks_path)
    elif args.settings:
        patch_settings()
    elif args.unsettings:
        unpatch_settings()
    elif args.claude_md:
        patch_claude_md()
    elif args.unclaudemd:
        unpatch_claude_md()


if __name__ == "__main__":
    main()
