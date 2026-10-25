# Friday (EDITH repo)

Personal stock analyst / portfolio manager for Indian and US markets, built **mutual funds first** (D-043): Phase 1 is the fund tracker and planner.

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
- **Instruments (D-038):** everything points at `instruments.id`, never at a symbol or ISIN. Pick instruments in the UI with `InstrumentSearch` (pass `kind="mutual_fund"` for fund-only pickers). Instruments are never deleted; a list refresh marks them inactive.
- **NAVs (D-044 to D-046):** stored exactly as published, up to 8 places (`Nav` type); read them with `friday.core.navs.service.nav_series`. Funds in a bucket are tracked automatically.
- **Backtests (D-048 to D-050):** amounts and units are `Decimal`, ratios are floats rounded to 2 places with `engine.figure`. Charts use `components/charts/LineChart` (SVG); numbers there are for drawing only, and every figure shown as text comes from the API.
- **Holdings (D-051 to D-054):** keyed by fund; each buy (lump sum or SIP instalment) is a lot with a stored `units_remaining`. Selling takes units from lots I pick (`lot_sales`), not a transaction type. Logic in `friday.core.holdings.service`; NAV sync adds due SIP instalments.
- Errors are RFC 9457 problem details. The server binds to `127.0.0.1` only.
- Windows is the target OS: keep commands Windows-safe (no `&&` chains in PowerShell 5, `npm.cmd` not `npm.ps1`, LF line endings via `.gitattributes`).

Plain-language overview: `docs/architecture.md` · Phases: `docs/phases.md`
