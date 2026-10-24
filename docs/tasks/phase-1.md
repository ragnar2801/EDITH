# Phase 1 — Tracker · Task board

> **Goal:** see my whole portfolio in one place with correct numbers. No AI. Prices update daily by themselves.
> **Exit:** all my real holdings are in, prices update daily, numbers match my broker statements ([`phases.md`](../phases.md)).
> **Fixed so far:** React frontend + Python backend (D-023), SQLite on the laptop (D-013), free data only (D-012), cron + backfill (D-022). **Everything else is decided in the DECIDE tasks below.**
> How this board works: [`README.md`](README.md)

**Last updated:** 2026-10-24

---

## Board

### M1 — Foundations (decisions)

| ID | Task | Type | Owner | Status | Depends on |
|----|------|------|-------|--------|------------|
| T1-01 | Laptop OS and scheduler | DECIDE | me | doing | — |
| T1-02 | Backend tooling (Python version, packages, lint, types) | DECIDE | both | todo | — |
| T1-03 | Backend web framework | DECIDE | both | todo | — |
| T1-04 | Database access and migrations | DECIDE | both | todo | T1-03 |
| T1-05 | Money, currency and time conventions | DECIDE | both | todo | — |
| T1-06 | Frontend tooling (build tool, TypeScript, packages, lint) | DECIDE | both | todo | — |
| T1-07 | Frontend libraries (UI kit, data fetching, tables, forms, routing) | DECIDE | both | todo | T1-06 |
| T1-08 | Charts library | DECIDE | both | todo | T1-06 |
| T1-09 | API contract between React and Python | DECIDE | both | todo | T1-03, T1-06 |
| T1-10 | Repo layout and dev workflow | DECIDE | both | todo | T1-02, T1-06 |
| T1-11 | Testing and CI | DECIDE | both | todo | T1-02, T1-06 |

### M2 — Data sources (decide with a quick test fetch)

| ID | Task | Type | Owner | Status | Depends on |
|----|------|------|-------|--------|------------|
| T1-12 | India stock end-of-day prices source | DECIDE | both | todo | — |
| T1-13 | Indian mutual fund NAV source | DECIDE | both | todo | — |
| T1-14 | US stock and ETF end-of-day prices source | DECIDE | both | todo | — |
| T1-15 | USD/INR exchange rate source | DECIDE | both | todo | — |
| T1-16 | Market holiday calendars | DECIDE | both | todo | — |
| T1-17 | Instrument master and identifiers | DECIDE | both | todo | T1-12, T1-13, T1-14 |

### M3 — Data model and screens (decisions)

| ID | Task | Type | Owner | Status | Depends on |
|----|------|------|-------|--------|------------|
| T1-18 | Holdings model (transactions, lots, corporate actions) | DECIDE | both | todo | T1-05 |
| T1-19 | Cash and remittance model | DECIDE | both | todo | T1-05 |
| T1-20 | Asset classification for allocation | DECIDE | both | todo | T1-17 |
| T1-21 | Returns definitions (P&L, XIRR, INR vs USD) | DECIDE | both | todo | T1-18 |
| T1-22 | LRS basics and rule values | DECIDE | both | todo | T1-19 |
| T1-23 | Phase 1 screens and initial data load | DECIDE | both | todo | T1-18, T1-19 |

### M4 — Build: backend

| ID | Task | Type | Owner | Status | Depends on |
|----|------|------|-------|--------|------------|
| T1-24 | Backend scaffold + `CLAUDE.md` dev conventions | BUILD | Claude | todo | T1-02, T1-03, T1-04, T1-10, T1-11 |
| T1-25 | Database schema v1 and migrations | BUILD | Claude | todo | T1-24, T1-18, T1-19, T1-20 |
| T1-26 | Instrument master import and search | BUILD | Claude | todo | T1-25, T1-17 |
| T1-27 | Fetcher framework (adapters, retries, backfill, job log) | BUILD | Claude | todo | T1-25, T1-16 |
| T1-28 | India prices fetcher | BUILD | Claude | todo | T1-27, T1-12 |
| T1-29 | Mutual fund NAV fetcher | BUILD | Claude | todo | T1-27, T1-13 |
| T1-30 | US prices fetcher | BUILD | Claude | todo | T1-27, T1-14 |
| T1-31 | USD/INR fetcher | BUILD | Claude | todo | T1-27, T1-15 |
| T1-32 | Scheduling: cron entries + "Refresh prices" | BUILD | both | todo | T1-28, T1-29, T1-30, T1-31, T1-01 |
| T1-33 | Calculations: valuation, P&L, allocation | BUILD | Claude | todo | T1-25, T1-20, T1-21 |
| T1-34 | Calculations: XIRR | BUILD | Claude | todo | T1-33 |
| T1-35 | LRS financial-year totals | BUILD | Claude | todo | T1-25, T1-22 |
| T1-36 | API endpoints (data entry + portfolio summary) | BUILD | Claude | todo | T1-25, T1-09, T1-33 |

