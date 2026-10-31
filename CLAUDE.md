# Friday (EDITH repo)

Personal portfolio tracker for Indian mutual funds, running locally on Windows.

## Rules

- **Work on `main` only.** Commit and push straight to `main`; no feature branches or pull requests.
- Commit messages say what changed in one line, then why if it isn't obvious.

## Development

**Real data is off limits.** My portfolio lives in `%LOCALAPPDATA%\Friday`: never read, query, copy or screenshot it, and never run `just run` or `friday` commands against it. Run and check the app with `just dev`, which uses the made-up database in `dev/` (`just demo` rebuilds it); `friday demo` fills an empty database for anything else.

Commands (all via `just`, see `README.md`): `setup`, `run`, `dev`, `test`, `lint`, `fmt`, `api`, `migrate`, `revision "msg"`, `smoke`.

Conventions:
- **All logic lives in `backend/friday/core/`.** API routes and jobs stay thin.
- **Money is `Decimal`, never `float`.** Store with `DecimalText(scale)`, expose with the `Amount` / `Price` / `Units` / `FxRate` types from `friday.core.schema_types` (2 / 4 / 8 / 6 decimal places). JSON carries amounts as strings; numbers are rejected.
- **Time:** store with `UtcDateTime`, accept `UtcDatetime` in API models (timezone required). Show IST in the UI. A market date is a plain date tied to its exchange.
- **Frontend never does arithmetic on amounts.** Format with `formatMoney`; the backend computes every figure.
- **After changing an endpoint, run `just api`** and commit the regenerated `frontend/src/api/` files (CI fails if they're stale).
- **Schema changes go through Alembic:** change models, then `just revision "what changed"`, review the file, commit it.
- **Instruments:** everything points at `instruments.id`, never at a symbol or ISIN. Pick instruments in the UI with `InstrumentSearch` (pass `kind="mutual_fund"` for fund-only pickers). Instruments are never deleted; a list refresh marks them inactive.
- **NAVs:** stored exactly as published, up to 8 places (`Nav` type); read them with `friday.core.navs.service.nav_series`. Funds in a model are tracked automatically. NAVs are synced by hand; there is no scheduler.
- **Plan and option:** AMFI's scheme master only fills what `NAVAll.txt` leaves blank.
- **Backtests:** amounts and units are `Decimal`, ratios are floats rounded to 2 places with `engine.figure`. Charts use `components/charts/LineChart` (SVG); numbers there are for drawing only, and every figure shown as text comes from the API. A run may carry a `split` that never changes the model; compare two runs with `GET /backtests/{id}/compare`. The split search (`friday.core.backtest.search`, numpy) only ranks; figures shown come from the engine.
- **Holdings:** keyed by fund; each buy (lump sum or SIP instalment) is a lot with a stored `units_remaining`. Selling takes units from lots I pick (`lot_sales`), not a transaction type. Logic in `friday.core.holdings.service`; NAV sync adds due SIP instalments. A lot or SIP may be in a bucket (an instalment is in its SIP's); reads take a `Scope`: one bucket, real money (`None`: no bucket or a real one) or `ANY`.
- **Models and buckets:** a model is a split of funds with weights (`friday.core.models`), for backtests and to invest towards. A bucket (`friday.core.buckets`) is money set aside for a goal: purchases and SIPs belong to it, and it follows one model (or none yet). A paper bucket holds pretend purchases at real NAVs; it's left out of real money everywhere (totals, holdings list, emergency money) and only shown on its own. Real and paper never mix: a purchase can't move between them, and a bucket switches only while empty. Deleting a paper bucket deletes its purchases; deleting a real one leaves them in no bucket.
- **Cash plan:** arithmetic only, never sells. Plans one bucket towards its model, counting only what the bucket holds. Emergency money is topped up first (real buckets) and is never in a split; the rest water-fills the model in whole rupees. A paper bucket's plan uses the amount typed, never staggers, and `POST /plan/paper` buys it at each fund's latest NAV. Logic in `friday.core.cash.plan` (pure) and `friday.core.cash.service`.
- **Portfolio:** value at the latest stored NAV; realised + unrealised = gain to the paisa; XIRR shown after a year; the benchmark gets the same dated flows (`ahead` = gain − its gain). Day = each fund's move between its own last two NAVs. History: value, invested and benchmark per NAV date, gain and time-weighted return over a range. Real money, or one bucket (`bucket_id`); a bucket with a model also gets drift and the same flows split by the model's weights, never rebalanced (`ahead_of_model`). Logic in `friday.core.portfolio.returns` and `.history` (pure) and `friday.core.portfolio.service`; endpoints `GET /portfolio` and `GET /portfolio/history`.
- **Compare:** funds, buckets or models side by side over the dates they all share (the youngest sets the start; `start` leaves younger ones out instead). Each becomes a series that works like a NAV: a fund's NAVs, a bucket's time-weighted growth (`friday.core.portfolio.service.growth`, so when money went in doesn't count; what it made is in `money`), a model's lump sum split by its weights and rebalanced as it says (`compare.service.model_growth`). Trailing and calendar-year returns use each one's whole history up to the same date. Rolling returns, risk, capture and correlation (weekly returns; the benchmark is id 0) cover the shared dates only. Logic in `friday.core.compare.figures` (pure) and `.service`; endpoints `GET /compare/funds`, `/compare/buckets`, `/compare/models`.
- **FM import:** the FM app (Flutter, phone; repo `../FM`) is where fund purchases and sales are recorded; Friday keeps a read-only copy. FM's "Sync to Friday" (`friday_lots_export.dart`) POSTs every investment lot as JSON (`format: fm-lots`, `version: 1`): FM's own lot row with its `security`, `account`, `currency`, `acquisition`, `bucket` (`id`, `name`; null for none) and `sales` nested in. A purchase goes in the Friday bucket tied to FM's bucket id (`fm_bucket`: made on first sight, or a real bucket of the same name taken over); FM names those buckets. `friday.core.fm.feed` reads fields by name, so new FM fields are ignored; bump `version` on both sides only when a field Friday reads is renamed or removed. Each sync deletes every lot with `source = "fm"` (and its sales) and adds the feed's, in one transaction; lots entered in Friday stay, and FM lots can't be edited, sold or deleted here. The feed isn't kept. Logic in `friday.core.fm.service`.
- Errors are RFC 9457 problem details. The server binds to `127.0.0.1` only; the FM receiver (`friday.core.fm.receiver`, port 8090, token in `fm/token.txt` under the data folder; tests and smoke turn it off) is the one listener on the network, serving only `GET /health` and `POST /lots`.
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
- **UI words:** Purchase (lot), Paper (pretend money in a paper bucket), Purpose (earmark), Investable (deployable), Invest rules (plan settings), Invest (cash plan), Funds (instruments). Code and API names stay.
- **Navigation:** Portfolio (Funds, for real money or one bucket via `?bucket=` | Buckets | Cash) · Invest · Models (Overview | Backtest | Optimise per model) · Funds (one page per fund: Overview | Transactions | Details) · Compare (Funds | Buckets | Models, picked in `?ids=`), plus Settings (Invest rules | Data). Link with `fundPath` / `modelPath` / `bucketPath` / `investPath` / `comparePath`; record transactions through `useAddTransaction()`; tabs that change the URL use `RouteTabs`. New screens fit into these before adding a nav item.
