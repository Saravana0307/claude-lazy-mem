You are executing the mem-toggle skill for claude-lazy-mem.

## What this skill does

Toggles or sets the claude-lazy-mem memory mode, and loads full context immediately when switching to full.

## Steps

1. Check the current mode:
   ```bash
   cat ~/.claude/mem-mode
   ```

2. Based on the user's intent:
   - "lazy", "go lazy", "fresh session", "no memory" → set lazy:
     ```bash
     bash ~/.claude/hooks/mem-mode-toggle.sh lazy
     ```
   - "full", "load memory", "enable memory", "full mode" → set full:
     ```bash
     bash ~/.claude/hooks/mem-mode-toggle.sh full
     ```
   - "toggle" or no specific mode → toggle:
     ```bash
     bash ~/.claude/hooks/mem-mode-toggle.sh
     ```

3. **If switching TO full mode**, load context immediately in the current session:
   ```bash
   _R="$HOME/.claude/plugins/marketplaces/thedotmack/plugin" && node "$_R/scripts/bun-runner.js" "$_R/scripts/worker-service.cjs" hook claude-code context
   ```
   Read the output — it is the memory context. Summarize what you found before proceeding.

4. Report the result:
   - New mode
   - For full: context is now loaded (from the command above) AND will auto-load at future session starts
   - For lazy: no context will auto-load at future session starts; use "load memory" to load on demand anytime

## Notes
- In any mode, you can always load context on demand by running the bash command in step 3
- `smart-explore` skill works anytime for code structure search regardless of mode
