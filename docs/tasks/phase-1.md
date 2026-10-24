# Phase 1 — Tracker · Task board

> **Goal:** see my whole portfolio in one place with correct numbers. No AI. Prices update daily by themselves.
> **Exit:** all my real holdings are in, prices update daily, numbers match my broker statements ([`phases.md`](../phases.md)).
> **Already fixed:** React frontend + Python backend (D-023) · SQLite on the laptop (D-013) · free data only (D-012) · scheduled fetch + backfill (D-022) · Windows + Task Scheduler (D-027).
> Everything else is decided **inside the task that needs it** (see each task's *Decisions* list). How this board works: [`README.md`](README.md)

**Board version:** 2 (regenerated 2026-10-24 as feature-sized tasks; the first draft's IDs are void) · **Done:** 2 / 11

---

## Board

| ID | Task | Kind | Owner | Status | Depends on |
|----|------|------|-------|--------|------------|
| T1-01 | Foundation: app skeleton running on Windows | Infra | Claude | done | — |
| T1-02 | Instruments: find any stock, fund or ETF | Feature | Claude | done | T1-01 |
| T1-03 | Holdings: record what I own | Feature | Claude | todo | T1-02 |
| T1-04 | Cash and remittances, with LRS totals | Feature | Claude | todo | T1-01 |
| T1-05 | India market data: stock prices and fund NAVs, with backfill | Feature | Claude | todo | T1-02 |
| T1-06 | US market data and USD/INR rates | Feature | Claude | todo | T1-05 |
| T1-07 | Watchlist | Feature | Claude | todo | T1-02, T1-05 |
| T1-08 | Portfolio view: value, P&L, allocation, XIRR | Feature | Claude | todo | T1-03, T1-04, T1-05, T1-06 |
| T1-09 | Daily automation on Windows | Infra | both | todo | T1-05, T1-06 |
| T1-10 | Phase 1 acceptance: my real data, reconciled | Verify | both | todo | T1-01 to T1-09 |
| T1-11 | REITs, InvITs and BSE-only listings | Feature | Claude | todo | T1-02 |

```
T1-01 ─┬─► T1-02 ─┬─► T1-03 ───────────────┐
       │          ├─► T1-05 ─┬─► T1-06 ─┬──►├─► T1-08 ─┐
       │          │          │          └─► T1-09 ─────┼─► T1-10
       │          └──────────┴─► T1-07 ────────────────┤
       └─► T1-04 ──────────────────────────► (T1-08) ──┘
```

T1-04 can be built in parallel with T1-02 / T1-03. T1-07 and T1-09 can run in parallel with T1-08. T1-11 (added during T1-02) can be done any time after T1-02.

---

## T1-01 · Foundation: app skeleton running on Windows
`Infra` · Owner: Claude · Status: done · Depends on: —

**Goal:** a working, empty Friday I can start on my laptop: backend, database, frontend and tooling all wired, so every later task only adds features.

**Scope**
- Repo layout with `backend/` and `frontend/`; `.env` handling; `data/` and `logs/` git-ignored
- Backend: project, health endpoint, SQLite connection (WAL, foreign keys on), migrations set up with an empty first migration
- Frontend: project, app shell with navigation placeholders for Phase 1 pages, UI kit installed, API client generated from the backend schema
- **Dev mode** (hot reload on both sides) and **daily mode** (one process serving the built UI at `localhost`)
- Task-runner commands that work on Windows: setup, dev, build, run, test, lint
- Lint, format and tests on both sides; CI decision
- `CLAUDE.md` gets the dev conventions (money, time, layout) from the decisions below

**Decisions** (approved 2026-10-24)
- Decided: Python **3.14**, managed by **uv**; backend lint/format with **ruff**; no type checker yet (D-029)
- Decided: **FastAPI** (D-030)
- Decided: **SQLAlchemy 2.0 (sync) + Alembic**; SQLite with WAL, foreign keys, busy timeout; `data/friday.db` (D-031)
- Decided: money as `Decimal`, stored as text, sent as JSON strings (numbers rejected); 2 / 4 / 8 / 6 decimal places for amounts / prices and NAVs / units / FX; UTC storage, IST display; market date per exchange (D-032)
- Decided: **Vite + React + TypeScript**, **npm**, **ESLint + Prettier** (D-033)
- Decided: **shadcn/ui + Tailwind**, **TanStack Query**, **React Router** (D-034)
- Decided: REST under `/api/v1`, **openapi-typescript + openapi-fetch**, RFC 9457 problem details (D-035)
- Decided: `backend/` + `frontend/`, **`just`** (PowerShell on Windows), server on `127.0.0.1:8000`, Vite dev server on `:5173` (D-036)
- Decided: **pytest**, **Vitest**, **GitHub Actions on a Windows runner** (D-037)

**Progress (2026-10-24)**
- Built: backend (FastAPI, SQLite + Alembic baseline, exact money/time types, problem-details errors, UI serving, `friday` CLI), frontend (Vite + React + TS, shadcn/ui, TanStack Query, React Router, app shell with Phase 1 pages, backend status badge, generated API client, `formatMoney`), `justfile`, `scripts/dev.py`, `scripts/smoke.py`, Windows CI, README, `CLAUDE.md` conventions
- Verified on Linux: `just setup`, `just lint`, `just test` (backend 20 tests, frontend 7 tests), `just smoke`, and screenshots of the running app (desktop and phone width)
- Notes: Vite's template now ships oxlint; replaced with ESLint as decided (D-033). TypeScript pinned to 5.9 because openapi-typescript doesn't support TypeScript 6 yet. shadcn's registry is blocked from the build environment, so the shadcn setup and components (button, card, badge) were added by hand from shadcn's source; `npx shadcn add` works normally on the laptop
- Windows CI passed on a fresh `windows-latest` clone (run #1, https://github.com/ragnar2801/EDITH/actions/runs/40106787128): `just setup`, `lint`, `test`, `api-check` and `smoke` (real server, health ok, UI served)
- Worth doing once on my laptop: `just setup` then `just run`, and open http://localhost:8000

**Done when**
- On a fresh clone on Windows, the documented setup + run commands open Friday at `localhost` showing the app shell and "backend: ok"
- `test` and `lint` pass on both sides
- A sample endpoint round-trips a money value (e.g. `1234567.89` INR) and a timestamp without any precision or time-zone change, covered by a test

---

## T1-02 · Instruments: find any stock, fund or ETF
`Feature` · Owner: Claude · Status: done · Depends on: T1-01

**Goal:** every instrument I could hold or watch is known to Friday, with the right type, exchange, currency and asset class, and I can find it by typing part of its name.

**Scope**
- Instrument tables and master lists for NSE (and BSE if needed) stocks, Indian mutual fund schemes, US stocks and ETFs
- Import + refresh command (idempotent)
- Asset classification per instrument (asset class, country, currency, fund category), with a manual override
- Search API and a reusable search box in the UI; a simple instrument page

**Decisions** (approved 2026-10-24)
- Decided: internal integer `id` as the key; (exchange, symbol), AMFI scheme code, ISIN and CIK stored as lookups; an alias table for old symbols and names; an ETF on NSE and in AMFI is one instrument, matched on ISIN (D-038)
- Decided: NSE archive files (equity list, ETF list, symbol and name changes), AMFI `NAVAll.txt`, Nasdaq Trader symbol files, SEC tickers for CIKs (optional); downloaded with httpx2 using per-source headers; raw copies kept in `data/sources/`; import from a folder as a fallback (D-039)
- Decided: allocation split over equity / debt / gold / silver / other plus exposure IN / US / GLOBAL; rules from NSE's ETF column, AMFI categories and name keywords; hybrid defaults; manual override that survives refresh (D-040)
- Decided: never delete; match by ISIN → symbol → NSE symbol-change chain; old values become aliases; missing or stale → inactive; reject a list under half its usual size (D-041)
- Decided: local SQLite FTS5 search with prefix matching, exact-symbol first, fund variants grouped with Direct + Growth first (D-042)

**Progress (2026-10-24)**
- Checked every source from the build environment first: NSE archives need browser-like headers, Nasdaq Trader rejects them (bot-check page), AMFI moved to `portal.amfiindia.com` and its file now has Plan and Option columns, AMFI uses two category naming schemes side by side, and about 5,600 AMFI schemes have no NAV since 2014–2025 (closed). REITs and InvITs are not in NSE's equity list → new task T1-11
- Built: tables `instruments`, `instrument_aliases`, `instrument_overrides`, `instrument_imports` and the FTS5 index (migration 0002); parsers for every file; refresh that matches, never deletes and changes only what differs; classification rules; search API (`/api/v1/instruments/search`, detail, override, sources); `friday instruments refresh|search` and `just instruments`; UI: reusable `InstrumentSearch` box, Instruments page with list status, instrument page with identifiers, plans, old names and a classification override form
- Live run (2026-10-24, all four sources downloaded): 2,968 NSE stocks and ETFs, 14,412 AMFI schemes (8,471 active), 11,755 US stocks and ETFs, 6,158 CIKs, 1,277 aliases from NSE's rename files; 12 s. Second live run: 0 added, 0 updated, 0 deactivated
- Done-when searches on the live data: "infos" → NSE INFY (stock, NSE, INR, equity; the NYSE ADR in USD also listed); "parag parikh flexi" → AMFI 122639 Direct Growth (mutual fund, INR, equity) with its 3 other plans; "QQQ" → NASDAQ QQQ (ETF, USD, equity). Also "zomato" → ETERNAL, NIFTYBEES carries its AMFI scheme
- Tests: 138 backend (parsers on byte-for-byte slices of the real files, classification table, refresh scenarios: renames, splits, reused symbols, delistings, bad downloads, overrides) and 17 frontend. `just lint`, `just test`, `just api-check`, `just smoke` pass on Linux; screenshots checked at desktop and phone width, light and dark
- Known limits: US ETFs are classified by name only (e.g. a US "multi-asset" ETF shows as equity; fix with an override). US ticker changes are matched only when `FRIDAY_SEC_USER_AGENT` is set (CIK). BSE-only stocks aren't listed (T1-11)
- Windows CI passed (run #3, https://github.com/ragnar2801/EDITH/actions/runs/40110560643): `just setup`, `lint`, `test`, `api-check`, `smoke`, including SQLite FTS5 on Windows Python
- Worth doing once on my laptop: `just instruments`, then search at http://localhost:8000/instruments

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

---

## T1-11 · REITs, InvITs and BSE-only listings
`Feature` · Owner: Claude · Status: todo · Depends on: T1-02

**Goal:** I can find and hold REITs, InvITs and stocks listed only on BSE, like any other instrument.

**Scope**
- Found in T1-02: NSE's `EQUITY_L.csv` has no REITs or InvITs, and BSE isn't imported
- Import the REIT and InvIT lists (NSE publishes them separately) as their own kind, classified as `other` (real estate / infrastructure) unless decided otherwise
- Import BSE's scrip list for stocks not on NSE, matched to NSE instruments by ISIN so dual-listed stocks stay one instrument

**Decisions**
- Source files for REITs, InvITs and BSE scrips (check what downloads without a browser session)
- Bucket for REITs and InvITs (`other`, or a new `real_estate` bucket)
- Whether BSE codes are stored for every NSE stock too (useful for BSE price fallback in T1-05)

**Done when**
- Searching "embassy" finds Embassy Office Parks REIT; a BSE-only stock is found by name
- A stock listed on both exchanges is still one instrument
- Refresh twice changes nothing; tests cover the new parsers

