# Friday (EDITH repo)

Personal stock analyst / portfolio manager for Indian and US markets. Design-stage project.

## Start of every session

1. Read `agents.md` sections 2 (decisions), 3 (current plan) and 5 (open questions).
2. Read the active task board: `docs/tasks/phase-1.md`. Follow the routine in `docs/tasks/README.md`.
3. Work on the task marked `doing`, the one the user names, or ask which to pick.

## Rules

- Only what's in the `agents.md` decision log as **Active** is decided. Library names and data sources elsewhere are proposals until the task that needs them decides.
- Each task starts with its *Decisions* list. Every decision is written under the task and logged as a `D-###` row in `agents.md`.
- Update the board table and the task's detail section together. Commit messages start with the task ID.
- New work found mid-task becomes a new task at the end of the board.

## Development

Commands (all via `just`, see `README.md`): `setup`, `run`, `dev`, `test`, `lint`, `fmt`, `api`, `migrate`, `revision "msg"`, `smoke`.

Conventions (decisions D-029 to D-037):
- **All logic lives in `backend/friday/core/`.** API routes, jobs and (later) the MCP server stay thin.
- **Money is `Decimal`, never `float`.** Store with `DecimalText(scale)`, expose with the `Amount` / `Price` / `Units` / `FxRate` types from `friday.core.schema_types` (2 / 4 / 8 / 6 decimal places). JSON carries amounts as strings; numbers are rejected.
- **Time:** store with `UtcDateTime`, accept `UtcDatetime` in API models (timezone required). Show IST in the UI. A market date is a plain date tied to its exchange.
- **Frontend never does arithmetic on amounts.** Format with `formatMoney`; the backend computes every figure.
- **After changing an endpoint, run `just api`** and commit the regenerated `frontend/src/api/` files (CI fails if they're stale).
- **Schema changes go through Alembic:** change models, then `just revision "what changed"`, review the file, commit it.
- **Instruments (D-038):** everything points at `instruments.id`, never at a symbol or ISIN. Pick instruments in the UI with `InstrumentSearch`. Instruments are never deleted; a list refresh marks them inactive.
- Errors are RFC 9457 problem details. The server binds to `127.0.0.1` only.
- Windows is the target OS: keep commands Windows-safe (no `&&` chains in PowerShell 5, `npm.cmd` not `npm.ps1`, LF line endings via `.gitattributes`).

Plain-language overview: `docs/architecture.md` · Phases: `docs/phases.md`
