# Changelog

## [1.0.0] — 2026-03-28

### Added
- Initial release
- Lazy-load gate: `hooks/mem-context-conditional.sh` replaces claude-mem's expensive context hook
- Session-start notifier: `hooks/mem-mode-notify.sh` emits ~25-token mode status + logs to DB
- Mode toggle: `hooks/mem-mode-toggle.sh` switches lazy↔full
- Patch script: `scripts/patch-hooks-json.py` with `--patch`, `--unpatch`, `--check`, `--dry-run`, `--settings`, `--claude-md` modes
- SQLite session tracking: `scripts/db.py` for session logs, summaries, and project breakdowns
- `install.sh` / `uninstall.sh` one-command setup and teardown
- `bin/lazy-mem` CLI: status, toggle, lazy, full, benchmark, ui, doctor
- Web dashboard: `ui/server.py` + `ui/templates/index.html` + `ui/static/` (port 7124)
  - Summary cards (sessions, tokens saved, cost saved)
  - Sessions over time chart (lazy vs full, stacked bar)
  - Cumulative savings chart (area)
  - Project breakdown table
  - Session history table
  - Mode toggle from UI
  - Health status (patch check)
- Update-resilience: patch-check warning injected at session start
- Dry-run install preview
