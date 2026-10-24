# Phase 1 — Tracker · Task board

> **Goal:** see my whole portfolio in one place with correct numbers. No AI. Prices update daily by themselves.
> **Exit:** all my real holdings are in, prices update daily, numbers match my broker statements ([`phases.md`](../phases.md)).
> **Already fixed:** React frontend + Python backend (D-023) · SQLite on the laptop (D-013) · free data only (D-012) · scheduled fetch + backfill (D-022) · Windows + Task Scheduler (D-027).
> Everything else is decided **inside the task that needs it** (see each task's *Decisions* list). How this board works: [`README.md`](README.md)

**Board version:** 2 (regenerated 2026-10-24 as feature-sized tasks; the first draft's IDs are void) · **Done:** 0 / 10

---

## Board

| ID | Task | Kind | Owner | Status | Depends on |
|----|------|------|-------|--------|------------|
| T1-01 | Foundation: app skeleton running on Windows | Infra | Claude | doing | — |
| T1-02 | Instruments: find any stock, fund or ETF | Feature | Claude | todo | T1-01 |
| T1-03 | Holdings: record what I own | Feature | Claude | todo | T1-02 |
| T1-04 | Cash and remittances, with LRS totals | Feature | Claude | todo | T1-01 |
| T1-05 | India market data: stock prices and fund NAVs, with backfill | Feature | Claude | todo | T1-02 |
| T1-06 | US market data and USD/INR rates | Feature | Claude | todo | T1-05 |
| T1-07 | Watchlist | Feature | Claude | todo | T1-02, T1-05 |
| T1-08 | Portfolio view: value, P&L, allocation, XIRR | Feature | Claude | todo | T1-03, T1-04, T1-05, T1-06 |
| T1-09 | Daily automation on Windows | Infra | both | todo | T1-05, T1-06 |
| T1-10 | Phase 1 acceptance: my real data, reconciled | Verify | both | todo | T1-01 to T1-09 |

```
T1-01 ─┬─► T1-02 ─┬─► T1-03 ───────────────┐
       │          ├─► T1-05 ─┬─► T1-06 ─┬──►├─► T1-08 ─┐
       │          │          │          └─► T1-09 ─────┼─► T1-10
       │          └──────────┴─► T1-07 ────────────────┤
       └─► T1-04 ──────────────────────────► (T1-08) ──┘
```

T1-04 can be built in parallel with T1-02 / T1-03. T1-07 and T1-09 can run in parallel with T1-08.

---

## T1-01 · Foundation: app skeleton running on Windows
`Infra` · Owner: Claude · Status: doing · Depends on: —

**Goal:** a working, empty Friday I can start on my laptop: backend, database, frontend and tooling all wired, so every later task only adds features.

**Scope**
- Repo layout with `backend/` and `frontend/`; `.env` handling; `data/` and `logs/` git-ignored
- Backend: project, health endpoint, SQLite connection (WAL, foreign keys on), migrations set up with an empty first migration
- Frontend: project, app shell with navigation placeholders for Phase 1 pages, UI kit installed, API client generated from the backend schema
- **Dev mode** (hot reload on both sides) and **daily mode** (one process serving the built UI at `localhost`)
- Task-runner commands that work on Windows: setup, dev, build, run, test, lint
- Lint, format and tests on both sides; CI decision
- `CLAUDE.md` gets the dev conventions (money, time, layout) from the decisions below

**Decisions** (each logged as a `D-###` in `agents.md`)
- Python version and package manager (candidates: 3.12 / 3.13 · uv / Poetry / pip + venv)
- Backend framework (candidates: FastAPI / Litestar / Flask; must produce an OpenAPI schema)
- Database access and migrations (candidates: SQLAlchemy 2 + Alembic / SQLModel / raw SQL + simple migrations)
- Money, currency and time conventions (`Decimal` vs integer minor units; amounts as strings in JSON; UTC storage, IST display; market date per exchange; decimal places for prices, NAVs, units, FX)
- Frontend tooling (candidates: Vite / Next.js · TypeScript · pnpm / npm · ESLint + Prettier / Biome)
- UI kit, data fetching and routing (candidates: shadcn/ui + Tailwind / Mantine / MUI · TanStack Query / SWR · React Router / TanStack Router)
- API contract (candidate: REST + OpenAPI + generated TypeScript client; `/api/v1`; error format)
- Repo layout and task runner (Windows-friendly: justfile / package scripts / PowerShell; no `make` by default, D-027)
- Testing and CI (pytest; Vitest or none in Phase 1; GitHub Actions or local only)

**Done when**
- On a fresh clone on Windows, the documented setup + run commands open Friday at `localhost` showing the app shell and "backend: ok"
- `test` and `lint` pass on both sides
- A sample endpoint round-trips a money value (e.g. `1234567.89` INR) and a timestamp without any precision or time-zone change, covered by a test

---

## T1-02 · Instruments: find any stock, fund or ETF
`Feature` · Owner: Claude · Status: todo · Depends on: T1-01

**Goal:** every instrument I could hold or watch is known to Friday, with the right type, exchange, currency and asset class, and I can find it by typing part of its name.

**Scope**
- Instrument tables and master lists for NSE (and BSE if needed) stocks, Indian mutual fund schemes, US stocks and ETFs
- Import + refresh command (idempotent)
- Asset classification per instrument (asset class, country, currency, fund category), with a manual override
- Search API and a reusable search box in the UI; a simple instrument page

**Decisions**
- Identifiers (ISIN, NSE symbol, BSE code, AMFI scheme code, US ticker / SEC CIK) and internal ID scheme
- Sources for the lists (candidates: NSE equity list file, AMFI scheme list from the NAV file, SEC `company_tickers.json`, Nasdaq Trader symbol files)
- Allocation buckets and how each instrument is assigned (e.g. how mutual funds map from their AMFI category; hybrid funds)
- How renames and mergers are handled

**Done when**
- Searching "infos", "parag parikh flexi" and "QQQ" finds the right instruments with correct type, exchange, currency and asset class
- Running the refresh twice changes nothing the second time
- Tests cover import parsing and classification rules

---

## T1-03 · Holdings: record what I own
`Feature` · Owner: Claude · Status: todo · Depends on: T1-02

**Goal:** I can enter every purchase, sale and corporate action, and Friday shows the correct units and cost for each holding.

**Scope**
- Transaction ledger: buy, sell, dividend, split, bonus (SIP instalments as buys); fees
- Lots derived from transactions; sells matched to lots
- API for create / edit / delete / list
- UI: transactions list, add/edit form using the instrument search, holdings list with units and cost (no prices yet)
- Optional CSV template import for the first bulk load

**Decisions**
- Transaction types and fields; how splits, bonuses and mergers are recorded
- Lot matching rule (FIFO is the usual rule for Indian tax on demat holdings; confirm, and confirm for US holdings)
- Whether brokerage, taxes and charges go into cost
- Fractional units (mutual funds, US fractional shares)
- Forms and tables libraries (candidates: React Hook Form + Zod / TanStack Form · TanStack Table / AG Grid Community / UI kit table)
- CSV import: yes or no in Phase 1

**Done when**
- A test portfolio with an Indian stock that had a split, a mutual fund with SIPs and a partial redemption, and a US ETF with fractional shares shows correct units and cost per holding
- Lot-matching and corporate-action rules have unit tests with hand-worked expected values

---

## T1-04 · Cash and remittances, with LRS totals
`Feature` · Owner: Claude · Status: todo · Depends on: T1-01

**Goal:** I can record my cash (INR and USD) and money sent to the US, and see LRS totals per financial year.

**Scope**
- Cash accounts: name, currency, balance, earmark (emergency / deployable / reserved)
- Remittances: date, INR sent, USD received, rate, TCS paid, bank charges
- LRS totals per financial year (April–March): sent, TCS paid, room left under the LRS limit and TCS threshold
- A `tax_rules` config table with each value's source and "verified on" date
- UI screens for cash accounts, remittances and the LRS summary

**Decisions**
- Cash model: current balance only, or balance history
- Remittance fields
- LRS and TCS rule values. My understanding is a USD 250,000 LRS limit and a ₹10 lakh TCS threshold per financial year from April 2025. **Verify against current official sources** before use, and record the source

**Done when**
- Remittances spread across two financial years show per-year totals that match a hand calculation
- Emergency cash is shown separately from deployable cash
- Rule values come from the config table, not from code; tests cover the totals

---

## T1-05 · India market data: stock prices and fund NAVs, with backfill
`Feature` · Owner: Claude · Status: todo · Depends on: T1-02

**Goal:** Friday has daily closing prices for my Indian stocks and NAVs for my mutual funds, fills in any missed days by itself, and I can trigger a refresh.

**Scope**
- Fetcher framework: common adapter interface, timeouts and retries, polite request rate, caching, idempotent writes, **backfill of every missed trading day since the last success** (D-022), a `job_runs` log
- Market holiday calendars, so a holiday isn't treated as a gap
- India stock end-of-day prices (primary + fallback); mutual fund NAVs (daily + history)
- History backfill for everything I hold or watch
- Command-line entry point per fetcher; "Refresh prices" button and "last updated" indicator in the UI

**Decisions** (each backed by a quick **test fetch** of my real symbols for the last 30 days, dated)
- India price source and fallback (candidates: NSE daily bhavcopy, which changed format in 2024 · BSE bhavcopy · Yahoo `.NS` / `.BO` · unofficial wrappers like jugaad-data or nsepython)
- Mutual fund NAV source (candidates: AMFI daily `NAVAll.txt` · AMFI NAV history · mfapi.in)
- Holiday calendar source (candidates: `exchange_calendars` · `pandas_market_calendars` · exchange-published lists)
- Adjusted vs unadjusted prices

**Done when**
- Spot checks of closes and NAVs for my instruments match the exchange or AMC website
- Running the same fetch twice adds nothing
- Skipping three days and then running fills exactly the missing trading days; holidays aren't reported as gaps
- The fallback source is used when the primary fails (tested with a simulated failure)

---

## T1-06 · US market data and USD/INR rates
`Feature` · Owner: Claude · Status: todo · Depends on: T1-05

**Goal:** Friday has daily closes for my US stocks and ETFs and a USD/INR rate for every date it needs, using the same framework as T1-05.

**Scope**
- US end-of-day prices (primary + fallback) for stocks and ETFs, with history
- Daily USD/INR rate, with history back to my earliest US purchase and remittance
- US market holidays
- Hooked into the same "Refresh prices" button and `job_runs` log

**Decisions** (each backed by a dated test fetch)
- US price source and fallback (candidates: Yahoo / yfinance · Stooq · free tiers of Alpha Vantage, Tiingo or Financial Modeling Prep; free terms change, verify)
- USD/INR source (candidates: FBIL reference rate, the successor to the RBI reference rate · Yahoo `INR=X`)
- Whether to also store a tax-specific rate now (Indian tax rules may prescribe e.g. the SBI TT buying rate for foreign gains; check, or defer to the v2 Tax Agent)

**Done when**
- Spot checks of US closes and USD/INR rates match a reference source
- Every date of a past US purchase or remittance has a rate
- Same backfill, re-run and fallback tests as T1-05 pass for the US sources

---

## T1-07 · Watchlist
`Feature` · Owner: Claude · Status: todo · Depends on: T1-02, T1-05

**Goal:** I can keep a list of stocks and funds I'm watching, with my reason, and see where each price stands.

**Scope**
- Watchlist items: instrument, *why I'm watching*, optional buy zone, max allocation, status (`active` / `candidate`), date added
- UI: list with latest price, change, distance from buy zone and from 52-week high; add / edit / remove
- New watchlist items get their price history backfilled by the fetchers

**Decisions**
- Fields and which price signals to show in Phase 1

**Done when**
- Adding an Indian stock, a mutual fund and a US ETF shows each with its latest price and buy-zone distance
- Adding an item triggers its price-history backfill

---

## T1-08 · Portfolio view: value, P&L, allocation, XIRR
`Feature` · Owner: Claude · Status: todo · Depends on: T1-03, T1-04, T1-05, T1-06

**Goal:** the dashboard shows what my portfolio is worth, how it has done, and how it's split, in INR and USD.

**Scope**
- Calculations (backend only): current value per holding in its own currency and in INR; realised and unrealised P&L; allocation by asset class, country and currency (cash included); XIRR per holding, per sleeve (India / US) and for the whole portfolio
- For US holdings: return in USD, return in INR, and the part caused by USD/INR moving
- API endpoints for summary, allocation, holdings and holding detail
- Dashboard: totals, allocation chart, holdings table, prices-last-updated
- Holding detail page: lots and transactions, price chart, P&L and XIRR

**Decisions**
- Returns definitions (what counts in P&L and XIRR, whether dividends count, which price is "current")
- Charts library (candidates: ECharts · Recharts · Chart.js · TradingView Lightweight Charts for price charts)
- Benchmarks (Nifty 50, S&P 500) in Phase 1 or later

**Done when**
- Hand-worked examples (single buy, partial sells, SIPs, a US holding where USD/INR moved) pass as unit tests
- Dashboard numbers match the API exactly
- The holding page works for an Indian stock, a mutual fund and a US ETF

---

## T1-09 · Daily automation on Windows
`Infra` · Owner: both · Status: todo · Depends on: T1-05, T1-06

**Goal:** prices update every day without me doing anything, including after the laptop was asleep.

**Scope**
- A script that installs and uninstalls Windows Task Scheduler tasks for each fetch (times from `agents.md` 3.4), with *run as soon as possible after a missed start* on and *only on AC power* off (D-027)
- Optionally: start the Friday server at logon, so the UI is always available
- Job logs in `logs/`; a status page in the UI showing recent `job_runs`

**Decisions**
- Final job times
- Whether the server starts at logon
- Log location and rotation

**Done when**
- After install, each job runs at its time and shows in the status page
- After a night with the laptop asleep, the missed jobs run once on wake and the data has no gaps
- Uninstall removes every task

---

## T1-10 · Phase 1 acceptance: my real data, reconciled
`Verify` · Owner: both · Status: todo · Depends on: T1-01 to T1-09

**Goal:** prove Phase 1 does what it promised, on my real portfolio.

**Scope**
- Enter all my real holdings, cash, remittances and watchlist items (me)
- Reconcile units, cost and current value against my broker statements and CAS
- Let it run unattended for a week, including nights asleep
- Anything wrong becomes a new task on this board

**Done when**
- Units, cost and value match my statements within rounding, or every difference is explained
- A week of daily updates shows every trading day filled once, no duplicates, holidays skipped
- No open bugs from this check, or they're logged as tasks

**Evidence:** —
