# Friday — Agent Architecture & Plan

> Living design doc for **Friday**, a personal stock analyst / portfolio manager.
> This file is the memory for brainstorming sessions: decisions, the current plan, open questions and ideas for later.
> Update it every session. Never delete history. Supersede it (see [How to use this file](#how-to-use-this-file)).

**Current plan:** v1 · **Last updated:** 2026-10-24

---

## 1. What Friday is

A simple web app plus a team of background agents that:

1. **Tracks** my cash (INR and USD) and my portfolio (Indian stocks and mutual funds, US stocks and ETFs).
2. **Researches** a manually curated watchlist and the wider market.
3. **Suggests** what to do in a Suggestions tab: where to put idle cash, when to rebalance, what to add, trim or switch, with reasons.

Friday **advises**. I **execute** trades myself at my broker.

### Principles

- **Code computes, LLMs judge.** Prices, returns, XIRR, drift, ratios, indicators and tax impact are deterministic code exposed as tools. LLMs interpret, weigh evidence and explain. No arithmetic inside prompts.
- **Watch cheaply, think expensively only when needed.** "24/7 agents" are schedulers and code-based watchers. An LLM only wakes up on a meaningful trigger.
- **One voice to the user.** Only the CIO agent creates suggestions. Every other agent writes research notes.
- **Every suggestion is falsifiable.** Each one states what to do, how much, why, how confident it is, and what would prove it wrong. Then it gets scored.
- **Policy over prediction.** Every suggestion is judged against my written Investment Policy Statement (IPS), not against "maximum returns".
- **Low noise.** Long-term investing means few, high-quality suggestions. Silence is a valid output.

---

## 2. Decision log

| ID | Date | Decision | Rationale | Status |
|----|------|----------|-----------|--------|
| D-001 | 2026-10-24 | Markets: **India** (NSE/BSE stocks, Indian mutual funds) and **US** (NASDAQ-listed stocks, US ETFs) | Where I invest | Active |
| D-002 | 2026-10-24 | **Watchlist is curated manually** by me | I want control over the universe | Active |
| D-003 | 2026-10-24 | Holdings and cash are entered **manually** (no broker sync in v1) | Simplest. Broker/CAS import comes later | Active |
| D-004 | 2026-10-24 | Investment style: **long-term** (buy, hold, rebalance). No intraday or swing trading | Matches my goals. Lets agents run on low cadence | Active |
| D-005 | 2026-10-24 | **Single user** (me). No multi-tenancy | Keeps auth and data model simple. Personal use avoids the advisory-registration question | Active |
| D-006 | 2026-10-24 | **Advisory only.** Friday never places orders | Safety. I stay in the loop | Active |
| D-007 | 2026-10-24 | Screener agent and external tip sources are **future**, not v1. When added, they feed the *same* pipeline (they propose ideas and never create suggestions directly) | Keeps one research path and one quality bar | Planned |
| D-008 | 2026-10-24 | Deterministic tools for all numbers. LLMs for judgment and narrative | Reproducibility, cost, correctness | Active |
| D-009 | 2026-10-24 | Base reporting currency **INR**. USD positions are shown in both currencies | I think in INR. USD exposure is a currency bet in its own right | Proposed (confirm) |

---

## 3. Current plan — v1

### 3.1 Scope

**In v1**
- Manual entry of holdings (as tax lots), cash accounts and the watchlist
- Portfolio view: allocation, P&L, XIRR, drift vs target (INR and USD)
- Suggestions tab: ranked suggestions with accept, reject and snooze, plus history
- Background agents (see roster): portfolio health, rebalancing, cash deployment, fund analysis, fundamental research on watchlist stocks, light macro view, CIO, Risk Guard, Scorekeeper, weekly brief

**Not in v1** (see [Roadmap](#4-roadmap--parking-lot))
- Broker or CAS sync, auto-trading, screener or idea discovery, external tips, technical and sentiment agents, intraday alerts, multi-user

### 3.2 Architecture

```
 Triggers: schedules (per market) · events (cash added, holding edited,
           watchlist add, drift breach, earnings/filing) · on-demand ask
        │
  ┌─────▼────────────┐  code only, cheap, frequent
  │ Data & Watchers  │─► prices, NAVs, FX, fundamentals, filings, macro
  └─────┬────────────┘   raise an EVENT only when something is material
        │
  ┌─────▼────────────┐  LLM, on trigger
  │ Research agents  │─► write RESEARCH NOTES (thesis, evidence, confidence, expiry)
  └─────┬────────────┘
  ┌─────▼────────────┐
  │ Portfolio agents │─► drift, rebalance plans, cash deployment plans
  └─────┬────────────┘
  ┌─────▼────────────┐
  │      CIO         │─► reads notes + portfolio + IPS → draft SUGGESTIONS
  └─────┬────────────┘
  ┌─────▼────────────┐
  │   Risk Guard     │─► hard-rule check: approve / downgrade / veto
  └─────┬────────────┘
        ▼
  Suggestions tab ──► my decision ──► Scorekeeper (tracks outcome vs benchmark)
```

Shared state lives in one database. Agents talk *through the store* (notes, events, suggestions), not to each other directly.

### 3.3 Agent roster

Model tier: **S** = small/fast model (triage, tagging), **L** = large model (deep reasoning), **—** = no LLM.

| # | Agent | Job | Trigger | Tier | v1? |
|---|-------|-----|---------|------|-----|
| 1 | **Data Refresher** | Pull EOD prices, NAVs, FX, and fundamentals for holdings and watchlist | Schedules (see 3.4) | — | ✅ |
| 2 | **Watchlist Sentinel** | Flag big moves, 52-week lows/highs, or prices entering my buy zone | After each data refresh | — | ✅ |
| 3 | **Filings & Earnings Scout** | Detect results, corporate actions and material filings for holdings and watchlist. Tag materiality | Daily | S | ✅ |
| 4 | **Fundamental Analyst** | Business quality, valuation vs own history and peers, balance-sheet red flags. Writes and refreshes the thesis note per stock | On watchlist add, after results, when a note expires | L | ✅ |
| 5 | **Fund Analyst** | MFs and ETFs: rolling returns vs benchmark, expense ratio, tracking difference, manager change, style drift, AUM, overlap with my other holdings. Flags regular plans (prefer direct) | Monthly (after factsheets), on add | L | ✅ |
| 6 | **Macro Strategist** | Light regime view per market (rates cycle, valuation of the market as a whole, INR/USD trend). Outputs asset-class tilts, not stock picks | Weekly, and after major macro events | L | ✅ |
| 7 | **Portfolio Doctor** | Allocation vs target, concentration, sector/country/currency exposure, MF look-through overlap (e.g. Indian funds holding US stocks) | Weekly, and on holding change | — + S | ✅ |
| 8 | **Rebalancer** | When drift breaches its band, propose trades. Use new cash first, then tax-aware sells (holding period, exit load, harvesting losses) | Drift breach, quarterly | — + L | ✅ |
| 9 | **Cash Deployer** | Deployable cash over threshold → where it should go and how: lump sum vs staggered, parking vehicle meanwhile (liquid fund / T-bill ETF) | Cash added, weekly | L | ✅ |
| 10 | **CIO** | Combine notes, plans, IPS and portfolio into ranked suggestions. Writes its own bear case before finalising (the "devil's advocate" step, built in) | Weekly, plus urgent events | L | ✅ |
| 11 | **Risk Guard** | Enforce hard rules (3.7). Can veto or downgrade | Every draft suggestion | — + S | ✅ |
| 12 | **Scorekeeper** | Mark each suggestion at 1, 3, 6 and 12 months vs benchmark. Hit rate per agent and per suggestion type | Monthly | — | ✅ |
| 13 | **Briefing Agent** | Weekly letter: portfolio status, what changed, open suggestions. Answers on-demand questions from the store | Weekly, on demand | S/L | ✅ |
| 14 | Tax Agent | Full tax view: realised/unrealised gains by bucket, year-end harvesting. (v1 has only the tax-aware tool used by the Rebalancer) | Event, year-end | L | later |
| 15 | Technical Analyst | Entry timing, trend context | Daily | S | later |
| 16 | Sentiment Analyst | Analyst ratings, promoter/insider activity, bulk deals | Daily | S | later |
| 17 | Screener / Idea Scout | Propose *new* watchlist candidates from screens | Weekly | — + L | later |
| 18 | External Tips Intake | Ingest tips from external sources/agents → normalise → send to research like any other idea | On arrival | S | later |

### 3.4 Schedules (all times IST)

| When | What |
|------|------|
| ~16:30 Mon–Fri | India EOD prices → Sentinel |
| ~23:30 Mon–Fri | Indian MF NAVs (AMFI publishes in the evening) → Sentinel |
| ~07:00 Tue–Sat | US EOD prices (after NASDAQ close) + FX → Sentinel |
| Daily | Filings & Earnings Scout |
| Sunday | Portfolio Doctor → Rebalancer/Cash Deployer → Macro → CIO → Risk Guard → Weekly brief |
| ~10th of month | Fund Analyst (factsheets out) · Scorekeeper |
| Quarterly | Forced rebalance review |

Both exchange holiday calendars (NSE and US) must be respected. US close shifts by an hour with US daylight saving.

### 3.5 Skills / tools

**Data:** `get_quote` · `get_ohlcv` · `get_fundamentals` · `get_fund_nav` · `get_fund_holdings` · `get_fx_rate` · `get_filings` · `get_news` · `get_macro_series`

**Calculations (pure code):** `valuation_vs_history` · `peer_compare` · `rolling_returns` · `xirr` · `allocation_drift` · `exposure_breakdown` (sector/country/currency, with MF look-through) · `overlap_matrix` · `tax_lot_impact` · `simulate_trades`

**Portfolio and state:** `get_holdings` · `get_cash` · `get_watchlist` · `get_policy` · `get_research_notes` · `write_research_note` · `raise_event`

**Output:** `create_suggestion` (CIO only) · `risk_check` · `notify_user`

### 3.6 Data model (minimal)

- `instruments`: symbol, exchange (NSE/BSE/NASDAQ/NYSE Arca…), type (stock/MF/ETF), currency, ISIN / AMFI scheme code, sector
- `holdings_lots`: instrument, buy date, qty/units, price, fees, currency (lots are needed for XIRR and tax)
- `cash_accounts`: name, currency, balance, **earmark** (emergency / deployable / reserved)
- `watchlist`: instrument, *my reason for watching*, buy zone (optional), max allocation, added date
- `policy` (IPS): goals, horizon, risk tolerance, target allocation and drift bands, hard rules, benchmarks
- `market_data`: prices, NAVs, FX, fundamentals snapshots
- `events`: type, instrument, payload, materiality, processed flag
- `research_notes`: agent, instrument/scope, thesis, evidence links, confidence, **expires_at**
- `suggestions`: see 3.8, with status and outcome tracking

### 3.7 Policy (IPS) & Risk Guard rules

> To be filled in by me. The values below are **proposed defaults** for discussion.

- Goals & horizon: _TBD_
- Target allocation: _TBD_ (e.g. India equity / US equity / debt / cash / gold)
- Drift band: ±5% absolute per asset class (proposed)
- Benchmarks: Nifty 50 (or Nifty 500) for India equity, NASDAQ-100 / S&P 500 for US, a blended benchmark for the whole portfolio (proposed)

**Hard rules (Risk Guard), proposed:**
- Emergency-fund cash is never deployable
- Max single stock: 10% of portfolio. Max single sector: 30%. Max single fund house: _TBD_
- No leverage, derivatives, shorting or margin
- Deployments above a threshold are staggered over several weeks unless I override
- No new buy in a stock within a few days before its results
- MF suggestions use direct plans only
- Every suggestion must cite at least one unexpired research note

### 3.8 Suggestion format

```
type:         DEPLOY_CASH | BUY | ADD | TRIM | EXIT | SWITCH_FUND | REBALANCE | NO_ACTION
instrument(s), market, amount (INR/USD), staggering plan
why:          short rationale + links to research notes
confidence:   low | medium | high
invalidation: what would make this wrong
horizon:      expected holding period
risk_check:   pass / downgraded (+ reason)
status:       proposed → accepted | rejected | snoozed | expired
outcome:      return vs benchmark at 1/3/6/12 months (Scorekeeper)
```

### 3.9 Data source candidates (not decided)

| Need | India | US |
|------|-------|----|
| EOD prices | Broker API (e.g. Kite Connect), Yahoo-style `.NS`/`.BO` feeds | Polygon, Finnhub, FMP, Alpha Vantage |
| MF NAV | AMFI daily NAV file, mfapi.in | n/a |
| Fundamentals | _TBD_ (no great free API; may need a paid source) | FMP, Finnhub, SEC EDGAR |
| Filings / results | NSE/BSE corporate announcements | SEC EDGAR |
| Fund holdings / factsheets | AMC monthly portfolio disclosures | ETF issuer holdings files |
| FX (INR/USD) | RBI reference rate | Any FX API |
| Macro | RBI, MOSPI | FRED |

---

## 4. Roadmap / parking lot

- **v2 candidates:** Tax Agent · Screener/Idea Scout · External Tips Intake (D-007) · CAS / broker CSV import · Technical & Sentiment agents · notifications (email/Telegram)
- **Later:** broker read-only sync · backtesting the CIO on historical data · "what-if" simulator in the UI · goal-based planning (retirement, house, etc.)
- **Ideas inbox rule (for screener/tips):** an idea goes to the watchlist as `candidate` → Fundamental/Fund Analyst research → only then is it eligible for the CIO. No shortcuts.

---

## 5. Open questions

1. **Tax residency:** am I an Indian resident investing in the US via LRS? That affects tax treatment of US holdings, dividend withholding, foreign-asset reporting, and US estate-tax exposure for non-US persons. These would become Risk Guard and Briefing items.
2. **Tax rules as config:** capital-gains rates and holding periods change with budgets. Keep them in a config table, not in code or prompts. Who updates them, and how?
3. **Target allocation and IPS values** (section 3.7)
4. **Tech stack:** backend, database, scheduler, agent framework, frontend. Not decided.
5. **Hosting:** where do the schedulers run (always-on VPS vs serverless cron)?
6. **Data budget:** free sources only, or willing to pay for fundamentals?
7. **Notification channel** for urgent items (in-app only for v1?)
8. **Where the screener/tips come from** when we build them: own screens, a newsletter, another agent?

---

## 6. Changelog

| Version | Date | Change |
|---------|------|--------|
| v1 | 2026-10-24 | Initial architecture from first brainstorm. Decisions D-001 to D-009. v1 agent roster, schedules, data model, suggestion format |

---

## How to use this file

- **Start of a session:** read sections 2, 3 and 5.
- **New decision:** add a row to the Decision log with the next `D-###`. To reverse a decision, mark the old row `Superseded by D-###`. Don't delete it.
- **Plan changes:** small edits go into the current version with a Changelog line. A significant redesign bumps the version: move the old plan to `docs/plans/vN.md` and start the new "Current plan" here.
- **Unresolved items** go to Open questions. **Good ideas that are out of scope** go to the Roadmap / parking lot.
- If this file gets too big, split it into `docs/architecture/*.md` and keep this file as the index.