### M5 — Build: frontend

| ID | Task | Type | Owner | Status | Depends on |
|----|------|------|-------|--------|------------|
| T1-37 | Frontend scaffold + generated API client | BUILD | Claude | todo | T1-06, T1-07, T1-09, T1-10 |
| T1-38 | App shell and navigation | BUILD | Claude | todo | T1-37, T1-23 |
| T1-39 | Data entry screens | BUILD | Claude | todo | T1-38, T1-36 |
| T1-40 | Dashboard | BUILD | Claude | todo | T1-38, T1-36, T1-08 |
| T1-41 | Holding detail page | BUILD | Claude | todo | T1-40 |

### M6 — Verify (Phase 1 exit)

| ID | Task | Type | Owner | Status | Depends on |
|----|------|------|-------|--------|------------|
| T1-42 | Enter my real holdings, cash and remittances | VERIFY | me | todo | T1-39 |
| T1-43 | Reconcile against broker and CAS statements | VERIFY | both | todo | T1-42, T1-34, T1-35 |
| T1-44 | One week of unattended daily updates | VERIFY | both | todo | T1-32 |

**Suggested order:** T1-01 → M1 (quick decisions) → M2 (each with a test fetch) → M3 → M4 and M5 in parallel → M6.

---

## M1 — Foundations

### T1-01 · Laptop OS and scheduler
`DECIDE` · Owner: me · Status: doing · Depends on: —

- **Question:** which OS does Friday run on, and which scheduler runs the daily jobs?
- **Options:** macOS (cron, or launchd, which runs a missed job once after wake) · Windows (Task Scheduler with "run as soon as possible after a missed start") · Linux (cron, or systemd timers with `Persistent=true`)
- **Note:** pulled forward from Phase 4a because Phase 1 cron (D-022) depends on it.
- **Done when:** OS and scheduler chosen, logged as D-###.
- **Outcome:** —

### T1-02 · Backend tooling
`DECIDE` · Owner: both · Status: todo · Depends on: —

- **Question:** Python version, environment and package manager, lint/format, type checking.
- **Options:** Python 3.12 / 3.13 · uv / Poetry / pip + venv · ruff / black + flake8 · mypy / pyright / none for now
- **Criteria:** simple setup on one laptop, fast, a lockfile, well supported.
- **Done when:** picks logged as D-###.
- **Outcome:** —

### T1-03 · Backend web framework
`DECIDE` · Owner: both · Status: todo · Depends on: —

- **Question:** which Python framework serves the API (and the built React app)?
- **Options:** FastAPI · Litestar · Flask (+ extensions). Django excluded (D-023).
- **Criteria:** automatic OpenAPI schema (for a generated TypeScript client), typing and validation, maturity, how well Claude Code knows it, easy to serve static files.
- **Done when:** pick logged as D-###.
- **Outcome:** —

### T1-04 · Database access and migrations
`DECIDE` · Owner: both · Status: todo · Depends on: T1-03

- **Question:** how Python talks to SQLite (D-013), and how the schema evolves.
- **Options:** SQLAlchemy 2.0 + Alembic · SQLModel + Alembic · raw SQL + a simple migration runner · Peewee
- **Also decide:** SQLite settings (WAL mode so the UI can read while jobs write, foreign keys on), where the DB file lives.
- **Done when:** pick and settings logged as D-###.
- **Outcome:** —

### T1-05 · Money, currency and time conventions
`DECIDE` · Owner: both · Status: todo · Depends on: —

