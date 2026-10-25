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
- **Work on `main` only.** Commit and push straight to `main`; no feature branches or pull requests.
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
- **Cash plan (D-056 to D-059):** arithmetic only, never sells. Emergency money is topped up first and is never in a split; the rest water-fills the target bucket in whole rupees. Logic in `friday.core.cash.plan` (pure) and `friday.core.cash.service`.
- **Screens (D-060, D-061):** one screen, one job. A page starts with `PageHeader` (title + actions, no subtitle) and is built from `Section`, `Field`, `DataTable`, `RowActions`, `EmptyState`, `Loading`. **No explanatory prose:** a term that needs defining gets an `InfoTip` (ⓘ, one sentence) next to its label; text under a control is for errors only. No task IDs, CLI commands, data-source names or "coming soon" in the UI; the nav lists only built screens. Small edits in a `Dialog`, big ones on their own page; optional fields behind "More options". Feedback with `toast` (sonner), deletes through `useConfirm()`. Fund rows show name and plan; identifiers live on the fund page. UI words: Model (bucket), Purchase (lot), Purpose (earmark), Investable (deployable), Invest rules (plan settings), Invest (cash plan), Funds (instruments); code and API names stay. Full rules: `docs/ui-redesign.md` §2.
- **Navigation (D-063, D-064):** four screens, Portfolio (Funds | Cash) · Invest · Models (Overview | Backtest per model) · Funds (one page per fund: Overview | Transactions | Details), plus Settings (Invest rules | Data). Link with `fundPath` / `modelPath`; record transactions through `useAddTransaction()`; tabs that change the URL use `RouteTabs`. New screens fit into these before adding a nav item.
- **Plan and option (D-069):** AMFI's scheme master only fills what `NAVAll.txt` leaves blank.
- **NAVs are synced by hand in Phase 1 (D-068):** no scheduler until `friday tick` (Phase 4a).
- Errors are RFC 9457 problem details. The server binds to `127.0.0.1` only.
- Windows is the target OS: keep commands Windows-safe (no `&&` chains in PowerShell 5, `npm.cmd` not `npm.ps1`, LF line endings via `.gitattributes`).

Plain-language overview: `docs/architecture.md` · Phases: `docs/phases.md`
