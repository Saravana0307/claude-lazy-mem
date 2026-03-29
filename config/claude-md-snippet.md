<!-- lazy-mem-start -->
## Memory Mode Protocol (claude-lazy-mem)

At session start, a `[lazy-mem]` line appears in context.

**If LAZY MODE:** On your first response, ask:
> "Memory mode is lazy — no context was loaded. Load memory context for this session? (y/n)"

If yes → run this bash command and read the output (full context load):
```
_R="$HOME/.claude/plugins/marketplaces/thedotmack/plugin" && node "$_R/scripts/bun-runner.js" "$_R/scripts/worker-service.cjs" hook claude-code context
```
If no → proceed fresh.

**If FULL MODE:** Context was auto-loaded at session start. Proceed normally.

**Mid-session context load (any time user says "load memory", "load context", "show memory"):**
Run the same bash command above — output is the full memory context.

**Switching mode for future sessions:**
- "full mode" / "always load memory" → `bash ~/.claude/hooks/mem-mode-toggle.sh full`
  Also run the context load command immediately to get context in the current session.
- "lazy mode" / "go back to lazy" / "fresh session" → `bash ~/.claude/hooks/mem-mode-toggle.sh lazy`

## Token Hygiene
- Use `smart-explore` instead of Read for code files over 100 lines
- Suggest `/compact` when conversation approaches 80k tokens
<!-- lazy-mem-end -->
