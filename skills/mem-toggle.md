You are executing the mem-toggle skill for claude-lazy-mem.

## What this skill does

Toggles or sets the claude-lazy-mem memory mode between `lazy` and `full`.

## Steps

1. Check the current mode:
   ```bash
   cat ~/.claude/mem-mode
   ```

2. Based on the user's intent:
   - If they said "lazy", "go lazy", "fresh session", "no memory": set lazy
     ```bash
     bash ~/.claude/hooks/mem-mode-toggle.sh lazy
     ```
   - If they said "full", "load memory", "enable memory", "full mode": set full
     ```bash
     bash ~/.claude/hooks/mem-mode-toggle.sh full
     ```
   - If they said "toggle" or no specific mode: toggle current
     ```bash
     bash ~/.claude/hooks/mem-mode-toggle.sh
     ```

3. If switching to **full** mode and the user wants memory context now (not just next session):
   - Use the `mem-search` skill immediately with a relevant query based on what the user is working on
   - Summarize what you find before proceeding

4. Report the result clearly:
   - New mode
   - Whether it takes effect immediately (full→lazy: yes) or at next session start (lazy→full for auto-load)
   - In full mode: remind that context auto-loads at next session start, but mem-search loads it now

## Notes
- Mode changes to `lazy` take effect immediately for context loading
- Mode changes to `full` mean context auto-loads at the **next** session start
- In any mode, `mem-search` and `smart-explore` skills always work on demand
