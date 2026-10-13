# Contributing to steam-achievement-unlocker-offline

Thanks for poking at the tater. This is an offline Steam achievement unlocker
for Windows — it edits local `UserGameStats` blobs and the Steam
`appcache/stats` cache so achievements show as unlocked without a live
Steam connection. No network calls, no Valve services, no DRM bypass of
anything you don't already own.

## Ground rules

1. **Offline only.** PRs that add network calls to Steam Community, CM
   servers, or anything that touches Valve infrastructure get closed
   without discussion. The whole point is that this runs against files on
   disk.
2. **Backups first.** Any handler that mutates `UserGameStats_*.bin` or
   `appcache/stats/UserGameStatsSchema_*.bin` MUST write a timestamped
   backup under `data/backups/` before the write. The `SteamStateWriter`
   service already does this — use it, don't roll your own.
3. **Schema-driven.** Achievement IDs come from the parsed schema, never
   hardcoded. If a game's schema is missing, the handler logs and skips.
4. **No new deps without a reason in the PR body.** We ship with a
   short dependency list on purpose.

## Dev setup

```powershell
py -3.11 -m venv .venv
.venv\Scripts\activate
pip install -e .[dev]
pytest -q
ruff check .
mypy src
```

## Repo layout

- `src/sau/bootstrap/` — entry points, CLI, path discovery
- `src/sau/core/` — engine, schema parser, stats codec
- `src/sau/handlers/` — one handler per achievement operation
- `src/sau/services/` — filesystem, backup, logging services
- `src/sau/models/` — dataclasses for schema, stats, config
- `src/sau/utils/` — small pure helpers
- `tests/` — pytest, golden-file based where possible

## Style

- `ruff` with the repo config. Line length 100.
- Type hints everywhere. `mypy --strict` on `src/sau/core/`.
- No prints in library code — use the `loguru`-free stdlib logger via
  `sau.services.logging_service`.

## Commit messages

`handlers: fix schema fallback when appid has no UserGameStats`

Prefixes: `bootstrap:`, `core:`, `handlers:`, `services:`, `models:`,
`utils:`, `tests:`, `docs:`.