- **Question:** how amounts, currencies and dates are stored and passed around.
- **Options:** money as `Decimal` (SQL `NUMERIC`) vs integer minor units (paise/cents) · amounts in JSON as strings vs numbers · timestamps in UTC, shown in IST · a "market date" belonging to its exchange · currency codes (ISO 4217: `INR`, `USD`) · how many decimals for prices, NAVs, units and FX rates
- **Why it matters:** floating-point money errors, and US closes landing on the next IST day.
- **Done when:** conventions logged as D-### and copied into `CLAUDE.md` when it's created (T1-24).
- **Outcome:** —

### T1-06 · Frontend tooling
`DECIDE` · Owner: both · Status: todo · Depends on: —

- **Question:** build tool, language, package manager, lint/format.
- **Options:** Vite (plain single-page app) / Next.js / React Router framework mode · TypeScript or JavaScript · pnpm / npm / bun · ESLint + Prettier / Biome
- **Criteria:** the Python backend is already the server, local single user, little config.
- **Done when:** picks logged as D-###.
- **Outcome:** —

### T1-07 · Frontend libraries
`DECIDE` · Owner: both · Status: todo · Depends on: T1-06

- **Question:** UI kit and styling, server data, tables, forms, routing.
- **Options:**
  - UI kit / styling: shadcn/ui + Tailwind · Mantine · MUI · Ant Design
  - Server data: TanStack Query · SWR
  - Tables: TanStack Table · AG Grid Community · the UI kit's table
  - Forms: React Hook Form + Zod · TanStack Form
  - Routing: React Router · TanStack Router
- **Criteria:** a lot of data entry and tables, consistent look with little custom CSS, easy for Claude Code to work in.
- **Done when:** picks logged as D-###.
- **Outcome:** —

### T1-08 · Charts library
`DECIDE` · Owner: both · Status: todo · Depends on: T1-06

- **Question:** which library draws allocation, performance and price charts?
- **Options:** ECharts · Recharts · Chart.js · Nivo · TradingView Lightweight Charts (price charts only)
- **Criteria:** donut/treemap for allocation, line charts for value over time, candlestick or line price charts, dark mode, free licence.
- **Done when:** pick(s) logged as D-###.
- **Outcome:** —

### T1-09 · API contract between React and Python
`DECIDE` · Owner: both · Status: todo · Depends on: T1-03, T1-06

- **Question:** how the frontend and backend agree on data shapes.
- **Options:** REST + OpenAPI schema + generated TypeScript client (e.g. openapi-typescript, Orval, Hey API) · REST + hand-written types · GraphQL (likely overkill)
- **Also decide:** URL prefix and versioning (`/api/v1`), error format, how money and dates appear in JSON (from T1-05).
- **Done when:** approach logged as D-###.
- **Outcome:** —

### T1-10 · Repo layout and dev workflow
`DECIDE` · Owner: both · Status: todo · Depends on: T1-02, T1-06

- **Question:** folder structure, and how I run Friday day to day vs while developing.
- **Options:** one repo with `backend/` and `frontend/` (current proposal in `agents.md` 3.13) vs other splits · daily use: one process that serves the built UI vs two processes · dev: Vite dev server proxying to the backend · task runner (Makefile / justfile / package scripts) · `.env` handling · `data/` and `logs/` git-ignored
- **Done when:** layout and commands logged as D-###, and `agents.md` 3.13 layout updated.
- **Outcome:** —

### T1-11 · Testing and CI
`DECIDE` · Owner: both · Status: todo · Depends on: T1-02, T1-06

- **Question:** what gets tested, with what, and whether tests run on GitHub.
- **Options:** pytest for backend (must-have for the maths) · Vitest (+ Testing Library) for frontend, or none in Phase 1 · GitHub Actions on push, or local only
- **Done when:** approach logged as D-###.
- **Outcome:** —

---

## M2 — Data sources

Each task here includes a **test fetch**: a throwaway script that pulls a few real symbols for the last 30 days, so the decision rests on evidence. Free sources change, so note the date tested.

### T1-12 · India stock end-of-day prices source
`DECIDE` · Owner: both · Status: todo · Depends on: —

- **Question:** primary and fallback source for NSE/BSE closing prices, including history for backfill.
- **Candidates:** NSE daily bhavcopy (note: NSE changed the file format in 2024) · BSE bhavcopy · Yahoo Finance (`.NS` / `.BO`) · unofficial wrapper libraries (e.g. jugaad-data, nsepython)
- **Test:** 5 of my stocks, last 30 trading days, from each candidate. Compare closes, note blocking, rate limits and adjusted vs unadjusted prices.
- **Done when:** primary + fallback logged as D-###, and `agents.md` 3.12 updated.
- **Outcome:** —

