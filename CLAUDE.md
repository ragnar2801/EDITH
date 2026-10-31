# Friday (EDITH repo)

Personal portfolio tracker for Indian mutual funds, running locally on Windows.

## Rules

- **Work on `main` only.** Commit and push straight to `main`; no feature branches or pull requests.
- Commit messages say what changed in one line, then why if it isn't obvious.

## Development

Commands (all via `just`, see `README.md`): `setup`, `run`, `dev`, `test`, `lint`, `fmt`, `api`, `migrate`, `revision "msg"`, `smoke`.

Conventions:
- **All logic lives in `backend/friday/core/`.** API routes and jobs stay thin.
- **Money is `Decimal`, never `float`.** Store with `DecimalText(scale)`, expose with the `Amount` / `Price` / `Units` / `FxRate` types from `friday.core.schema_types` (2 / 4 / 8 / 6 decimal places). JSON carries amounts as strings; numbers are rejected.
- **Time:** store with `UtcDateTime`, accept `UtcDatetime` in API models (timezone required). Show IST in the UI. A market date is a plain date tied to its exchange.
- **Frontend never does arithmetic on amounts.** Format with `formatMoney`; the backend computes every figure.
- **After changing an endpoint, run `just api`** and commit the regenerated `frontend/src/api/` files (CI fails if they're stale).
- **Schema changes go through Alembic:** change models, then `just revision "what changed"`, review the file, commit it.
- **Instruments:** everything points at `instruments.id`, never at a symbol or ISIN. Pick instruments in the UI with `InstrumentSearch` (pass `kind="mutual_fund"` for fund-only pickers). Instruments are never deleted; a list refresh marks them inactive.
- **NAVs:** stored exactly as published, up to 8 places (`Nav` type); read them with `friday.core.navs.service.nav_series`. Funds in a bucket are tracked automatically. NAVs are synced by hand; there is no scheduler.
- **Plan and option:** AMFI's scheme master only fills what `NAVAll.txt` leaves blank.
- **Backtests:** amounts and units are `Decimal`, ratios are floats rounded to 2 places with `engine.figure`. Charts use `components/charts/LineChart` (SVG); numbers there are for drawing only, and every figure shown as text comes from the API. A run may carry a `split` that never changes the model; compare two runs with `GET /backtests/{id}/compare`. The split search (`friday.core.backtest.search`, numpy) only ranks; figures shown come from the engine.
- **Holdings:** keyed by fund; each buy (lump sum or SIP instalment) is a lot with a stored `units_remaining`. Selling takes units from lots I pick (`lot_sales`), not a transaction type. Logic in `friday.core.holdings.service`; NAV sync adds due SIP instalments.
- **Cash plan:** arithmetic only, never sells. Emergency money is topped up first and is never in a split; the rest water-fills the target bucket in whole rupees. Logic in `friday.core.cash.plan` (pure) and `friday.core.cash.service`.
- **Portfolio:** value at the latest stored NAV; realised + unrealised = gain to the paisa; XIRR shown after a year; the benchmark gets the same dated flows (`ahead` = gain − its gain). Day = each fund's move between its own last two NAVs. History: value, invested and benchmark per NAV date, gain and time-weighted return over a range. Logic in `friday.core.portfolio.returns` and `.history` (pure) and `friday.core.portfolio.service`; endpoints `GET /portfolio` and `GET /portfolio/history`.
- **FM import:** the FM app (Flutter, phone) is where fund purchases and sales are recorded; Friday keeps a read-only copy. Its phone pushes a copy of its whole database to `friday.core.fm.receiver` (FM's own `GET /health` / `POST /db` protocol, `x-sync-token`). `friday.core.fm.snapshot` reads FM's tables by column name, so new FM columns are ignored; each import replaces every lot with `source = "fm"` in one transaction, and those lots can't be edited, sold or deleted here. Logic in `friday.core.fm.service`.
- Errors are RFC 9457 problem details. The server binds to `127.0.0.1` only; the FM receiver (off unless `FRIDAY_FM_PUSH` is set) is the one listener on the network, on its own port, serving nothing but the push.
- Windows is the target OS: keep commands Windows-safe (no `&&` chains in PowerShell 5, `npm.cmd` not `npm.ps1`, LF line endings via `.gitattributes`).

## Screens

- **One screen, one job.** A page starts with `PageHeader` (title + actions, no subtitle) and is built from `Section`, `Field`, `DataTable`, `RowActions`, `EmptyState`, `Loading`.
- **No explanatory prose.** A term that needs defining gets an `InfoTip` (ⓘ, one sentence) next to its label. Text under a control is for errors only; formats go in placeholders.
- **No build talk in the UI:** no task IDs, CLI commands, data-source names, "coming soon" or placeholder pages. The nav lists only built screens.
- **Verbs on buttons, nouns on titles.**
- **Small edits in a `Dialog`, big ones on their own page;** optional fields behind "More options".
- **Feedback with `toast` (sonner),** with Undo where the API allows it. Deletes go through `useConfirm()`.
- **Empty state:** icon, one short line, one button.
- **Numbers look like numbers:** right-aligned, tabular figures, one `DataTable` everywhere. Row click opens the detail; row actions live in a `…` menu.
- **Identity, not identifiers.** Fund rows show name and plan; AMFI code, ISIN and the rest live on the fund page.
- **UI words:** Model (bucket), Purchase (lot), Purpose (earmark), Investable (deployable), Invest rules (plan settings), Invest (cash plan), Funds (instruments). Code and API names stay.
- **Navigation:** Portfolio (Funds | Cash) · Invest · Models (Overview | Backtest | Optimise per model) · Funds (one page per fund: Overview | Transactions | Details), plus Settings (Invest rules | Data). Link with `fundPath` / `modelPath`; record transactions through `useAddTransaction()`; tabs that change the URL use `RouteTabs`. New screens fit into these before adding a nav item.
