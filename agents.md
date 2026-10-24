# Friday — Agent Architecture & Plan

> Living design doc for **Friday**, a personal stock analyst / portfolio manager.
> This file is the memory for brainstorming sessions: decisions, the current plan, open questions and ideas for later.
> Update it every session. Never delete history. Supersede it (see [How to use this file](#how-to-use-this-file)).

**Current plan:** v1.3 · **Last updated:** 2026-10-24

---

## 1. What Friday is

A simple web app plus a team of agents that:

1. **Tracks** my cash (INR and USD) and my portfolio (Indian stocks and mutual funds, US stocks and ETFs).
2. **Researches** a manually curated watchlist and the wider market.
3. **Suggests** what to do in a Suggestions tab: where to put idle cash, when to rebalance, what to add, trim or switch, with reasons.

Friday **advises**. I **execute** trades myself at my broker.

In v1, Friday runs the non-LLM work (data, calculations, watching) automatically, 24/7 on my laptop. When LLM thinking is needed, Friday **asks me**: it notifies me, I run Claude Code, and I paste the structured result back into the UI (D-021).

### Principles

- **Code computes, LLMs judge.** Prices, returns, XIRR, drift, ratios, indicators and tax impact are deterministic code. LLMs interpret, weigh evidence and explain. No arithmetic inside prompts.
- **Watch automatically, think on request.** Code watches 24/7. LLM work is batched and run by me, about once a week.
- **One voice to the user.** Only the CIO agent writes suggestions. Every other agent writes research notes.
- **Every suggestion is falsifiable.** Each one states what to do, how much, why, how confident it is, and what would prove it wrong. Then it gets scored.
- **Beat the index or buy the index.** Every stock or active-fund idea must argue why it beats simply buying the index fund. If it can't, the suggestion is the index fund.
- **Policy over prediction.** Every suggestion is judged against my written Investment Policy Statement (IPS).
- **Low noise.** Long-term investing means few, high-quality suggestions. Silence is a valid output.
- **Laptop-first.** The system must survive sleep, reboot and going offline without losing or duplicating work.
- **Claude reads, Friday writes.** Claude never touches the database. It reads a context pack and returns JSON. Friday validates and stores it.

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
| D-008 | 2026-10-24 | Deterministic code for all numbers. LLMs for judgment and narrative | Reproducibility, cost, correctness | Active |
| D-009 | 2026-10-24 | Base reporting currency **INR**. USD positions are shown in both currencies | I think in INR | Proposed (confirm) |
| D-010 | 2026-10-24 | **Indian tax resident.** US investing via **LRS**. Existing US holdings and USD cash may already be there | Drives tax, TCS, remittance limits and estate-tax checks | Active |
| D-011 | 2026-10-24 | Return target: **beat Nifty 50 and S&P 500 by 5–10% a year**. Recorded as a *stretch* goal. The working target is to beat a blended benchmark after costs and taxes, measured by the Scorekeeper | 5–10% sustained outperformance is rare even for professionals. A measurable target keeps Friday honest | Active (stretch) |
| D-012 | 2026-10-24 | **Free data only:** NSE (bhavcopy, announcements), AMFI, Yahoo Finance, SEC EDGAR, FRED | No paid subscriptions | Active |
| D-013 | 2026-10-24 | **Runs locally on my laptop, 24/7.** One process plus SQLite. Must tolerate sleep, reboot and offline | Simple, private, free hosting | Active |
| D-014 | 2026-10-24 | Most events wait for the **weekly session**. Only *urgent* events get an immediate ping | Long-term style. Avoids noise | Proposed |
| D-015 | 2026-10-24 | Every BUY/ADD must justify itself against the **index-fund alternative** | Keeps the alpha target honest | Proposed |
| D-016 | 2026-10-24 | **LLM = Claude, run through Claude Code.** Agents are subagents, workflows are skills, all in this repo | No custom agent framework to build | Active |
| D-017 | 2026-10-24 | **Plain Python for everything that doesn't need judgment** (fetchers, watchers, LRS ledger, Scorekeeper, Housekeeper) | Doesn't spend Claude usage on downloads and arithmetic | Active |
| D-018 | 2026-10-24 | Scheduling: one OS scheduler entry runs `friday tick` every 15 min, which decides what's due. ~~It also starts `claude -p` for LLM jobs~~ | OS-agnostic, handles catch-up and dedupe itself | Active for Python jobs. LLM part superseded by D-021 |
| D-019 | 2026-10-24 | ~~Hard rules enforced inside an MCP server's `create_suggestion` tool~~ | — | Superseded by D-024 |
| D-020 | 2026-10-24 | ~~Unattended runs use `--permission-mode dontAsk` with an allowlist~~ | — | Superseded by D-021 (no unattended runs in v1). Revisit with automation (v2) |
| D-021 | 2026-10-24 | **Manual LLM step in v1.** Friday never calls Claude itself. When LLM work is due, it creates a task and notifies me. I run it in Claude Code and paste the structured output into the UI | Removes headless runs, permission lockdown, billing questions and the MCP server from v1. I review every LLM run. Fits advisory-only | Active |
| D-022 | 2026-10-24 | **Batch all pending LLM tasks into one command, `/friday-run`, in one session.** Target: ~1 session a week plus rare urgent pings | Keeps the manual step cheap. One paste instead of many | Active |
| D-023 | 2026-10-24 | **Context packs for the hand-off.** Friday exports a read-only JSON pack (portfolio, precomputed numbers, notes, pending tasks). Claude reads it and never touches the DB. MCP server deferred to v2 | Simplest possible interface. Claude can't corrupt state | Active |
| D-024 | 2026-10-24 | **Versioned output schema + importer.** The pasted JSON is validated against a schema, de-duplicated by task ID, and checked against Risk Guard hard rules **on import** (code, not LLM) | A rule can't be argued past. A bad paste can't corrupt data | Active |
| D-025 | 2026-10-24 | **No daily LLM work.** Filing triage becomes code rules (announcement category + keywords). Macro view moves into the weekly session | A daily manual step would be a chore | Active |
| D-026 | 2026-10-24 | **Notifications:** in-app badge and desktop notification in v1. Email (Gmail SMTP with an app password, free) optional. Telegram later | Free, local, enough for ~1 ping a week | Proposed |

---

## 3. Current plan — v1.3

### 3.1 Scope

**In v1**
- Manual entry of holdings (as tax lots), cash accounts, LRS remittances and the watchlist
- Portfolio view: allocation, P&L, XIRR, drift vs target, benchmark comparison (INR and USD)
- Automatic data refresh and watching (Python, 24/7)
- **LLM task inbox:** pending tasks, notifications, copy-command button, paste box with validation
- Suggestions tab: ranked suggestions with accept, reject and snooze, plus history and scoring

**Not in v1** (see [Roadmap](#4-roadmap--parking-lot))
- Automatic Claude runs (headless) and the MCP server, broker or CAS sync, auto-trading, screener or idea discovery, external tips, technical and sentiment agents, full tax agent, multi-user

### 3.2 The manual loop

```
 Friday (Python, 24/7)                         Me                         Claude Code
 ─────────────────────                        ────                       ───────────
 fetch → calculate → watch
        │
        ▼
 create LLM task(s) ──► notify ─────────────► open Friday UI
 export context pack                         copy "/friday-run" ───────► claude (in repo)
                                                                         /friday-run
                                                                         reads exchange/ pack
                                                                         runs subagents
                                             copy JSON output ◄───────── prints JSON
 importer: validate schema,  ◄── paste ────── paste into UI
 dedupe, Risk Guard rules
        │
        ▼
 notes + suggestions saved → Suggestions tab → accept / reject → Scorekeeper
```

### 3.3 Runtime components (one laptop)

| Component | Role | Notes |
|-----------|------|-------|
| **Web UI** | Portfolio, cash, watchlist, **task inbox + paste box**, suggestions, weekly letter | Served on `localhost` |
| **Backend** | CRUD for my data. Serves the UI. Runs the importer | Same process as the tick |
| **SQLite DB** | All state: holdings, prices, notes, tasks, suggestions | One file, backed up daily |
| **Orchestrator** (`friday tick`) | Runs due Python jobs, creates LLM tasks, sends notifications, catch-up after sleep | Run by the OS scheduler every 15 min |
| **Data adapters** | One per free source, with fallback and caching | NSE → Yahoo fallback for India |
| **Context pack exporter** | Writes `exchange/pending.json` and `exchange/context/<snapshot>.json` | Read-only for Claude |
| **Importer** | Validates pasted JSON, dedupes, applies Risk Guard rules, stores results | The only write path for LLM output |
| **Notifier** | In-app badge, desktop notification, optional email | D-026 |
| **Claude Code project** | `CLAUDE.md`, subagents, skills in `.claude/` | Run by me, interactively |

### 3.4 Agent roster

LLM column: **—** = code only, **haiku / sonnet / opus** = Claude subagent model (run in my manual session).

#### Code (automatic, 24/7)

| ID | Component | Work | Frequency (IST) |
|----|-----------|------|-----------------|
| D1 | India EOD Fetcher | NSE bhavcopy (Yahoo `.NS` fallback) | Mon–Fri 16:30 |
| D2 | MF NAV Fetcher | AMFI `NAVAll.txt` | Daily 23:30 |
| D3 | US EOD Fetcher | Yahoo Finance | Tue–Sat 07:00 |
| D4 | FX Fetcher | USD/INR (Yahoo `INR=X`, RBI reference rate) | With D1 and D3 |
| D5 | Fundamentals Fetcher | Yahoo, NSE results, SEC EDGAR | Sat 08:00, and on results |
| D6 | Corporate Events Fetcher | NSE announcements, SEC EDGAR | Daily 20:00 |
| D7 | Macro Fetcher | RBI, NSE (index P/E), FRED | Sat 08:00 |
| D8 | Fund Data Fetcher | AMC disclosures, ETF issuer files (partial in v1) | Monthly ~12th |
| W1 | Watchlist Sentinel | Buy zone hit, X% below 52-week high, big move on a holding | After each price fetch |
| W2 | Drift Monitor | Weights outside their bands | After each price fetch, on holding edit |
| W3 | Cash Monitor | Deployable cash above threshold | On cash edit, daily |
| W4 | Filing Rules | Tag announcements by category/keywords (results, rating change, management change, pledging…). **Code, not LLM** (D-025) | After D6 |
| W5 | Data Health | Stale, missing or outlier data. Blocks context-pack export if bad | After every fetch |
| P4 | LRS & Tax Ledger | LRS limit and TCS threshold per financial year, holding periods, US-situs value, dividends with withholding, year-end reminders | On entry, monthly, FY end |
| C2 | Risk Guard | Hard rules checked **on import** (D-024). Approve, downgrade or reject each suggestion with a reason | On every paste |
| F1 | Scorekeeper | Grades suggestions vs benchmark at 1/3/6/12 months. Tracks alpha vs target | Daily mark, monthly report |
| S1 | Orchestrator | Schedules, task creation, notifications, catch-up | Every 15 min |
| S2 | Housekeeper | Expire notes, tasks and suggestions. DB backup | Daily 03:00 or on wake |

#### Claude subagents (run by me via `/friday-run`)

| ID | Subagent | Work | When it's needed | Model |
|----|----------|------|------------------|-------|
| R1 | fundamental-analyst | Per stock: quality, valuation vs history and peers, red flags, thesis, why it beats the index | Watchlist add · results · note older than 90 days · price alert | sonnet (opus for first deep dive) |
| R2 | fund-analyst | Per MF/ETF: rolling returns, costs, tracking, manager change, style drift, overlap. Flags regular plans | Monthly · on add | sonnet |
| R3 | macro-strategist | India and US regime view, asset-class tilts | Weekly session · after RBI/FOMC | sonnet |
| P1 | portfolio-doctor | Health narrative on top of precomputed numbers | Weekly session | sonnet |
| P2 | rebalancer | Trade plan when drift breaches band (new cash first, tax-aware) | Drift task · quarterly | sonnet |
| P3 | cash-deployer | Where idle cash goes, India vs US, lump sum vs staggered, LRS friction | Cash task · weekly | sonnet |
| C1 | cio | Bear case for each idea, then ranked suggestions (incl. NO_ACTION) | End of every `/friday-run` that has new inputs | opus |
| F2 | briefing | Weekly letter | Weekly session | sonnet |

#### Later (not v1)

| Agent | Work |
|-------|------|
| Tax Agent (full) | Gains by bucket, harvesting plan, advance-tax estimate |
| Technical Analyst | Entry timing and trend context |
| Sentiment Analyst | Analyst ratings, promoter/insider activity, bulk/block deals |
| Screener / Idea Scout | Propose new watchlist candidates |
| External Tips Intake | Normalise outside tips into watchlist candidates (D-007) |

### 3.5 LLM tasks

| Task type | Created when | Priority | Batched into |
|-----------|--------------|----------|--------------|
| `weekly_review` | Every Sunday 09:00 | Normal | Sunday session |
| `research` (per instrument) | Watchlist add · results filed · note expired · W1 alert | Normal (urgent if a holding is down ≥ 15% or the buy zone is hit) | Next session |
| `fund_review` | ~12th of month | Normal | Next Sunday session |
| `deploy_cash` | W3 cash event | Normal | Next session |
| `rebalance` | W2 drift event · quarterly | Normal | Next session |
| `macro_update` | Weekly · after RBI/FOMC | Normal | Next session |

**Lifecycle:** `pending` → `notified` → `done` (output imported) or `expired`.
- **Normal tasks** collect quietly. There's one ping on Sunday ("4 Friday tasks ready").
- **Urgent tasks** ping right away.
- **Reminders:** if a task is still pending after 24 h, Friday re-pings, at most once a day.
- **Expiry:** a weekly review that's still undone the next Saturday is merged into the next one.

**Expected effort:** one session a week. That's one command, mostly waiting, then one paste. Results season adds a few research tasks, but they ride the same session.

### 3.6 Timeline (IST)

| When | What happens |
|------|--------------|
| Mon–Fri 16:30 | D1 India EOD + D4 FX → W5 → W1, W2 |
| Daily 20:00 | D6 announcements → W4 rules → research task if a holding or watchlist stock reported |
| Daily 23:30 | D2 MF NAVs → W5 → W1, W2 |
| Tue–Sat 07:00 | D3 US EOD + D4 FX → W5 → W1, W2 |
| Daily 03:00 | S2 Housekeeper. F1 daily mark |
| Sat 08:00 | D5 fundamentals. D7 macro |
| **Sun 09:00** | Create `weekly_review` (+ `macro_update`). Export context pack. **Ping me** |
| ~12th monthly | D8 fund data → `fund_review` task. F1 monthly report |
| Quarterly | `rebalance` review task |
| FY end (Feb–Mar) | P4 reminders: LRS/TCS totals, holding periods, harvesting window |

### 3.7 Events → reaction

| Event | Raised by | Reaction | Ping |
|-------|-----------|----------|------|
| Watchlist item added | UI | D5 → `research` task | Sunday |
| Holding / cash / remittance edited | UI | W2, W3, P4 recompute | — |
| Price in buy zone | W1 | Urgent `research` task (thesis check) | **Now** |
| Holding down ≥ 15% from cost or high | W1 | Urgent `research` task | **Now** |
| Results or material filing | W4 | D5 → `research` task | Sunday (now if flagged severe) |
| Drift outside band | W2 | `rebalance` task | Sunday |
| Deployable cash above threshold | W3 | `deploy_cash` task | Sunday |
| Stale or bad data | W5 | Block export. Alert in UI | Now |

### 3.8 Laptop reality (D-013)

| Concern | Design answer |
|---------|---------------|
| Lid closed / sleep | On wake, the tick compares last-success times with the schedule and runs missed jobs once |
| Duplicate runs | Every job is idempotent, keyed by `(job, market_date)` |
| Reboot | OS scheduler entry (launchd / cron / systemd timer / Task Scheduler) |
| Offline | Retry with backoff. W5 marks data stale |
| Free sources break | One adapter per source, fallback chain, caching, polite request rate |
| Data loss | Daily SQLite backup |
| I run the session late | Context pack carries a snapshot time. Importer warns if prices moved a lot since then, and marks affected suggestions "re-check price" |

### 3.9 The hand-off contract

#### Context pack (Friday → Claude), in `exchange/` (git-ignored)

| File | Contents |
|------|----------|
| `exchange/pending.json` | Pending tasks: id, type, scope (symbol or portfolio), priority, why it was created, snapshot id |
| `exchange/context/<snapshot_id>.json` | Policy (IPS) · holdings and cash · **precomputed analytics** (allocation, drift, XIRR, exposures, overlap, LRS position, tax-lot summary) · per-instrument data (prices, valuation history, fundamentals, fund metrics) · recent events and filings · current research notes · open suggestions · Scorekeeper stats |

Claude Code subagents read these files. They don't compute numbers. If they need a figure that isn't in the pack, they say so in the output (`missing_data`), and we add it to the exporter.

#### Output (Claude → Friday): one JSON object, pasted into the UI

```json
{
  "friday_schema": "1.0",
  "run_id": "R-2026-10-25-01",
  "snapshot_id": "S-2026-10-25-0900",
  "task_ids": ["T-0412", "T-0413"],
  "research_notes": [
    { "task_id": "T-0413", "agent": "fundamental-analyst", "symbol": "INFY.NS",
      "thesis": "...", "evidence": ["..."], "vs_index": "...",
      "confidence": "medium", "invalidation": "...", "expires_in_days": 90 }
  ],
  "suggestions": [
    { "type": "DEPLOY_CASH", "instruments": ["..."], "amount": 100000, "currency": "INR",
      "staggering": "4 weekly tranches", "why": "...", "vs_index": "...",
      "confidence": "medium", "invalidation": "...", "horizon": "3y+",
      "note_refs": ["T-0413"] }
  ],
  "briefing": { "headline": "...", "body_md": "..." },
  "missing_data": []
}
```

**Importer rules:**
- Validate against `schemas/friday_output.schema.json` and show clear errors. I can paste the error back to Claude to fix.
- The same `run_id` or `task_id` imported twice is ignored (idempotent).
- Run Risk Guard hard rules (3.10) on every suggestion. Status becomes `proposed`, `downgraded` (with reason) or `rejected` (with reason).
- Mark imported tasks `done`. Notes get `expires_at`.

#### Suggestion format (stored)

```
type:         DEPLOY_CASH | BUY | ADD | TRIM | EXIT | SWITCH_FUND | REBALANCE | REMIT_USD | NO_ACTION
instrument(s), market, amount (INR/USD), staggering plan
why:          short rationale + links to research notes
vs_index:     why this beats the index-fund alternative
confidence:   low | medium | high
invalidation: what would make this wrong
horizon:      expected holding period
risk_check:   pass / downgraded / rejected (+ reason)
status:       proposed → accepted | rejected | snoozed | expired
outcome:      return vs benchmark at 1/3/6/12 months (Scorekeeper)
```

### 3.10 Policy (IPS), benchmarks & Risk Guard rules

> No IPS yet. Values below are **proposed defaults** to fill in or change.

- **Return target:** stretch goal, beat Nifty 50 and S&P 500 by 5–10% a year (D-011). Working goal: beat the blended benchmark after costs and taxes over rolling 3 years.
- **Benchmarks (proposed):** India sleeve vs Nifty 50 TRI. US sleeve vs S&P 500 TR in USD (measures picking skill). Whole portfolio in INR vs a blend weighted by target allocation (measures what I actually get).
- Goals & horizon: _TBD_
- Max drawdown I can tolerate: _TBD_
- Target allocation: _TBD_ (India equity / US equity / debt / cash / gold)
- Drift band: ±5% absolute per asset class (proposed)

**Hard rules (Risk Guard, run by the importer), proposed:**
- Emergency-fund cash is never deployable
- Max single stock: 10% of portfolio. Max single sector: 30%
- No leverage, derivatives, shorting or margin
- Deployments above a threshold are staggered over several weeks unless I override
- No new buy in a stock within a few days before its results
- MF suggestions use direct plans only
- Every suggestion cites at least one unexpired research note, and every BUY/ADD has a `vs_index` argument (D-015)
- Warn when US-situs holdings approach the US estate-tax exemption for non-US persons
- Warn before a remittance would cross the LRS limit or TCS threshold for the year

### 3.11 Data model (minimal)

- `instruments`: symbol, exchange, type (stock/MF/ETF), currency, ISIN / AMFI scheme code, sector, domicile
- `holdings_lots`: instrument, buy date, qty/units, price, fees, currency
- `cash_accounts`: name, currency, balance, **earmark** (emergency / deployable / reserved)
- `remittances`: date, INR amount, USD received, FX rate, TCS paid, financial year
- `watchlist`: instrument, my reason, buy zone (optional), max allocation, status (`active` / `candidate`), added date
- `policy` (IPS): goals, horizon, risk tolerance, target allocation and bands, hard rules, benchmarks
- `tax_rules`: config table (rates, holding periods, thresholds), updated after each Budget
- `market_data`: prices, NAVs, FX, fundamentals snapshots
- `events`: type, instrument, payload, urgency, processed flag
- `job_runs`: job, market_date, status, timestamps (catch-up and idempotency)
- `llm_tasks`: id, type, scope, priority, reason, snapshot_id, status, created/notified/done times
- `imports`: run_id, raw paste, validation result, imported_at
- `research_notes`: agent, instrument/scope, thesis, evidence, confidence, **expires_at**
- `suggestions`: see 3.9, with risk check, status and outcome

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

Caveat: these are unofficial or scraped endpoints. Fine for low-volume personal use, but expect breakage. The adapter and fallback design exists for this reason.

### 3.13 Claude Code project (D-016, D-021 to D-023)

#### Friday concepts → Claude Code features

| Friday concept | Claude Code feature | Where |
|----------------|---------------------|-------|
| Rules every agent follows | `CLAUDE.md` (short. This design doc stays separate) | `/CLAUDE.md` |
| LLM agents (R1–R3, P1–P3, C1, F2) | Subagents with model and tools per agent | `.claude/agents/*.md` |
| The one command I run | Skill `/friday-run` | `.claude/skills/friday-run/` |
| Ad-hoc commands | Skills `/research <symbol>`, `/deploy-cash`, `/rebalance-check`, `/ask` | `.claude/skills/` |
| Know-how | Background skills preloaded into subagents: policy, valuation-framework, fund-checklist, tax-india-lrs, note-format, output-schema | `.claude/skills/` |
| Agent learnings | Subagent `memory: project` | `.claude/agent-memory/<agent>/` |
| Data hand-off | Read-only context pack files | `exchange/` |

#### `/friday-run` flow

1. Read `exchange/pending.json` and the context pack it points to.
2. Run the subagents each task needs: research tasks first (R1/R2/R3), then portfolio work (P1–P3).
3. Run `cio` once over all new notes and plans.
4. Run `briefing` if a weekly review is included.
5. Print **one** JSON object that matches the output schema. Optionally also save it to `exchange/outbox/<run_id>.json`.

Subagent tools: `Read` (context pack and skills) for all. `WebSearch` and `WebFetch` only for research agents (R1–R3). No agent can write to the DB, because none has a path to it.

#### Project layout (target)

```
friday/
├── agents.md                 # this design doc (memory for brainstorming)
├── CLAUDE.md                 # short rules loaded in every Claude session
├── .claude/
│   ├── agents/               # 8 subagents
│   ├── skills/               # friday-run, research, deploy-cash, rebalance-check, ask
│   │                         # + policy, valuation-framework, fund-checklist,
│   │                         #   tax-india-lrs, note-format, output-schema
│   └── agent-memory/
├── schemas/
│   └── friday_output.schema.json
├── friday/                   # Python package
│   ├── db.py                 # SQLite schema and access
│   ├── fetchers/             # nse, amfi, yahoo, edgar, fred, fx
│   ├── calc/                 # xirr, drift, valuation, overlap, tax, lrs
│   ├── watchers/             # W1–W5
│   ├── tasks.py              # LLM task creation and lifecycle
│   ├── context_pack.py       # exporter
│   ├── importer.py           # validate, dedupe, Risk Guard, store
│   ├── risk_rules.py         # hard rules
│   ├── notify.py             # desktop / email
│   ├── scorekeeper.py
│   └── orchestrator.py       # `friday tick`
├── web/                      # UI
├── exchange/                 # git-ignored: pending.json, context/, outbox/
├── data/friday.db            # git-ignored
└── logs/                     # git-ignored
```

---

## 4. Roadmap / parking lot

- **v2: automation.** Friday runs `claude -p "/friday-run"` itself and imports the output (no paste). Needs the earlier designs D-018 (LLM part) and D-020: locked-down permissions (`--permission-mode dontAsk`, allowlist), one job at a time, budget cap, and probably an MCP server for tools. Do this only once the manual loop has proven itself.
- **v2 candidates:** Tax Agent (full) · Screener/Idea Scout · External Tips Intake (D-007) · CAS / broker CSV import · Technical & Sentiment agents · Telegram notifications · import from `exchange/outbox/` with one click instead of pasting
- **Later:** broker read-only sync · backtesting the CIO on historical data · "what-if" simulator in the UI · goal-based planning
- **Idea to evaluate:** Ireland-domiciled (UCITS) ETFs as an alternative to US-domiciled ETFs. They reduce US estate-tax exposure and dividend withholding for Indian residents, but they trade on LSE, not NASDAQ.
- **Ideas inbox rule (for screener/tips):** an idea goes to the watchlist as `candidate` → R1/R2 research → only then is it eligible for the CIO. No shortcuts.

---

## 5. Open questions

1. **IPS values:** goals, horizon, max drawdown, target allocation India vs US vs debt vs gold (3.10)
2. **Tax rules config:** rates, holding periods and LRS/TCS thresholds change with budgets. Who updates `tax_rules`, and how?
3. **Tech stack:** backend language (Python assumed for fetchers), web framework, frontend
4. **Laptop OS:** macOS, Windows or Linux? Decides the OS scheduler for `friday tick` and the desktop-notification library
5. **Email pings:** wanted in v1, or in-app + desktop is enough?
6. **Existing US holdings:** which broker? Affects how lots and historical FX rates are entered
7. **Where the screener/tips come from** when we build them

### Resolved
- ~~Tax residency~~ → D-010 · ~~Data budget~~ → D-012 · ~~Hosting~~ → D-013 · ~~Benchmarks / target~~ → D-011 · ~~Which LLM~~ → D-016 · ~~Agent framework~~ → D-016 · ~~Claude billing~~ → D-021 (manual runs use my normal Claude Code login)

---

## 6. Changelog

| Version | Date | Change |
|---------|------|--------|
| v1 | 2026-10-24 | Initial architecture from first brainstorm. Decisions D-001 to D-009. v1 agent roster, schedules, data model, suggestion format |
| v1.1 | 2026-10-24 | Decisions D-010 to D-015 (LRS resident, return target, free data, laptop-local, urgency policy, index baseline). Full system design: runtime components, roster by layer, IST timeline, event table, laptop resilience, LLM load estimate. Added LRS & Tax Ledger, Data Health, Orchestrator, Housekeeper. Data sources decided |
| v1.2 | 2026-10-24 | Decisions D-016 to D-020: Friday as a Claude Code project (subagents, skills, local MCP server), Python for non-LLM work, `friday tick` + `claude -p` scheduling, hard rules in code, locked-down unattended permissions |
| v1.3 | 2026-10-24 | **Manual LLM step** (D-021 to D-026). Friday notifies me, I run `/friday-run` in Claude Code, paste the JSON into the UI. Context packs replace the MCP server. Importer validates and applies Risk Guard. Filing triage moved to code, no daily LLM work. Added the manual loop, LLM task types and lifecycle, and the hand-off contract. D-019 and D-020 superseded. Automation moved to the v2 roadmap |

---

## How to use this file

- **Start of a session:** read sections 2, 3 and 5.
- **New decision:** add a row to the Decision log with the next `D-###`. To reverse a decision, mark the old row `Superseded by D-###`. Don't delete it.
- **Plan changes:** small edits go into the current version with a Changelog line. A significant redesign bumps the version: move the old plan to `docs/plans/vN.md` and start the new "Current plan" here.
- **Unresolved items** go to Open questions. **Good ideas that are out of scope** go to the Roadmap / parking lot.
- If this file gets too big, split it into `docs/architecture/*.md` and keep this file as the index.
