# Friday — Agent Architecture & Plan

> Living design doc for **Friday**, a personal stock analyst / portfolio manager.
> This file is the memory for brainstorming sessions: decisions, the current plan, open questions and ideas for later.
> Update it every session. Never delete history. Supersede it (see [How to use this file](#how-to-use-this-file)).
> Plain-language overview and user journeys: [`docs/architecture.md`](docs/architecture.md).

**Current plan:** v1.2 · **Last updated:** 2026-10-24

---

## 1. What Friday is

A simple web app plus a team of background agents that:

1. **Tracks** my cash (INR and USD) and my portfolio (Indian stocks and mutual funds, US stocks and ETFs).
2. **Researches** a manually curated watchlist and the wider market.
3. **Suggests** what to do in a Suggestions tab: where to put idle cash, when to rebalance, what to add, trim or switch, with reasons.

Friday **advises**. I **execute** trades myself at my broker.

### Principles

- **Code computes, LLMs judge.** Prices, returns, XIRR, drift, ratios, indicators and tax impact are deterministic code exposed as tools. LLMs interpret, weigh evidence and explain. No arithmetic inside prompts.
- **Watch cheaply, think expensively only when needed.** Most of the "agents" are plain code. An LLM only wakes up on a meaningful trigger.
- **One voice to the user.** Only the CIO agent creates suggestions. Every other agent writes research notes.
- **Every suggestion is falsifiable.** Each one states what to do, how much, why, how confident it is, and what would prove it wrong. Then it gets scored.
- **Beat the index or buy the index.** Every stock or active-fund idea must argue why it beats simply buying the index fund. If it can't, the suggestion is the index fund.
- **Policy over prediction.** Every suggestion is judged against my written Investment Policy Statement (IPS).
- **Low noise.** Long-term investing means few, high-quality suggestions. Silence is a valid output.
- **Laptop-first.** The system must survive sleep, reboot and going offline without losing or duplicating work.

---

## 2. Decision log

| ID | Date | Decision | Rationale | Status |
|----|------|----------|-----------|--------|
| D-001 | 2026-10-24 | Markets: **India** (NSE/BSE stocks, Indian mutual funds) and **US** (NASDAQ-listed stocks, US ETFs) | Where I invest | Active |
| D-002 | 2026-10-24 | **Watchlist is curated manually** by me | I want control over the universe | Active |
| D-003 | 2026-10-24 | Holdings and cash are entered **manually** (no broker sync in v1) | Simplest. Broker/CAS import comes later | Active |
| D-004 | 2026-10-24 | Investment style: **long-term** (buy, hold, rebalance). No intraday or swing trading | Matches my goals. Lets agents run on low cadence | Active |
| D-005 | 2026-10-24 | **Single user** (me). No multi-tenancy | Keeps auth and data model simple | Active |
| D-006 | 2026-10-24 | **Advisory only.** Friday never places orders | Safety. I stay in the loop | Active |
| D-007 | 2026-10-24 | Screener agent and external tip sources are **future**, not v1. When added, they feed the *same* pipeline (they propose ideas and never create suggestions directly) | Keeps one research path and one quality bar | Planned |
| D-008 | 2026-10-24 | Deterministic tools for all numbers. LLMs for judgment and narrative | Reproducibility, cost, correctness | Active |
| D-009 | 2026-10-24 | Base reporting currency **INR**. USD positions are shown in both currencies | I think in INR | Proposed (confirm) |
| D-010 | 2026-10-24 | **Indian tax resident.** US investing via **LRS**. Existing US holdings and USD cash may already be there | Drives tax, TCS, remittance limits and estate-tax checks | Active |
| D-011 | 2026-10-24 | Return target: **beat Nifty 50 and S&P 500 by 5–10% a year**. Recorded as a *stretch* goal. The working target is to beat a blended benchmark after costs and taxes, measured by the Scorekeeper | 5–10% sustained outperformance is rare even for professionals. A measurable target keeps Friday honest | Active (stretch) |
| D-012 | 2026-10-24 | **Free data only:** NSE (bhavcopy, announcements), AMFI, Yahoo Finance, SEC EDGAR, FRED | No paid subscriptions | Active |
| D-013 | 2026-10-24 | **Runs locally on my laptop, 24/7.** One process plus SQLite. Must tolerate sleep, reboot and offline | Simple, private, free hosting | Active |
| D-014 | 2026-10-24 | Most events wait for the **weekly CIO run**. Only *urgent* events trigger a mid-week CIO run, at most once a day | Long-term style. Avoids noise and LLM cost | Proposed |
| D-015 | 2026-10-24 | Every BUY/ADD must justify itself against the **index-fund alternative** | Keeps the alpha target honest | Proposed |
| D-016 | 2026-10-24 | **LLM = Claude, run through Claude Code.** Friday is a Claude Code project: agents are subagents, workflows are skills, tools come from a local MCP server | No custom agent framework to build. Same setup works interactively and unattended | Active |
| D-017 | 2026-10-24 | **Plain Python for everything that doesn't need judgment** (fetchers, watchers, LRS ledger, Scorekeeper, Housekeeper). Claude Code is only invoked for LLM agents | Doesn't spend Claude usage on downloads and arithmetic | Active |
| D-018 | 2026-10-24 | **Scheduling:** one OS scheduler entry runs `friday tick` every 15 min. The tick decides what's due, runs Python jobs, and starts `claude -p "/<skill>"` for LLM jobs. Manual runs: `claude` in the project, then `/<skill>` | OS-agnostic, handles catch-up and dedupe itself, no app needs to stay open | Proposed |
| D-019 | 2026-10-24 | **Hard rules are enforced in code** inside the MCP server (`create_suggestion` runs Risk Guard checks before saving). Only the CIO subagent is allowed the `create_suggestion` tool | An LLM can't talk its way past a rule. Web content can't inject a suggestion | Proposed |
| D-020 | 2026-10-24 | Unattended runs use `--permission-mode dontAsk` with an allowlist (Friday MCP tools, web search/fetch, read). Anything else is denied, never prompted | Nobody is there to answer prompts at 3 a.m. | Proposed |

---

## 3. Current plan — v1.2

### 3.1 Scope

**In v1**
- Manual entry of holdings (as tax lots), cash accounts, LRS remittances and the watchlist
- Portfolio view: allocation, P&L, XIRR, drift vs target, benchmark comparison (INR and USD)
- Suggestions tab: ranked suggestions with accept, reject and snooze, plus history and scoring
- The v1 agents in 3.3

**Not in v1** (see [Roadmap](#4-roadmap--parking-lot))
- Broker or CAS sync, auto-trading, screener or idea discovery, external tips, technical and sentiment agents, intraday alerts, full tax agent, multi-user

### 3.2 Runtime components (one laptop)

| Component | Role | Notes |
|-----------|------|-------|
| **Web UI** | Portfolio, cash, watchlist, suggestions, weekly letter, ask-Friday chat | Served on `localhost` |
| **API / backend** | CRUD for my data. Serves the UI. Exposes tools to agents | Same process as the scheduler |
| **SQLite DB** | All state: holdings, prices, notes, events, suggestions | One file, backed up daily |
| **Orchestrator** (`friday tick`) | Decides what's due, event dispatch, catch-up after sleep, retries, one Claude job at a time, usage cap | Python, not an LLM. The "24/7" part |
| **Data adapters** | One adapter per free source, with fallback and caching | NSE → Yahoo fallback for India |
| **Friday MCP server** | Exposes DB reads, calculations and writes as typed tools to Claude. Enforces hard rules | Local stdio server registered in `.mcp.json` |
| **Agent runner** | Claude Code: `claude -p "/<skill>"` for scheduled runs, interactive `claude` for manual ones | Only part that uses Claude usage (D-016) |
| **OS scheduler** | Runs `friday tick` every 15 min (launchd / cron / systemd timer / Task Scheduler) | Keeps it "always on" |

### 3.3 Agent roster

There are 22 components, but only about **9 use an LLM**. The rest are deterministic code.
LLM column: **—** = none, **S** = small/fast model, **L** = large model.

#### Layer 0 — Data fetchers (code)

| ID | Agent | Work | Source (free) | Frequency (IST) | LLM | v1 |
|----|-------|------|---------------|-----------------|-----|----|
| D1 | India EOD Fetcher | EOD prices for all NSE stocks | NSE bhavcopy. Yahoo `.NS` fallback | Mon–Fri 16:30 (NSE trading days) | — | ✅ |
| D2 | MF NAV Fetcher | Daily NAV for all Indian MF schemes | AMFI `NAVAll.txt` | Daily 23:30 | — | ✅ |
| D3 | US EOD Fetcher | EOD prices for US stocks and ETFs | Yahoo Finance | Tue–Sat 07:00 (after NASDAQ close) | — | ✅ |
| D4 | FX Fetcher | USD/INR rate | Yahoo `INR=X`. RBI reference rate | Runs with D1 and D3 | — | ✅ |
| D5 | Fundamentals Fetcher | Financials and ratios for holdings and watchlist | Yahoo. NSE results. SEC EDGAR | Sat 08:00, and on results event | — | ✅ |
| D6 | Corporate Events Fetcher | Results dates, filings, dividends, splits | NSE announcements. SEC EDGAR | Daily 20:00 | — | ✅ |
| D7 | Macro Fetcher | Rates, inflation, Nifty P/E, US yields | RBI, NSE, FRED | Sat 08:00 | — | ✅ |
| D8 | Fund Data Fetcher | Expense ratio, category, AUM, holdings for look-through | AMC factsheets/disclosures. ETF issuer files | Monthly ~12th | — | ⚠️ partial |

#### Layer 1 — Watchers (code rules that raise events)

| ID | Agent | Work | Frequency | LLM | v1 |
|----|-------|------|-----------|-----|----|
| W1 | Watchlist Sentinel | Price in my buy zone, X% below 52-week high, unusual move on a holding | After D1/D2/D3 | — | ✅ |
| W2 | Drift Monitor | Asset-class / country / single-stock weight outside its band | After every price update, and on holding edit | — | ✅ |
| W3 | Cash Monitor | Deployable cash above threshold (INR or USD) | On cash edit, and daily | — | ✅ |
| W4 | Filing Triage | Tag new filings by materiality (ignore noise, escalate results, management change, pledging, etc.) | After D6 | S | ✅ |
| W5 | Data Health | Stale, missing or outlier prices. Blocks downstream agents if data is bad | After every fetch | — | ✅ |

#### Layer 2 — Research agents (write research notes)

| ID | Agent | Work | Trigger / frequency | LLM | v1 |
|----|-------|------|---------------------|-----|----|
| R1 | Fundamental Analyst | Per stock: business quality, valuation vs own history and peers, red flags, thesis, and why this beats the index | On watchlist add · after results · note older than 90 days · W1 price alert (thesis re-check) | L | ✅ |
| R2 | Fund Analyst | Per MF/ETF: rolling returns vs benchmark, expense ratio, tracking difference, manager change, style drift, overlap. Flags regular plans | Monthly after D8 · on add | L | ✅ |
| R3 | Macro Strategist | Per market (IN, US): rate cycle, market valuation, INR/USD trend. Outputs asset-class tilts only | Sat 10:00 · after RBI MPC / FOMC decisions | L | ✅ |

#### Layer 3 — Portfolio agents

| ID | Agent | Work | Trigger / frequency | LLM | v1 |
|----|-------|------|---------------------|-----|----|
| P1 | Portfolio Doctor | Health report: allocation, concentration, sector/country/currency exposure, overlap, performance vs benchmarks | Sun weekly pipeline · on holding edit | — + S | ✅ |
| P2 | Rebalancer | Trade plan when drift breaches its band. New cash first, then tax-aware sells (holding period, exit load) | W2 drift event · quarterly review | — + L | ✅ |
| P3 | Cash Deployer | Where idle cash should go: India vs US, lump sum vs staggered, where to park it meanwhile. Accounts for LRS friction (TCS, FX spread) when moving INR to the US | W3 cash event · Sun weekly | L | ✅ |
| P4 | LRS & Tax Ledger | Tracks remittances against the LRS limit and TCS threshold per financial year. Tracks holding periods, US-situs value (estate-tax exposure), and dividends with withholding. Sends year-end reminders (e.g. foreign-asset reporting) | On remittance or trade entry · monthly · financial-year end | — | ✅ light |

#### Layer 4 — Decision

| ID | Agent | Work | Trigger / frequency | LLM | v1 |
|----|-------|------|---------------------|-----|----|
| C1 | CIO | Reads notes, plans, IPS and portfolio. Writes the bear case for each idea, then publishes ranked suggestions (including NO_ACTION) | Sun weekly pipeline · urgent events (max once a day) | L | ✅ |
| C2 | Risk Guard | Checks every draft against hard rules. Approves, downgrades or vetoes. Rules run as code inside `create_suggestion` (D-019). A small model only writes the explanation | On every `create_suggestion` call | — + S | ✅ |

#### Layer 5 — Feedback, communication and system

| ID | Agent | Work | Trigger / frequency | LLM | v1 |
|----|-------|------|---------------------|-----|----|
| F1 | Scorekeeper | Marks every suggestion vs its benchmark at 1/3/6/12 months. Tracks hit rate per agent and alpha vs target (D-011) | Daily mark (code) · monthly report | — | ✅ |
| F2 | Briefing Agent | Weekly letter. Urgent alerts. Answers my questions from the DB | Sun after C2 · on demand | S/L | ✅ |
| S1 | Orchestrator | Schedules, event routing, catch-up after sleep, retries, dedupe, debounce, LLM budget cap | Always on | — | ✅ |
| S2 | Housekeeper | Expire old notes and suggestions. DB backup. Log rotation | Daily 03:00 (or on wake) | — | ✅ |

#### Later (not v1)

| Agent | Work | Frequency |
|-------|------|-----------|
| Tax Agent (full) | Realised/unrealised gains by bucket, harvesting plan, advance-tax estimate | Event · financial-year end |
| Technical Analyst | Entry timing and trend context for buys | Daily |
| Sentiment Analyst | Analyst ratings, promoter/insider activity, bulk/block deals | Daily |
| Screener / Idea Scout | Propose new watchlist candidates from screens | Weekly |
| External Tips Intake | Normalise outside tips into watchlist candidates (D-007) | On arrival |

### 3.4 Timeline (IST)

| When | What runs |
|------|-----------|
| Mon–Fri 16:30 | D1 India EOD + D4 FX → W5 → W1, W2 |
| Daily 20:00 | D6 corporate events → W4 triage → R1 if a holding or watchlist stock reported results |
| Daily 23:30 | D2 MF NAVs → W5 → W1, W2 |
| Tue–Sat 07:00 | D3 US EOD + D4 FX → W5 → W1, W2 |
| Daily 03:00 | S2 Housekeeper. F1 daily mark |
| Sat 08:00 | D5 fundamentals refresh. D7 macro |
| Sat 10:00 | R3 Macro Strategist (India and US) |
| **Sun 09:00 — weekly pipeline** (chained, each step starts when the previous one finishes) | P1 → P2 (if drift) and P3 (if cash) → C1 CIO → C2 Risk Guard → F2 weekly letter |
| ~12th monthly | D8 fund data → R2 Fund Analyst. F1 monthly report |
| Quarterly | Forced P2 rebalance review. Results season means more R1 runs |
| FY end (Feb–Mar) | P4 reminders: LRS/TCS totals, holding periods, harvesting window |

### 3.5 Events → who reacts

| Event | Raised by | Reaction | Urgency |
|-------|-----------|----------|---------|
| Watchlist item added | UI | D5 → R1 or R2 initial research | Normal |
| Holding / cash / remittance edited | UI | W2, W3, P4 → P1 | Normal |
| Price in buy zone | W1 | R1 thesis check → C1 | **Urgent** |
| Holding down ≥ 15% from cost or high | W1 | R1 thesis check → C1 | **Urgent** |
| Results or material filing | W4 | D5 → R1 updates note | Normal (urgent if thesis broken) |
| Drift outside band | W2 | P2 → C1 (weekly) | Normal |
| Deployable cash above threshold | W3 | P3 → C1 (weekly) | Normal |
| RBI MPC / FOMC decision | Calendar | R3 refresh | Normal |
| Stale or bad data | W5 | Pause C1. Show alert in UI | Blocking |

"Normal" waits for the Sunday pipeline. "Urgent" can trigger a mid-week C1 run, at most once a day (D-014).

### 3.6 Laptop reality (D-013)

| Concern | Design answer |
|---------|---------------|
| Lid closed / sleep | On wake, the Orchestrator compares last-success times with the schedule and runs missed jobs once (catch-up). EOD data a few hours late is harmless |
| Duplicate runs | Every job is idempotent, keyed by `(job, market_date)` |
| Reboot | Runs as an OS service with auto-start |
| Offline | Retry with backoff. W5 marks data stale. Nothing downstream runs on stale data |
| Free sources break or rate-limit | One adapter per source, fallback chain, caching, polite request rate. NSE needs browser-like headers. Bhavcopy files are more stable than NSE's JSON endpoints |
| Data loss | Daily SQLite backup (optionally to a cloud-synced folder) |
| LLM cost runaway | Weekly token budget in the Orchestrator. Research notes cached and reused until they expire |

### 3.7 Expected LLM load (rough)

Assuming ~20 watchlist/held stocks and ~10 funds/ETFs: roughly **10–20 large-model runs a week** (CIO, Macro ×2, Cash Deployer, Rebalancer, a few Fundamental re-checks), plus ~10 Fund Analyst runs a month and some small-model triage calls each day. Results season causes spikes.

### 3.8 Skills / tools

**Data:** `get_quote` · `get_ohlcv` · `get_fundamentals` · `get_fund_nav` · `get_fund_holdings` · `get_fx_rate` · `get_filings` · `get_news` · `get_macro_series`

**Calculations (pure code):** `valuation_vs_history` · `peer_compare` · `rolling_returns` · `xirr` · `allocation_drift` · `exposure_breakdown` (sector/country/currency, with MF look-through) · `overlap_matrix` · `tax_lot_impact` · `lrs_position` · `benchmark_compare` · `simulate_trades`

**Portfolio and state:** `get_holdings` · `get_cash` · `get_watchlist` · `get_policy` · `get_research_notes` · `write_research_note` · `raise_event`

**Output:** `create_suggestion` (CIO only) · `risk_check` · `notify_user`

### 3.9 Data model (minimal)

- `instruments`: symbol, exchange (NSE/BSE/NASDAQ/NYSE Arca…), type (stock/MF/ETF), currency, ISIN / AMFI scheme code, sector, domicile
- `holdings_lots`: instrument, buy date, qty/units, price, fees, currency (lots are needed for XIRR and tax)
- `cash_accounts`: name, currency, balance, **earmark** (emergency / deployable / reserved)
- `remittances`: date, INR amount, USD received, FX rate, TCS paid, financial year (for LRS)
- `watchlist`: instrument, *my reason for watching*, buy zone (optional), max allocation, status (`active` / `candidate`), added date
- `policy` (IPS): goals, horizon, risk tolerance, target allocation and drift bands, hard rules, benchmarks
- `tax_rules`: config table (rates, holding periods, thresholds), updated after each Budget, never hard-coded
- `market_data`: prices, NAVs, FX, fundamentals snapshots
- `events`: type, instrument, payload, urgency, processed flag
- `job_runs`: job, market_date, status, started/finished (for catch-up and idempotency)
- `research_notes`: agent, instrument/scope, thesis, evidence links, confidence, **expires_at**
- `suggestions`: see 3.11, with status and outcome tracking

### 3.10 Policy (IPS), benchmarks & Risk Guard rules

> No IPS yet. Values below are **proposed defaults** to fill in or change.

- **Return target:** stretch goal, beat Nifty 50 and S&P 500 by 5–10% a year (D-011). Working goal: beat the blended benchmark after costs and taxes over rolling 3 years.
- **Benchmarks (proposed):** India sleeve vs Nifty 50 TRI. US sleeve vs S&P 500 TR in USD (measures picking skill). Whole portfolio in INR vs a blend weighted by target allocation (measures what I actually get).
- Goals & horizon: _TBD_
- Max drawdown I can tolerate: _TBD_
- Target allocation: _TBD_ (India equity / US equity / debt / cash / gold)
- Drift band: ±5% absolute per asset class (proposed)

**Hard rules (Risk Guard), proposed:**
- Emergency-fund cash is never deployable
- Max single stock: 10% of portfolio. Max single sector: 30%
- No leverage, derivatives, shorting or margin
- Deployments above a threshold are staggered over several weeks unless I override
- No new buy in a stock within a few days before its results
- MF suggestions use direct plans only
- Every suggestion cites at least one unexpired research note, and every BUY/ADD states why it beats the index (D-015)
- Warn when US-situs holdings approach the US estate-tax exemption for non-US persons
- Warn before a remittance would cross the LRS limit or TCS threshold for the year

### 3.11 Suggestion format

```
type:         DEPLOY_CASH | BUY | ADD | TRIM | EXIT | SWITCH_FUND | REBALANCE | REMIT_USD | NO_ACTION
instrument(s), market, amount (INR/USD), staggering plan
why:          short rationale + links to research notes
vs_index:     why this beats the index-fund alternative
confidence:   low | medium | high
invalidation: what would make this wrong
horizon:      expected holding period
risk_check:   pass / downgraded (+ reason)
status:       proposed → accepted | rejected | snoozed | expired
outcome:      return vs benchmark at 1/3/6/12 months (Scorekeeper)
```

### 3.12 Data sources (decided: free only, D-012)

| Need | India | US |
|------|-------|----|
| EOD prices | NSE bhavcopy (primary), Yahoo `.NS` / `.BO` (fallback) | Yahoo Finance |
| MF NAV | AMFI `NAVAll.txt` (history via mfapi.in) | n/a |
| Fundamentals | Yahoo, NSE results filings | Yahoo, SEC EDGAR (XBRL) |
| Filings / results | NSE corporate announcements | SEC EDGAR |
| Fund holdings / factsheets | AMC monthly portfolio disclosures (formats vary by AMC) | ETF issuer holdings files |
| FX (INR/USD) | RBI reference rate, Yahoo `INR=X` | — |
| Macro | RBI, NSE (index P/E) | FRED |

Caveat: these are unofficial or scraped endpoints. Fine for low-volume personal use, but expect breakage. The adapter and fallback design (3.6) exists for this reason.

### 3.13 Implementation on Claude Code (D-016 to D-020)

#### Friday concepts → Claude Code features

| Friday concept | Claude Code feature | Where |
|----------------|---------------------|-------|
| Rules every agent follows (principles, no math in prompts, advisory only) | `CLAUDE.md` (short; this design doc stays separate) | `/CLAUDE.md` |
| LLM agents (R1–R3, P1–P3, C1, C2 explainer, W4, F2) | Subagents, with model, tool allowlist and memory per agent | `.claude/agents/*.md` |
| Workflows you can trigger (weekly review, research a ticker…) | Skills invoked as slash commands | `.claude/skills/<name>/SKILL.md` |
| Know-how agents need (valuation framework, fund checklist, tax/LRS rules, note and suggestion formats) | Background skills (`user-invocable: false`), preloaded into the subagents that need them via `skills:` | `.claude/skills/<name>/` |
| Tools (`get_holdings`, `xirr`, `allocation_drift`, `create_suggestion`…) | Local MCP server wrapping SQLite and the calculation code | `.mcp.json` → `friday/mcp_server.py` |
| Agent learnings ("last time I over-weighted X") | Subagent `memory: project` | `.claude/agent-memory/<agent>/` |
| Fetchers, watchers, LRS ledger, Scorekeeper, Housekeeper, Orchestrator | **Not Claude.** Plain Python (D-017) | `friday/` package |
| Unattended runs | `claude -p` (headless) started by the Orchestrator | — |
| Manual runs and "ask Friday" | Interactive `claude` in the project folder | — |

#### Subagents

| File (`.claude/agents/`) | Agent | Model | Key tools | Preloaded skills |
|--------------------------|-------|-------|-----------|------------------|
| `fundamental-analyst.md` | R1 | sonnet (opus for first deep dive) | Friday read tools, `write_research_note`, WebSearch, WebFetch | valuation-framework, note-format |
| `fund-analyst.md` | R2 | sonnet | Friday read tools, `write_research_note`, WebFetch | fund-checklist, note-format |
| `macro-strategist.md` | R3 | sonnet | Friday macro tools, `write_research_note`, WebSearch | note-format |
| `portfolio-doctor.md` | P1 | sonnet | Friday read and calc tools | policy |
| `rebalancer.md` | P2 | sonnet | Friday calc tools, `tax_lot_impact`, `simulate_trades` | policy, tax-india-lrs |
| `cash-deployer.md` | P3 | sonnet | Friday calc tools, `lrs_position`, `simulate_trades` | policy, tax-india-lrs |
| `cio.md` | C1 | opus | All Friday read tools, **`create_suggestion` (only this agent)** | policy, suggestion-format |
| `risk-explainer.md` | C2 (explanation only) | haiku | `get_policy`, read suggestion | policy |
| `filing-triage.md` | W4 | haiku | `get_filings`, `raise_event` | — |
| `briefing.md` | F2 | sonnet | Friday read tools | — |

Research agents get web access but no tool that creates suggestions. The CIO creates suggestions but reads only Friday's own data.

#### Workflow skills (slash commands)

| Skill | What it does | Subagents it runs (in order) | Triggered by |
|-------|--------------|------------------------------|--------------|
| `/weekly-review` | The Sunday pipeline | portfolio-doctor → rebalancer (if drift) and cash-deployer (if cash) → cio → briefing | Tick, Sun 09:00 · manual |
| `/research <symbol>` | Create or refresh the research note for one instrument | fundamental-analyst or fund-analyst | Watchlist add · results event · note expiry · manual |
| `/deploy-cash [amount]` | Where should this cash go? | cash-deployer → cio | Cash event · manual |
| `/rebalance-check` | Is a rebalance needed, and how? | portfolio-doctor → rebalancer → cio | Drift event · quarterly · manual |
| `/macro-update` | Refresh India and US macro views | macro-strategist | Tick, Sat 10:00 · after RBI/FOMC · manual |
| `/fund-review` | Monthly review of all held and watched funds/ETFs | fund-analyst (per fund) | Tick, ~12th monthly · manual |
| `/triage-filings` | Tag today's filings, escalate material ones | filing-triage | Tick, daily 20:00 |
| `/urgent-review` | Mid-week CIO run for urgent events only | fundamental-analyst (thesis check) → cio | Urgent event, max once a day (D-014) |

#### Scheduling options considered

| Option | Verdict | Why |
|--------|---------|-----|
| **OS scheduler → `friday tick` → `claude -p`** | ✅ Chosen (D-018) | No app needs to stay open. Survives reboot. The tick does its own catch-up via `job_runs`, so missed runs are handled the same on any OS. Also runs the non-Claude Python jobs |
| Claude Desktop local scheduled tasks | Good fallback for the LLM jobs | Local files, per-task permissions, one catch-up run on wake. But the Desktop app must be open, it can't run the Python jobs, and the schedule lives outside the repo |
| `/loop` or in-session cron | ❌ | Only fires while a session is open. Recurring tasks expire after 7 days. No catch-up |
| Cloud scheduled tasks | ❌ for now | Runs on a fresh cloud clone, so it can't see the local SQLite database |

#### What the tick runs

| Job | Command | Claude? |
|-----|---------|---------|
| Price, NAV, FX, fundamentals, events, macro, fund data | `python -m friday.fetch <source>` | No |
| Watchers W1–W3, W5 | `python -m friday.watch` (after each fetch) | No |
| Filing triage | `claude -p "/triage-filings"` | Yes (haiku) |
| Research on events | `claude -p "/research <symbol>"` | Yes |
| Macro, weekly, monthly, urgent | `claude -p "/macro-update"` etc. | Yes |
| Scorekeeper, LRS ledger, Housekeeper | `python -m friday.score` etc. | No |

Example unattended call:

```bash
claude -p "/weekly-review" \
  --permission-mode dontAsk \
  --allowedTools "mcp__friday__*,WebSearch,WebFetch,Read" \
  --output-format json \
  --max-budget-usd 3 \
  > logs/weekly-review-$(date +%F).json
```

Notes:
- Don't use `--bare` for these runs. Bare mode skips the project's `CLAUDE.md`, subagents, skills and `.mcp.json`, and requires an API key.
- The tick runs one Claude job at a time (a lock), so jobs never overlap and SQLite has a single writer.
- The exit code and JSON output are logged to `job_runs`. A failed job is retried on the next tick, with backoff.

#### Project layout (target)

```
friday/
├── agents.md                 # this design doc (memory for brainstorming)
├── CLAUDE.md                 # short rules loaded in every Claude session
├── .mcp.json                 # registers the local "friday" MCP server
├── .claude/
│   ├── settings.json         # permission allowlist, hooks
│   ├── agents/               # subagents (table above)
│   ├── skills/
│   │   ├── weekly-review/  research/  deploy-cash/  rebalance-check/
│   │   ├── macro-update/  fund-review/  triage-filings/  urgent-review/
│   │   └── policy/  valuation-framework/  fund-checklist/
│   │       tax-india-lrs/  note-format/  suggestion-format/   # background know-how
│   └── agent-memory/         # per-agent learnings
├── friday/                   # Python package
│   ├── mcp_server.py         # tools for Claude, enforces hard rules
│   ├── db.py                 # SQLite schema and access
│   ├── fetchers/             # nse, amfi, yahoo, edgar, fred, fx
│   ├── calc/                 # xirr, drift, valuation, overlap, tax, lrs
│   ├── watchers/             # W1–W3, W5
│   ├── risk_rules.py         # hard rules (D-019)
│   ├── scorekeeper.py
│   └── orchestrator.py       # `friday tick`
├── web/                      # UI (reads and writes SQLite through the backend)
├── data/friday.db            # git-ignored
└── logs/                     # git-ignored
```

---

## 4. Roadmap / parking lot

- **v2 candidates:** Tax Agent (full) · Screener/Idea Scout · External Tips Intake (D-007) · CAS / broker CSV import · Technical & Sentiment agents · notifications (email/Telegram)
- **Later:** broker read-only sync · backtesting the CIO on historical data · "what-if" simulator in the UI · goal-based planning (retirement, house, etc.)
- **Idea to evaluate:** Ireland-domiciled (UCITS) ETFs as an alternative to US-domiciled ETFs. They reduce US estate-tax exposure and dividend withholding for Indian residents, but they trade on LSE, not NASDAQ.
- **Ideas inbox rule (for screener/tips):** an idea goes to the watchlist as `candidate` → R1/R2 research → only then is it eligible for the CIO. No shortcuts.

---

## 5. Open questions

1. **Claude billing:** run the scheduled jobs on my Claude subscription login (shares usage limits with my interactive use) or on an API key (pay per use, separate budget)?2. **IPS values:** goals, horizon, max drawdown, target allocation India vs US vs debt vs gold (section 3.10)
3. **Tax rules config:** capital-gains rates, holding periods and LRS/TCS thresholds change with budgets. Who updates the `tax_rules` table, and how?
4. **Tech stack:** backend language, scheduler, agent framework, frontend. Not decided.
5. **Notification channel** for urgent items: in-app only for v1, or also desktop notifications?
6. **Where the screener/tips come from** when we build them: own screens, a newsletter, another agent?
7. **Existing US holdings:** which broker and platform? Affects how I enter lots and FX rates historically.
8. **Laptop OS:** macOS, Windows or Linux? Decides which OS scheduler runs `friday tick`.

### Resolved
- ~~Tax residency~~ → D-010 · ~~Data budget~~ → D-012 · ~~Hosting~~ → D-013 · ~~Benchmarks / target~~ → D-011 (IPS details still open) · ~~Which LLM~~ → D-016 · ~~Agent framework~~ → D-016 (Claude Code)

---

## 6. Changelog

| Version | Date | Change |
|---------|------|--------|
| v1 | 2026-10-24 | Initial architecture from first brainstorm. Decisions D-001 to D-009. v1 agent roster, schedules, data model, suggestion format |
| v1.1 | 2026-10-24 | Decisions D-010 to D-015 (LRS resident, return target, free data, laptop-local, urgency policy, index baseline). Full system design: runtime components, 22-component roster by layer, IST timeline, event table, laptop resilience, LLM load estimate. Added LRS & Tax Ledger (P4), Data Health (W5), Orchestrator and Housekeeper. Data sources decided |
| v1.2 | 2026-10-24 | Decisions D-016 to D-020: Friday as a Claude Code project (subagents, skills, local MCP server), Python for non-LLM work, `friday tick` + `claude -p` scheduling, hard rules in code, locked-down unattended permissions. Added section 3.13 |
| v1.2 (docs) | 2026-10-24 | Added `docs/architecture.md`: plain-language overview of the v1.2 architecture and user journeys J1–J10. No design change |

---

## How to use this file

- **Start of a session:** read sections 2, 3 and 5.
- **New decision:** add a row to the Decision log with the next `D-###`. To reverse a decision, mark the old row `Superseded by D-###`. Don't delete it.
- **Plan changes:** small edits go into the current version with a Changelog line. A significant redesign bumps the version: move the old plan to `docs/plans/vN.md` and start the new "Current plan" here.
- **Unresolved items** go to Open questions. **Good ideas that are out of scope** go to the Roadmap / parking lot.
- If this file gets too big, split it into `docs/architecture/*.md` and keep this file as the index.
