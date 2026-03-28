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
<!-- lazy-mem-end -->