### T1-13 · Indian mutual fund NAV source
`DECIDE` · Owner: both · Status: todo · Depends on: —

- **Question:** where daily NAVs and NAV history come from.
- **Candidates:** AMFI daily `NAVAll.txt` (latest NAV for all schemes) · AMFI historical NAV download · mfapi.in (community JSON API with history)
- **Test:** 3 of my funds (direct plans), last 30 days, from each. Check scheme codes, ISINs and publish time.
- **Done when:** daily + history source logged as D-###.
- **Outcome:** —

### T1-14 · US stock and ETF end-of-day prices source
`DECIDE` · Owner: both · Status: todo · Depends on: —

- **Question:** primary and fallback for NASDAQ stocks and US ETFs.
- **Candidates:** Yahoo Finance (yfinance) · Stooq · free tiers of Alpha Vantage, Tiingo or Financial Modeling Prep (need an API key, rate limits change; verify current terms)
- **Test:** 5 symbols (stocks + ETFs), last 30 days. Compare closes, splits and dividends handling, limits.
- **Done when:** primary + fallback logged as D-###.
- **Outcome:** —

### T1-15 · USD/INR exchange rate source
`DECIDE` · Owner: both · Status: todo · Depends on: —

- **Question:** which daily USD/INR rate to store, from where, and for what purpose.
- **Candidates:** FBIL reference rate (successor to the RBI reference rate) · Yahoo `INR=X` · others found during the test
- **Also decide:** whether Phase 1 needs a tax-specific rate. Indian tax rules may prescribe a specific rate (e.g. SBI TT buying rate) for converting foreign gains; check, and decide whether to store it now or later (full Tax Agent is v2).
- **Test:** last 30 days from each candidate.
- **Done when:** source(s) and purpose logged as D-###.
- **Outcome:** —

### T1-16 · Market holiday calendars
`DECIDE` · Owner: both · Status: todo · Depends on: —

