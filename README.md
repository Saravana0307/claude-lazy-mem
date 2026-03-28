# claude-lazy-mem

> Gate claude-mem context loading per session — lazy by default, full when you need it.

[claude-mem](https://github.com/thedotmack/claude-mem) is great, but it loads **20–30k tokens** of memory context at every session start — even for a quick 5-minute task. `claude-lazy-mem` makes context loading **opt-in**: Claude asks once at the start of each session whether to load memory. If you say no, zero extra tokens are loaded. You can still use `mem-search` and `smart-explore` skills on demand.

---

## Features

- **Lazy by default** — no context loaded unless you ask for it
- **Per-session choice** — Claude asks once at session start, non-intrusively
- **CLI toggle** — `lazy-mem full` before a deep work session; `lazy-mem lazy` to go back
- **Web dashboard** — track savings, session history, and mode breakdowns at `localhost:7124`
- **Update-resilient** — detects when a plugin update breaks the patch and warns you
- **Zero dependencies** — Python 3 stdlib only, no pip install needed

---

## Install

```bash
git clone https://github.com/Saravana0307/claude-lazy-mem
cd claude-lazy-mem
bash install.sh
```

### Preview before installing

```bash
bash install.sh --dry-run
```

### Requirements

- Claude Code with [`claude-mem@thedotmack`](https://github.com/thedotmack/claude-mem) installed
- Python 3 (stdlib only)
- bash

---

## Usage

```bash
lazy-mem status        # current mode + savings summary
lazy-mem toggle        # switch lazy↔full
lazy-mem lazy          # set lazy mode (default)
lazy-mem full          # set full mode
lazy-mem benchmark     # detailed token savings report
lazy-mem ui            # open web dashboard at localhost:7124
lazy-mem doctor        # verify all hooks are correctly set up
```

---

## How It Works

claude-mem's `SessionStart` hook normally calls:
```
worker-service.cjs hook claude-code context   ← injects 20–30k tokens
```

`claude-lazy-mem` replaces this with a small wrapper that checks `~/.claude/mem-mode`:

| Mode | Behavior |
|------|----------|
| `lazy` (default) | Exits immediately — zero tokens loaded |
| `full` | Delegates to the original hook unchanged |

A lightweight notifier hook (~25 tokens) tells Claude the active mode so it knows whether to ask about memory at session start.

### Session flow

**Lazy mode (default):**
```
Session starts
 └─ [lazy-mem] LAZY MODE — memory context NOT loaded.
    Claude: "Memory mode is lazy. Load context for this session? (y/n)"
    User: "no"  → proceed fresh, 0 memory tokens
    User: "yes" → Claude runs mem-search skill (~2–5k tokens, targeted)
```

**Full mode:**
```
Session starts
 └─ worker-service loads full context (~20–30k tokens)
    [lazy-mem] FULL MODE — context auto-loaded.
    Claude proceeds normally
```

---

## Web Dashboard

```bash
lazy-mem ui
```

Opens `http://localhost:7124` with:

- **Mode toggle** — switch lazy/full without the CLI
- **Summary cards** — total sessions, lazy %, tokens saved, cost saved
- **Session timeline** — daily lazy vs full session counts (7d / 30d / 90d)
- **Cumulative savings chart** — tokens saved over time
- **Project breakdown** — per-project savings table
- **Session history** — sortable table with mode, tokens, cost per session
- **Health status** — verifies hooks.json patch is in place

---

## Benchmark

> Populate after a week of use — real numbers from your setup.

| Metric | Value |
|--------|-------|
| Sessions tracked | — |
| Lazy sessions | — |
| Avg context size (full mode) | — |
| Estimated tokens saved | — |
| Estimated cost saved | — |

---

## After Plugin Updates

When `claude update` upgrades claude-mem, the `hooks.json` patch gets overwritten. Claude will warn you at the next session start:

```
[lazy-mem] WARNING: claude-mem hooks.json patch is missing. Run: lazy-mem doctor
```

Re-apply the patch:

```bash
lazy-mem doctor
# or directly:
bash ~/.claude/hooks/patch-mem-hooks.sh
```

---

## Uninstall

```bash
bash uninstall.sh
```

Restores `hooks.json`, removes entries from `settings.json` and `CLAUDE.md`, and optionally deletes the session database.

---

## Token Hygiene Tips

Beyond lazy-mem, these habits reduce token usage significantly:

1. **`mem-search` over full context** — 5–10× cheaper for targeted memory lookups
2. **`smart-explore` over Read** — 4–8× cheaper for code understanding (AST-based)
3. **`/compact` discipline** — run when conversation approaches 80k tokens
4. **[RTK](https://github.com/saravanak0307/rtk)** — auto-rewrites bash commands for 60–90% output reduction

---

## License

MIT
