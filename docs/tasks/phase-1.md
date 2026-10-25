# Phase 1 — Fund tracker and planner · Task board

> **Goal:** see all my mutual funds in one place with correct numbers, test target splits on history, and know where new cash should go. No AI. NAVs update daily by themselves.
> **Exit:** all my real funds are in, NAVs update daily, numbers match my statements, and the cash plan matches a hand calculation ([`phases.md`](../phases.md)).
> **Scope (D-043):** mutual funds only. Indian stocks and ETFs come in Phase 6, US holdings and LRS in Phase 7. Buckets, backtests and NAV history come from the earlier `ragnar2801/Friday` app, rebuilt here on EDITH's stack.
> **Already fixed:** React frontend + Python backend (D-023) · SQLite on the laptop (D-013) · free data only (D-012) · scheduled fetch + catch-up (D-022) · Windows + Task Scheduler (D-027) · Nifty 50 benchmark (D-043).
> Everything else is decided **inside the task that needs it** (see each task's *Decisions* list). How this board works: [`README.md`](README.md)

**Board version:** 3 (2026-10-25: re-planned for funds first, D-043; T1-03 to T1-11 dropped, their content moved to T1-12 onward and Phases 6–7) · **Done:** 7 / 13

---

## Board

| ID | Task | Kind | Owner | Status | Depends on |
|----|------|------|-------|--------|------------|
| T1-01 | Foundation: app skeleton running on Windows | Infra | Claude | done | — |
| T1-02 | Instruments: find any stock, fund or ETF | Feature | Claude | done | T1-01 |
| T1-12 | Fund NAVs: full history, daily catch-up, refresh | Feature | Claude | done | T1-02 |
| T1-13 | Buckets: my target split | Feature | Claude | done | T1-12 |
| T1-14 | Backtests: lump sum, SIP, SWP and custom, vs Nifty 50 | Feature | Claude | done | T1-12, T1-13 |
| T1-15 | Fund holdings: lump sums, SIPs and sells | Feature | Claude | done | T1-12 |
| T1-16 | Cash, and "I have ₹X, where does it go?" | Feature | Claude | done | T1-13, T1-15 |
| T1-17 | Portfolio view vs target: value, P&L, XIRR, drift | Feature | Claude | todo | T1-13, T1-15, T1-16, T1-22 |
| T1-18 | Daily NAV update on Windows | Infra | both | todo | T1-12 |
| T1-19 | Phase 1 acceptance: my real funds, reconciled | Verify | both | todo | T1-12 to T1-18 |
| T1-20 | Plan and option for every fund (AMFI leaves 5,623 blank) | Feature | Claude | todo | T1-02 |
| T1-21 | UI kit and copy clean-up: no prose, info icons, no build talk | Feature | Claude | todo | T1-16 |
| T1-22 | Journeys: new navigation, one fund page, Invest, Models, Settings | Feature | Claude | todo | T1-21 |
| ~~T1-03 to T1-11~~ | Board v2 tasks for stocks, US, LRS and the watchlist | — | — | dropped | see [Dropped tasks](#dropped-tasks-board-v2) |

```
T1-01 ─► T1-02 ─► T1-12 ─┬─► T1-13 ─┬─► T1-14
                         │          └──────────────┐
                         ├─► T1-15 ─► T1-16 ─► T1-17 ─┐
                         └─► T1-18 ───────────────────┴─► T1-19
```

T1-14 and T1-15 can be built in parallel. T1-18 can start any time after T1-12. T1-21 and T1-22 (UI rework, [`ui-redesign.md`](../ui-redesign.md)) come before T1-17, so the portfolio view is built once in its final place.

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
## T1-12 · Fund NAVs: full history, daily catch-up, refresh
`Feature` · Owner: Claude · Status: done · Depends on: T1-02

**Goal:** Friday has every NAV since launch for the funds I track, catches up on missed days by itself, and I can trigger a refresh from the UI or the command line.

**Scope**
- A NAV table keyed by (fund, date), filled from the full history on first sync and only the missing days after that
- "Tracked" funds: the ones I mark, plus every fund in a bucket and every bucket's benchmark
- Sync for all tracked funds or one fund: from the UI (Data status page, instrument page), `friday navs sync` / `just navs`, and later Task Scheduler (T1-18); a run log
- Instrument page: NAV chart with ranges, latest NAV, 1-day / 1-year / since-launch change, CAGR, 52-week range, recent NAVs
- Data status page: tracked funds with first and last NAV dates, last sync, sync buttons

**Decisions** (2026-10-25, decided while bringing Friday's features in; review welcome)
- Decided: NAV history and daily updates from **mfapi.in** (`api.mfapi.in/mf/<scheme code>`, a free mirror of AMFI data with full history in one request per fund; checked 2026-10-25). **AMFI `NAVAll.txt`** is the fallback for the latest NAV when mfapi fails (D-044)
- Decided: NAVs are stored **exactly as published, up to 8 decimal places** (some AMCs publish 8, e.g. Bandhan's arbitrage and debt funds), with a new API type `Nav`; zero and missing NAVs are skipped. Amends D-032's 4 places for NAVs (D-045)
- Decided: **one sync model, from Friday:** catch up to today for every tracked fund, upserting on (fund, date) so a re-run adds nothing. Tracked = marked by me, in a bucket, or a bucket's benchmark. Sync runs on demand in Phase 1 (button, CLI) and daily from T1-18. Each run is logged with per-fund results. Mutual funds and AMFI-listed schemes only (D-046)
- Decided: NAV statistics (changes, CAGR, 52-week range) are computed in the backend, like every other figure (D-032, D-046)

**Progress (2026-10-25)**
- Built: tables `fund_navs`, `tracked_funds`, `nav_syncs` (migration 0003); mfapi.in and AMFI `NAVAll.txt` parsers; downloads with retries; sync that stores only missing or corrected NAVs and commits fund by fund; NAV statistics; endpoints `GET /navs/status`, `POST /navs/sync`, `GET /instruments/{id}/navs`, `GET /instruments/{id}/nav-summary`, `PUT`/`DELETE /instruments/{id}/tracking`; `friday navs track <AMFI code>` and `friday navs sync` / `just navs`; Data status page; NAV card on fund pages (figures, chart with 1M … Max, recent NAVs); Friday's SVG chart ported to React (D-050), drawn at the real width so it stays readable on a phone
- Live run (2026-10-25): Parag Parikh Flexi Cap Direct Growth, 3,298 NAVs from 28 May 2013; UTI Nifty 50 Index Fund Direct Growth, 3,398 NAVs from 2 Jan 2013; both in 2.7 s, and a second run added nothing. Latest NAV ₹88.9695 on 23 Oct 2026, the same as AMFI's `NAVAll.txt`. With the five funds of the bucket below: 16,603 NAVs
- Found: AMFI's file had 475 schemes with 5–8 decimal places (D-045). 5,623 of its 14,412 rows have blank Plan and Option columns (e.g. Motilal Oswal Midcap), so search can't tell Direct Growth from IDCW for them → new task T1-20
- Tests: parsers on slices of the real responses (8-place NAVs, `0.0000` NAVs, wrong scheme, HTML instead of JSON), sync (first sync, repeat adds nothing, missed days filled exactly, corrections, AMFI fallback, one fund failing, all failing, untracked funds refused), statistics by hand, API; frontend: Data status page, NAV card, tracking
- Windows CI green: run #7, https://github.com/ragnar2801/EDITH/actions/runs/40160211154

**Done when**
- Tracking a fund pulls its full history; a second sync adds nothing; skipping days and syncing fills exactly the missing NAVs
- When mfapi is unreachable, the latest NAV still comes from AMFI's file
- The NAV and changes on the instrument page match the AMC or AMFI website for a spot-checked fund
- Tests cover the parsers (on slices of real responses), sync, fallback and the statistics

---

## T1-13 · Buckets: my target split
`Feature` · Owner: Claude · Status: done · Depends on: T1-12

**Goal:** I can write down my target split (e.g. 40% flexi cap, 25% large cap, 20% mid cap, 15% small cap) as a bucket, with a rebalance policy and a benchmark, and keep several to compare.

**Scope**
- Buckets: name, description, funds with weights, rebalance policy, benchmark
- Create, edit, delete; pick funds with the instrument search
- Adding a fund to a bucket starts tracking its NAVs
- Buckets page and a short summary on the dashboard

**Decisions** (2026-10-25, decided while bringing Friday's features in; review welcome)
- Decided: weights are exact percentages (2 decimal places) that must **add up to exactly 100**; nothing is silently normalised (Friday normalised). Funds only: AMFI schemes. Rebalance policy none / monthly / quarterly / yearly. Benchmark: any fund, default **UTI Nifty 50 Index Fund – Direct Plan – Growth** (AMFI 120716, history from 2013) for the Nifty 50 (D-043). Deleting a bucket deletes its saved backtests (D-047)

**Progress (2026-10-25)**
- Built: tables `buckets`, `bucket_funds` (migration 0004); validation (exact total of 100, funds only, no duplicates, unique names); endpoints `GET`/`POST /buckets`, `GET`/`PUT`/`DELETE /buckets/{id}`, `GET /buckets/default-benchmark`; funds and benchmarks of buckets count as tracked; saving a bucket downloads NAVs for funds that have none; Buckets page with an editor (fund search limited to mutual funds, running total, equal weights) and a dashboard summary
- The editor's running total and "equal weights" work in whole basis points in the browser (weights, not money: 0.1 + 0.2 + 99.7 is exactly 100); the backend's check is the one that counts
- Live: bucket *Core 40/25/20/15* (Parag Parikh Flexi Cap, Nippon India Large Cap, Motilal Oswal Midcap, Nippon India Small Cap, all Direct Growth) against the UTI Nifty 50 Index Fund; NAVs for all four from 25 Feb 2014
- Tests: create, read, edit (weights, order, members), delete, totals of 99.99 and 100.01 refused with the reason, JSON numbers refused, a stock refused, a fund listed twice, duplicate names, tracking and untracking; frontend: editor, exact totals, equal weights, refused save, dashboard
- Windows CI green: run #8, https://github.com/ragnar2801/EDITH/actions/runs/40160688693

**Done when**
- A bucket of four funds with weights adding to 100 saves; 99.99 is rejected with the reason
- Its funds and benchmark are tracked and their NAVs sync
- Tests cover validation and the API

---

## T1-14 · Backtests: lump sum, SIP, SWP and custom, vs Nifty 50
`Feature` · Owner: Claude · Status: done · Depends on: T1-12, T1-13

**Goal:** I can see how a bucket would have done in the past, invested as a lump sum, as a SIP, drawn down as an SWP, or along my own timeline of buys and sells, next to the same money in the Nifty 50 index fund.

**Scope**
- Engine (ported from Friday): Regular (lump sum, optional rebalance), SIP (weekly / monthly / quarterly), SWP (with depletion date), Custom (positions between dates, or explicit buys and sells)
- Metrics: final value, invested, withdrawn, absolute return, CAGR, XIRR, max drawdown, volatility, Sharpe, Sortino; per-fund end values; for Custom, per-fund P&L and the executed trade log
- Benchmark run through the same strategy
- Save, name, load and delete runs per bucket
- Chart with zoom presets (1M … 5Y, Max), hover, drag to measure an interval, buy/sell markers; interval figures
- Backtest page

**Decisions** (2026-10-25, decided while bringing Friday's features in; review welcome)
- Decided: engine semantics as in Friday: NAVs aligned on the union of dates and carried forward; a run starts when every fund has a NAV (and says so if that clips the requested start); SIP instalments on the first NAV date of each period; SWP sells pro rata to value; Custom executes on the first NAV date on or after each trade, sells before buys on the same day. **Amounts and units are exact `Decimal`s** like a ledger (D-032); ratios (XIRR, CAGR, volatility, Sharpe, Sortino, drawdown) are floats rounded to 2 places. A NAV more than 1.8× or under 0.55× the median of its neighbours is treated as a bad tick and replaced, **with a warning** (Friday did it silently). The **benchmark gets the same cash flows** as the bucket (Friday scaled a lump sum, which misleads for SIPs and SWPs). Risk-free rate is an input, default 0. Costs, exit loads and taxes are off (D-048)
- Decided: every run is stored; the last 20 unsaved runs are kept, saved runs stay until deleted. **Interval figures come from the backend** for a stored run (Modified Dietz return, max drawdown, start and end value, money in and out in the window), so the UI does no arithmetic (D-049)
- Decided: charts use **Friday's own SVG line chart, ported to React**; no chart library yet. Coordinates use JavaScript numbers for drawing only; every figure shown as text comes from the API. Chart libraries stay candidates for T1-17 (D-050)

**Progress (2026-10-25)**
- Built: `friday.core.backtest` (engine, request and result models, service), table `backtest_runs` (migration 0005), endpoints `POST /backtests`, `GET /buckets/{id}/backtests`, `GET`/`PATCH`/`DELETE /backtests/{id}`, `GET /backtests/{id}/interval`; Backtest page in Friday's layout (controls on the left; figures next to the benchmark; chart with zoom presets, hover, drag to measure and trade markers; window figures; funds at the end, or P&L per fund and the trade log for custom runs); save with a name, load, delete
- Changed from Friday, found while porting: the benchmark gets the **same cash flows** (Friday compared a SIP with a lump sum); bad-tick replacement now **warns**, and compares each NAV with up to 5 neighbours each side **within 15 days** (Friday's 2-neighbour window let two bad ticks in a row overwrite a good NAV next to them; without the day limit a gap in the history looked like a spike); CAGR is **time-weighted for every strategy** and drawdown, volatility, Sharpe and Sortino come from the same time-weighted index, so SIPs and SWPs are comparable with lump sums; a **same-day sell and buy nets off** in money put in and taken out; weekly SIPs use ISO weeks (Monday start); custom trades always execute at the NAV (Friday allowed a price override, which has no meaning for funds); window figures come from the backend (D-049)
- Live (2026-10-25, *Core 40/25/20/15*, 1 Jan 2015 to 23 Oct 2026): SIP of ₹10,000 a month: ₹14.2 lakh in, ₹40.31 lakh at the end, XIRR 16.56% vs 10.15% for the same SIP in the Nifty 50 index fund. Lump sum of ₹1 lakh: ₹5.61 lakh, CAGR 15.72% vs 9.91%. SWP from ₹50 lakh at ₹40,000 a month: the money lasted; ₹56.4 lakh withdrawn and ₹1.19 crore left (the index fund: ₹47.5 lakh left). Max drawdown 35% (2020). Each run takes 0.2–0.35 s
- Not ported from Friday: its Help page (EDITH's README and docs cover it), its Settings page (the theme follows the system; the risk-free rate is a backtest field) and NSE stock prices from Yahoo (Phase 6)
- Tests: 26 engine tests on hand-worked examples (Friday's own, plus rebalancing, SIP and SWP by hand, weekly SIP dates, pro-rata SWP, a switch netting off, oversell, holiday execution, benchmark replay and its cap, growth index, Modified Dietz by hand, despiking cases) and 17 API tests (runs, start clipped, save/list/load/delete, pruning to 20, window figures, custom runs, refused parameters, funds outside the bucket, no NAVs yet, bucket deletion); frontend: run, window figures, save and load, refused run, choosing a bucket
- Totals across the repo: backend 228 tests, frontend 35; `just lint`, `just test`, `just api-check`, `just smoke` pass on Linux; screenshots checked at desktop and phone width, light and dark
- Windows CI: run #9, https://github.com/ragnar2801/EDITH/actions/runs/40161747646
- Worth doing once on my laptop: `just setup`, `just instruments --source amfi`, then build my real bucket and run a SIP backtest

**Done when**
- Hand-worked examples pass as unit tests: lump sum doubling, weighted split, SIP at a flat NAV (XIRR ≈ 0), SWP depletion, a Custom rotation, a capped oversell, the benchmark getting the same SIP
- A SIP backtest of a real bucket from 2015 runs in under a few seconds and its benchmark line is the same SIP into the Nifty 50 index fund
- Interval figures for a window match a hand calculation

---

## T1-15 · Fund holdings: lump sums, SIPs and sells
`Feature` · Owner: Claude · Status: done · Depends on: T1-12

**Goal:** I enter my lump sums and SIPs, sell units from the lots I choose, and Friday shows the units and cost I hold in each fund.

**Scope** (simplified 2026-10-25: no tax, folios, switches, mergers, IDCW or stamp duty)
- A holding is keyed by **fund** only (`instruments.id`, one per AMFI scheme code, D-038). No folios
- Two ways money goes in: **lump sum** (one buy) and **SIP** (amount, day of month, start date, optional end date)
- **Each buy is a lot** with its units, NAV, amount and a **units remaining** balance. Selling is not a transaction type: I pick lots and how many units to take from each
- API for create / edit / delete / list; holdings page, fund holding page with lots and SIPs, forms with `InstrumentSearch kind="mutual_fund"`; units and cost per fund (value comes in T1-17)
- Holding a fund tracks it for NAVs (D-046)

**Decisions** (approved 2026-10-25)
- Decided: a holding is keyed by fund only (`instruments.id`). Each buy, a lump sum or a SIP instalment, is one **lot**: date, amount (2 places), NAV, units (8 places stored, 3 shown) and a stored **units remaining**. Tax, folios, switches, scheme mergers, plan switches, IDCW, stamp duty and exit loads are out of Phase 1 (D-051)
- Decided: when I leave the NAV blank, it is the fund's NAV for that date from the stored history (refused if Friday has none: type it). When I leave units blank, they are amount ÷ NAV rounded to 3 places, as AMCs allot; I can type my statement's units instead (D-052)
- Decided: a **SIP** is amount, day of month (1–28), start date and optional end date. Friday adds one instalment per month on the first NAV date on or after the SIP day (within 10 days; a month without one, such as a data gap or before the fund's first NAV, has no instalment), up to the latest stored NAV, when the SIP is saved and after every NAV sync. An instalment can be edited (my statement's figures) or skipped (a missed month); editing the SIP rebuilds the other instalments and keeps those. A SIP with sold instalments can't be deleted (D-053)
- Decided: **selling is taking units from lots I pick**, not a transaction type. A sale has a date and, per lot, the units taken; the NAV is that date's NAV from history (or typed). Each take is kept (lot, date, units, NAV) so T1-17 can work out realised P&L and XIRR, and deleting it puts the units back. A lot can't go below zero, be edited below the units already sold, or be deleted while it has sales (D-054)
- Decided: forms and tables are plain components, as in `BucketsPage`. No CSV import in Phase 1: SIP schedules cover most of the typing (D-055)

**Progress (2026-10-25)**
- Built: tables `sips`, `lots`, `lot_sales` (migration 0006); `friday.core.holdings.service` (lump sums, lot edits, SIP instalments, selling from picked lots, undoing a sale, units and cost per fund); endpoints `GET /holdings`, `GET /holdings/{instrument_id}`, `POST`/`PUT`/`DELETE /lots`, `POST`/`PUT`/`DELETE /sips`, `POST /sales`, `DELETE /sales/{id}`; held funds count as tracked (`used_by: holding`) and every NAV sync adds the SIP instalments its new NAVs cover
- UI: Holdings page (fund search, units, cost, lots, active SIPs) and a page per fund with lump sum, SIP, edit / skip and sell forms; lots show what was sold from them, with an undo. A fund with no NAVs is tracked and downloaded before the first lump sum or SIP is saved. The *Transactions* placeholder is gone: lots live on the fund's page
- Checked on a copy of the live database: a ₹5,000 SIP on the 5th of Parag Parikh Flexi Cap from 1 Jan 2025 gave 22 instalments (weekend dates moved to the next NAV date); selling all of the Jan 2025 lot and 20 units of Feb 2025 left 1,140.793 units at a cost of ₹1,03,245.71, matching a hand calculation
- Tests: 8 on SIP dates (holidays, end date, year rollover, a data gap, before the first NAV, waiting for NAVs, 3-place units) and 14 API tests (SIP plus lump sum, selling from picked lots, skip, step-up rebuild, undo, typed statement figures, edited instalments kept, oversell, missing NAVs, one fund per sale, protected lots, bad input, funds only, tracking and sync); frontend: holdings list, lump sum with NAV download, sell, refused sale, SIP and undo

**Done when**
- A test portfolio with a lump sum and a SIP fund that was partly sold shows correct units, cost and units remaining per lot
- SIP instalment dates (holidays, a skipped month, an end date) and lot balances have unit tests with hand-worked values

---

## T1-16 · Cash, and "I have ₹X, where does it go?"
`Feature` · Owner: Claude · Status: done · Depends on: T1-13, T1-15

**Goal:** I record my INR cash (with an emergency earmark), choose which bucket is my target, and Friday tells me exactly how much to put in each fund so I move towards the target without selling.

**Scope**
- INR cash accounts: name, balance, earmark (emergency / deployable / reserved); emergency kept in a named arbitrage or liquid fund counts as emergency, never deployable
- Mark one bucket as **my target split**
- Plan: top up emergency first, then send new cash to the funds furthest below target (no sells), with the resulting split; a stagger plan (STP via a liquid or arbitrage fund over N months) when the amount is above a threshold
- Plan page and API; the plan is arithmetic only (no AI)

**Decisions** (approved 2026-10-25)
- Decided: cash accounts hold the **current balance only**, INR, with an earmark: emergency, deployable or reserved (D-056)
- Decided: one row of **plan settings**: target bucket, emergency goal and fund, stagger fund, threshold (default ₹5,00,000) and months (default 6), minimum per fund (default ₹500) (D-057)
- Decided: the plan **tops up emergency money first**, then **water-fills** the target bucket on value ÷ weight (the lowest funds rise to one level; nothing is sold or pushed above target), in **whole rupees** with spare rupees to the largest remainders; a share under the minimum is dropped and the rest re-planned. Funds outside the bucket are listed and ignored; **stocks and US holdings stay out until Phase 3** (D-058)
- Decided: at or above the threshold, a **monthly transfer table** (STP) over the set months, equal whole-rupee transfers with the last month taking the rounding (D-059)

**Progress (2026-10-25)**
- Built: tables `cash_accounts` and `plan_settings` (migration 0007); `friday.core.cash.plan` (pure arithmetic: emergency top-up, water-filling, whole rupees, minimum per fund, stagger table) and `friday.core.cash.service` (accounts, settings, fund values at the latest NAV, emergency status, the plan); endpoints `GET /cash`, `POST`/`PUT`/`DELETE /cash/accounts`, `GET`/`PUT /plan/settings`, `POST /plan` (blank amount = all deployable cash)
- UI: Cash page with totals per earmark and the emergency goal, the plan (per fund: target, value and share now, invest, share after; the stagger table; funds left out), cash accounts, and plan settings (target bucket, emergency and stagger funds picked with `InstrumentSearch`)
- Checked on a copy of the live database with the CORE bucket (35 / 20 / 15 / 25 / 5): ₹6,00,000 deployable against a ₹3,00,000 emergency goal planned ₹3,00,000 to emergency and ₹3,00,000 split 1,05,000 / 60,000 / 45,000 / 75,000 / 15,000; ₹12,00,000 added a six-month table of ₹1,50,000 a month. Phone width has no sideways scroll
- Tests: 8 hand-worked plan cases (on target, one fund far below, sharing beyond the lowest fund, whole rupees with the spare rupee, minimum per fund, emergency first, a six-month stagger, below the threshold) and 5 API tests (totals and emergency status, the full plan with the emergency fund kept out, staggering, settings rules, account edits); frontend: plan with stagger table, blank amount and errors, adding an account

**Done when**
- Plans for three hand-worked cases (all below target, one far below, a large amount needing staggering) match a hand calculation
- Emergency money is never in a plan

---

## T1-17 · Portfolio view vs target: value, P&L, XIRR, drift
`Feature` · Owner: Claude · Status: todo · Depends on: T1-13, T1-15, T1-16, T1-22

**Goal:** the dashboard shows what my funds are worth, how they've done against the Nifty 50 index fund, and how far each is from my target split.

**Scope**
- Calculations (backend only): value per fund (latest NAV), realised and unrealised P&L, XIRR per fund and overall, the same cash flows into the Nifty 50 index fund for comparison, allocation by fund and by equity / debt / gold (D-040 classification), drift vs the target bucket
- Dashboard: totals, allocation, drift, holdings table, NAVs last updated; fund detail page: lots, transactions, NAV chart, P&L and XIRR

**Decisions**
- Returns definitions (what counts in P&L and XIRR)
- Charts library for allocation (candidates: keep the SVG chart from D-050 and add a bar · ECharts · Recharts)
- Drift bands shown now, or only in Phase 3

**Done when**
- Hand-worked examples (one lump sum, SIPs with a partial sell) pass as unit tests
- Dashboard numbers match the API exactly

---

## T1-18 · Daily NAV update on Windows
`Infra` · Owner: both · Status: todo · Depends on: T1-12

**Goal:** NAVs update every day without me doing anything, including after the laptop was asleep.

**Scope**
- One Task Scheduler entry (installed and removed by a script) that runs the NAV sync daily (about 23:30 IST, after AMFI publishes), with *run as soon as possible after a missed start* on and *only on AC power* off (D-027). It calls one entry point that `friday tick` replaces in Phase 4a with a one-line change
- Optionally: start the Friday server at logon
- Logs in `logs/`; the Data status page shows recent runs

**Decisions**
- Job time; whether the server starts at logon; log rotation

**Done when**
- After install, the job runs at its time and shows on the Data status page
- After a night asleep, the missed run happens once on wake and no NAV is missing
- Uninstall removes the task

---

## T1-19 · Phase 1 acceptance: my real funds, reconciled
`Verify` · Owner: both · Status: todo · Depends on: T1-12 to T1-18

**Goal:** prove Phase 1 does what it promised, on my real funds.

**Scope**
- Enter all my real fund transactions, cash and my target bucket (me)
- Reconcile units, cost and value against my AMC / CAS statements
- Let it run unattended for a week, including nights asleep
- Anything wrong becomes a new task on this board

**Done when**
- Units, cost and value match my statements within rounding, or every difference is explained
- A week of daily updates shows every NAV date filled once, no duplicates

---

## T1-20 · Plan and option for every fund
`Feature` · Owner: Claude · Status: todo · Depends on: T1-02

**Goal:** search and buckets always show whether a fund variant is Direct or Regular, Growth or IDCW, so I never pick the wrong one.

**Scope**
- Found in T1-12 (2026-10-25): 5,623 of the 14,412 rows in AMFI's `NAVAll.txt` have blank Plan and Option columns, and some active funds' names don't say either (e.g. Motilal Oswal Midcap: 127042 is Direct Growth, 127044 Direct IDCW; search showed 127044 first, unlabelled). The wrong pick understates backtest returns
- AMFI's scheme master (`portal.amfiindia.com/DownloadSchemeData_Po.aspx?mf=0`, CSV, checked 2026-10-25) has a *Scheme NAV Name* such as "Motilal Oswal Midcap Fund-Direct Plan-Growth Option", plus launch dates and minimum amounts
- Import it alongside `NAVAll.txt` and fill plan and option where they're blank; keep "Direct + Growth first" in search (D-042)

**Decisions**
- Source and refresh rhythm for the scheme master; what to do when the two files disagree

**Done when**
- Searching "motilal oswal midcap" shows 127042 first, labelled Direct · Growth
- No active scheme with a scheme-master entry is left without a plan and option
- Refresh twice changes nothing; tests cover the parser on a slice of the real file

---

## T1-21 · UI kit and copy clean-up: no prose, info icons, no build talk
`Feature` · Owner: Claude · Status: todo · Depends on: T1-16

**Goal:** every screen looks and reads like a finished product: a title and its actions, figures and controls, and an info icon where a term needs defining. No paragraphs, task IDs, CLI commands or "coming soon".

**Scope**
- Found 2026-10-25 (UI review, [`ui-redesign.md`](../ui-redesign.md) sections 1, 2, 6 and 7): every page opens with an explanatory paragraph, card descriptions explain algorithms, task IDs and `just` commands appear in the UI, and each page hand-rolls headers, tables, fields and confirms
- Components (shadcn by hand on the installed `radix-ui`): `PageHeader`, `InfoTip`, `Field`, `Dialog`, `AlertDialog`, `Tabs`, `DropdownMenu`, `DataTable`, `EmptyState`, `Toast`, `Skeleton`
- Apply them to today's screens without moving anything: strip prose and build talk, hint lines → info tips or placeholders, `window.confirm` → confirm dialog, "Saved." → toast, row buttons → `⋯` menu, AMFI codes out of list rows, `SectionPage` deleted
- Screen rules (`ui-redesign.md` section 2) added to `CLAUDE.md`

**Decisions** (candidates in `ui-redesign.md` section 9)
- Screen rules into `CLAUDE.md` (#1); toast component (#7); UI words: bucket, lot, earmark, deployable (#3 to #5)

**Done when**
- No page has a subtitle paragraph or an explanatory card description; no UI string contains a task ID, a `just` command or a data-source name
- Every former hint is an info tip (keyboard-focusable, readable on tap) or gone
- Deletes go through a confirm dialog; saves and deletes show a toast
- `just lint`, `just test` pass; screenshots at desktop and phone width, light and dark

---

## T1-22 · Journeys: new navigation, one fund page, Invest, Models, Settings
`Feature` · Owner: Claude · Status: todo · Depends on: T1-21

**Goal:** the app is organised around what I come to do (see what I own, record a transaction, invest new cash, design and test a split, look up a fund), each on its own screen.

**Scope** (`ui-redesign.md` sections 3 to 5)
- Navigation: Portfolio · Invest · Models · Funds, plus a header with NAV freshness (sync on click), a global `+ Add` and Settings
- Portfolio (`/`): funds tab (today's holdings list) and cash tab (accounts); setup checklist when empty
- Add transaction dialog (lump sum, SIP, sell), global and pre-filled from a fund
- Invest (`/invest`): the cash plan alone, amount pre-filled with investable cash
- Models: list with a Target badge and "Set as target"; full-page editor; model page with Overview and Backtest tabs (no bucket picker)
- One fund page (`/funds/:id`) with Overview, Transactions and Details tabs, replacing the instrument and holding pages
- Settings: invest rules and data (sync log, tracked funds, list status)
- Redirects from the old routes; fund search limited to mutual funds

**Decisions** (candidates in `ui-redesign.md` section 9)
- Top bar or sidebar (#2); where cash accounts live (#6); fund-list download from the UI (#8); hide stocks and US listings (#9)

**Done when**
- Journeys J1 to J8 in `ui-redesign.md` work as written, checked in the running app
- Recording a lump sum takes 3 steps from any screen without leaving it
- Clicking any fund name anywhere opens the same fund page
- The target model is visible on Models, Invest and Settings, and set from Models
- Old URLs redirect; `just lint`, `just test`, `just api-check` pass; screenshots at desktop and phone width, light and dark

---

## Dropped tasks (board v2)

Dropped on 2026-10-25 when Phase 1 was re-planned for mutual funds first (D-043). IDs are not reused. Their sections are kept below as written, for history; where their content went:

| ID | Was | Now |
|----|-----|-----|
| T1-03 | Holdings for all instruments | Funds: T1-15 · stocks (splits, bonuses, mergers): Phase 6 |
| T1-04 | Cash and remittances, LRS totals | INR cash: T1-16 · remittances and LRS: Phase 7 |
| T1-05 | India prices and NAVs, with backfill | NAVs: T1-12 · NSE prices and holidays: Phase 6 |
| T1-06 | US prices and USD/INR | Phase 7 |
| T1-07 | Watchlist | Phase 2 |
| T1-08 | Portfolio view | Funds: T1-17 · stocks and USD views: Phases 6–7 |
| T1-09 | Daily automation on Windows | T1-18 |
| T1-10 | Phase 1 acceptance | T1-19 |
| T1-11 | REITs, InvITs and BSE-only listings | Phase 6 |

### T1-03 · Holdings: record what I own
`Feature` · Owner: Claude · Status: dropped · Depends on: T1-02

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


### T1-04 · Cash and remittances, with LRS totals
`Feature` · Owner: Claude · Status: dropped · Depends on: T1-01

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


### T1-05 · India market data: stock prices and fund NAVs, with backfill
`Feature` · Owner: Claude · Status: dropped · Depends on: T1-02

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


### T1-06 · US market data and USD/INR rates
`Feature` · Owner: Claude · Status: dropped · Depends on: T1-05

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


### T1-07 · Watchlist
`Feature` · Owner: Claude · Status: dropped · Depends on: T1-02, T1-05

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


### T1-08 · Portfolio view: value, P&L, allocation, XIRR
`Feature` · Owner: Claude · Status: dropped · Depends on: T1-03, T1-04, T1-05, T1-06

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


### T1-09 · Daily automation on Windows
`Infra` · Owner: both · Status: dropped · Depends on: T1-05, T1-06

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


### T1-10 · Phase 1 acceptance: my real data, reconciled
`Verify` · Owner: both · Status: dropped · Depends on: T1-01 to T1-09

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


### T1-11 · REITs, InvITs and BSE-only listings
`Feature` · Owner: Claude · Status: dropped · Depends on: T1-02

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