- **Question:** how Friday knows NSE/BSE and US trading days (so a holiday isn't treated as missing data during backfill).
- **Candidates:** `exchange_calendars` · `pandas_market_calendars` · exchange-published holiday lists (NSE, Nasdaq) loaded into a table
- **Test:** check this year's NSE and US holidays against the official lists.
- **Done when:** approach logged as D-###.
- **Outcome:** —

### T1-17 · Instrument master and identifiers
`DECIDE` · Owner: both · Status: todo · Depends on: T1-12, T1-13, T1-14

- **Question:** how each instrument is identified, and where the lists for searching come from.
- **Identifiers:** NSE symbol and ISIN · BSE code · AMFI scheme code (+ ISIN) · US ticker (+ SEC CIK)
- **Candidate lists:** NSE equity list file · AMFI scheme list (from the NAV file) · SEC `company_tickers.json` · Nasdaq Trader symbol files (include ETFs)
- **Also decide:** internal ID scheme, how a symbol rename or merger is handled, search experience in the UI.
- **Done when:** identifier scheme and sources logged as D-###.
- **Outcome:** —

---

## M3 — Data model and screens

### T1-18 · Holdings model
`DECIDE` · Owner: both · Status: todo · Depends on: T1-05

- **Question:** how holdings are recorded.
- **Options:** a transaction ledger (buy, sell, dividend, split, bonus, merger/demerger, SIP instalments as buys) with lots derived from it, vs editing lots directly
- **Also decide:** how sells are matched to lots (FIFO is the usual rule for Indian tax on demat holdings; confirm, and confirm for US holdings) · whether brokerage, taxes and charges go into cost · fractional units (MFs, US fractional shares)
- **Done when:** model logged as D-### and `agents.md` 3.9 updated.
- **Outcome:** —

### T1-19 · Cash and remittance model
`DECIDE` · Owner: both · Status: todo · Depends on: T1-05

- **Question:** how cash accounts and money sent abroad are recorded.
- **Scope:** accounts (bank, broker cash, US broker cash), currency, earmark (emergency / deployable / reserved) · balance history vs current balance only · remittances: date, INR sent, USD received, rate, TCS paid, bank charges, financial year
- **Done when:** model logged as D-### and `agents.md` 3.9 updated.
- **Outcome:** —

### T1-20 · Asset classification for allocation
`DECIDE` · Owner: both · Status: todo · Depends on: T1-17

- **Question:** which buckets the allocation view uses, and how each instrument is assigned.
- **Scope:** asset classes (India equity, US equity, debt, gold, cash, …) · country and currency exposure · how mutual funds are classified (AMFI category? hybrid funds split or counted as one?) · manual override per instrument
- **Done when:** buckets and rules logged as D-###.
- **Outcome:** —

### T1-21 · Returns definitions
`DECIDE` · Owner: both · Status: todo · Depends on: T1-18

- **Question:** exactly which numbers the dashboard shows and how they're calculated.
- **Scope:** XIRR per holding, per sleeve (India / US) and whole portfolio · realised vs unrealised P&L · whether dividends count · US holdings: return in USD, return in INR, and the part caused by USD/INR moving · which price is "current" (last close) · benchmarks: in Phase 1 or later
- **Done when:** definitions logged as D-###, with a worked example to use as a test case in T1-34.
- **Outcome:** —

### T1-22 · LRS basics and rule values
`DECIDE` · Owner: both · Status: todo · Depends on: T1-19

- **Question:** what the Phase 1 LRS view shows and which rule values it uses.
- **Scope:** financial year (April–March) · LRS limit per year · TCS threshold and rate on remittances for investment · where values live (a config table with a "verified on" date, D-### for `tax_rules`)
- **Note:** these values change with budgets. My understanding is a USD 250,000 LRS limit and a TCS threshold of ₹10 lakh per year from April 2025. **Verify both against current official sources** before use.
- **Done when:** values verified, sources noted, logged as D-###.
- **Outcome:** —

### T1-23 · Phase 1 screens and initial data load
`DECIDE` · Owner: both · Status: todo · Depends on: T1-18, T1-19

- **Question:** which pages exist in Phase 1 and what's on each; how I get my existing data in.
- **Candidate pages:** dashboard · holdings · transactions · cash accounts · remittances · watchlist · settings
- **Initial load:** forms only, or also a CSV template import for the first bulk load (D-003 says manual entry; a CSV of my own is still manual)
- **Done when:** page list + rough wireframes (text or sketch) logged as D-###.
- **Outcome:** —

---

## M4 — Build: backend

### T1-24 · Backend scaffold + `CLAUDE.md` dev conventions
`BUILD` · Owner: Claude · Status: todo · Depends on: T1-02, T1-03, T1-04, T1-10, T1-11

- **Scope:** project skeleton per the decisions, a health endpoint, lint/test commands working, `CLAUDE.md` with dev conventions (T1-05 rules, task routine from `docs/tasks/README.md`).
- **Done when:** a fresh clone runs the backend and its tests with the documented commands.

### T1-25 · Database schema v1 and migrations
`BUILD` · Owner: Claude · Status: todo · Depends on: T1-24, T1-18, T1-19, T1-20

- **Scope:** tables for instruments, transactions/lots, cash accounts, remittances, watchlist, prices, NAVs, FX rates, job runs. First migration.
- **Done when:** migration runs on an empty DB; models have basic tests.

### T1-26 · Instrument master import and search
`BUILD` · Owner: Claude · Status: todo · Depends on: T1-25, T1-17

- **Scope:** import the instrument lists chosen in T1-17, refresh them, search by symbol or name.
- **Done when:** I can find any of my stocks, funds and ETFs by typing part of its name.

### T1-27 · Fetcher framework
`BUILD` · Owner: Claude · Status: todo · Depends on: T1-25, T1-16

- **Scope:** a common adapter interface, timeouts and retries, polite request rate, caching, **backfill of every missed trading day since the last success** (D-022), idempotent writes, a `job_runs` log.
- **Done when:** a fake adapter passes tests for backfill, holidays and re-runs (no duplicates).

### T1-28 · India prices fetcher
`BUILD` · Owner: Claude · Status: todo · Depends on: T1-27, T1-12

- **Done when:** last close and history for all my India holdings and watchlist items are stored, with fallback working.

### T1-29 · Mutual fund NAV fetcher
`BUILD` · Owner: Claude · Status: todo · Depends on: T1-27, T1-13

- **Done when:** latest NAV and history for all my funds are stored.

### T1-30 · US prices fetcher
`BUILD` · Owner: Claude · Status: todo · Depends on: T1-27, T1-14

- **Done when:** last close and history for all my US stocks and ETFs are stored, with fallback working.

### T1-31 · USD/INR fetcher
`BUILD` · Owner: Claude · Status: todo · Depends on: T1-27, T1-15

- **Done when:** a daily rate is stored for every date needed (including the dates of past US purchases and remittances).

### T1-32 · Scheduling: cron entries + "Refresh prices"
`BUILD` · Owner: both · Status: todo · Depends on: T1-28, T1-29, T1-30, T1-31, T1-01

- **Scope:** scheduler entries for the OS chosen in T1-01 (times from `agents.md` 3.4), install/uninstall instructions, a "Refresh prices" endpoint that runs the same jobs.
- **Done when:** jobs run on schedule on my laptop; the button works.

### T1-33 · Calculations: valuation, P&L, allocation
`BUILD` · Owner: Claude · Status: todo · Depends on: T1-25, T1-20, T1-21

- **Scope:** current value per holding (native currency and INR), realised and unrealised P&L, allocation by the buckets from T1-20.
- **Done when:** unit tests pass on hand-worked examples.

### T1-34 · Calculations: XIRR
`BUILD` · Owner: Claude · Status: todo · Depends on: T1-33

- **Scope:** XIRR per holding, sleeve and portfolio, in INR (and USD for the US sleeve), per T1-21.
- **Done when:** the worked example from T1-21 and edge cases (single buy, partial sells, no cash flows) pass.

### T1-35 · LRS financial-year totals
`BUILD` · Owner: Claude · Status: todo · Depends on: T1-25, T1-22

- **Done when:** totals per financial year (sent, TCS paid, room left under limit and threshold) match a hand calculation.

### T1-36 · API endpoints
`BUILD` · Owner: Claude · Status: todo · Depends on: T1-25, T1-09, T1-33

- **Scope:** create/read/update/delete for transactions, cash accounts, remittances and watchlist; portfolio summary, allocation, holding detail, LRS totals; price refresh status.
- **Done when:** endpoints are in the API schema and have tests.

---

## M5 — Build: frontend

### T1-37 · Frontend scaffold + generated API client
`BUILD` · Owner: Claude · Status: todo · Depends on: T1-06, T1-07, T1-09, T1-10

- **Done when:** the app builds, calls the backend health endpoint through the generated client, and lint passes.

### T1-38 · App shell and navigation
`BUILD` · Owner: Claude · Status: todo · Depends on: T1-37, T1-23

- **Done when:** all Phase 1 pages from T1-23 exist (empty), with navigation and a "prices last updated" indicator.

### T1-39 · Data entry screens
`BUILD` · Owner: Claude · Status: todo · Depends on: T1-38, T1-36

- **Scope:** transactions (with instrument search), cash accounts, remittances, watchlist (with "why I'm watching"), plus CSV import if T1-23 chose it. Validation and clear errors.
- **Done when:** I can enter, edit and delete each kind of record.

### T1-40 · Dashboard
`BUILD` · Owner: Claude · Status: todo · Depends on: T1-38, T1-36, T1-08

- **Scope:** total value (INR, with USD view), P&L, XIRR, allocation chart, holdings table, prices-last-updated.
- **Done when:** numbers match the API and the charts render with my data.

### T1-41 · Holding detail page
`BUILD` · Owner: Claude · Status: todo · Depends on: T1-40

- **Scope:** lots and transactions, price chart, P&L and XIRR for that holding.
- **Done when:** works for an Indian stock, a mutual fund and a US ETF.

---

## M6 — Verify (Phase 1 exit)

### T1-42 · Enter my real holdings, cash and remittances
`VERIFY` · Owner: me · Status: todo · Depends on: T1-39

- **Done when:** everything I own is in Friday.
- **Evidence:** —

### T1-43 · Reconcile against broker and CAS statements
`VERIFY` · Owner: both · Status: todo · Depends on: T1-42, T1-34, T1-35

- **Done when:** units, cost and current value match my broker statements and CAS within rounding. Any difference is explained or fixed (new tasks if needed).
- **Evidence:** —

### T1-44 · One week of unattended daily updates
`VERIFY` · Owner: both · Status: todo · Depends on: T1-32

- **Done when:** a week of daily runs, including at least one night with the laptop asleep, shows every trading day filled once, no duplicates, holidays skipped.
- **Evidence:** —
