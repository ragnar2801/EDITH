# Friday — Architecture Overview

> Plain-language overview of the **target architecture** (plan v1.2) and the user journeys it supports.
> Decisions, detailed tables and open questions live in [`agents.md`](../agents.md). Build order: [`phases.md`](phases.md). Decision IDs (`D-###`) and component IDs (`R1`, `C1`, …) refer to that file.

**Matches plan:** v1.2 · **Last updated:** 2026-10-24

---

## TL;DR

- **What it is:** a personal analyst for my Indian and US stocks, mutual funds and ETFs. It runs 24/7 on my laptop and suggests what to do with my cash and portfolio. It never trades. I place every trade myself.
- **How it works:** plain Python code does the routine work (downloading prices, maths, watching for triggers). Claude is only called when judgment is needed, roughly 10–20 times a week.
- **Built on Claude Code:** each AI agent is a Claude Code subagent, each workflow is a skill such as `/weekly-review`, and a small local service (an MCP server) gives Claude safe tools to read my data.
- **Runs itself:** a scheduler wakes up every 15 minutes, checks what's due, runs it, and catches up after the laptop has been asleep.
- **Safety:** hard rules (position limits, emergency fund, LRS limits) are checked in code, not by the AI. Only one agent, the CIO, can create suggestions.

---

## 1. What Friday does

| | |
|---|---|
| **Tracks** | My cash (INR and USD) and my holdings in India and the US |
| **Watches** | Prices, fund NAVs, company results and filings, the economy |
| **Researches** | Every stock and fund on the watchlist I curate |
| **Suggests** | Where to put idle cash, when to rebalance, what to add, trim or switch, each with a reason |
| **Grades itself** | Compares every past suggestion against Nifty and the S&P 500 |

---

## 2. The big picture

```
 My laptop (runs 24/7)

   Web UI (React)
        │
   API (FastAPI) ──► Database (one file) ◄── Python jobs (prices, maths, watchers)
                          ▲                        ▲
                          │                        │
                 Friday tool service          friday tick (every 15 min)
                          ▲                        │
                 Claude Code agents ◄──────────────┘
                 (analysts, CIO)
```

---

## 3. The parts

| Part | Plain-English job |
|---|---|
| **Web UI (React)** | Where I enter holdings and cash, and read suggestions and the weekly letter |
| **API (FastAPI)** | The UI's only way to read or change data. Uses the same core code as the jobs and the tool service |
| **Database** | One SQLite file holding everything: holdings, prices, research notes, suggestions |
| **Python jobs** | Download free data (NSE, AMFI, Yahoo, SEC EDGAR, FRED) and do all the calculations |
| **`friday tick`** | The heartbeat. Every 15 minutes it asks "what's due?" and runs it |
| **Friday tool service (MCP server)** | Claude's only door to my data: "get holdings", "calculate drift", "save note", "create suggestion". It enforces the rules |
| **Claude Code project** | Agent definitions, skills and rules, all stored in this repo |

---

## 4. Who does what

| Group | Members | What they do | AI? |
|---|---|---|---|
| **Collectors** | India prices, fund NAVs, US prices, exchange rate, financials, filings, economy data, fund details (D1–D8) | Fetch fresh data daily or weekly | No |
| **Watchers** | Watchlist Sentinel, Drift Monitor, Cash Monitor, Data Health (W1–W3, W5) | Raise a flag when a price hits my buy zone, my mix drifts, cash piles up, or data looks wrong | No |
| **Filter** | Filing Triage (W4) | Separates important announcements from noise | Small model |
| **Analysts** | Fundamental Analyst, Fund Analyst, Macro Strategist (R1–R3) | Write research notes: is this a good business, a good fund, a good time? | Yes |
| **Portfolio helpers** | Portfolio Doctor, Rebalancer, Cash Deployer (P1–P3) | Check portfolio health, plan rebalancing trades, decide where cash goes | Yes |
| **Bookkeeper** | LRS & Tax Ledger (P4) | Tracks money sent abroad against the yearly LRS limit and TCS threshold, holding periods, US estate-tax exposure | No |
| **Decision maker** | CIO (C1) | Reads everything, argues the other side, then writes ranked suggestions | Yes (largest model) |
| **Gatekeeper** | Risk Guard (C2) | Blocks or downgrades any suggestion that breaks my rules | Code (a small model writes the explanation) |
| **Reporter** | Briefing Agent (F2) | Weekly letter and answers to my questions | Yes |
| **Grader** | Scorekeeper (F1) | Grades past suggestions against the benchmarks | No |
| **Caretakers** | Orchestrator, Housekeeper (S1, S2) | Scheduling, catch-up, backups, cleanup | No |

---

## 5. A normal week (IST)

| When | What happens |
|---|---|
| Weekdays 16:30 | India closing prices → watchers |
| Every evening | Company announcements filtered. Important ones get researched |
| Every night ~23:30 | Fund NAVs → watchers |
| Tue–Sat 07:00 | US closing prices → watchers |
| Saturday | Financials and economy data refresh, then the Macro Strategist |
| **Sunday 09:00** | **Weekly review:** health check → rebalance and cash plans → CIO → Risk Guard → weekly letter |
| Monthly | Fund reviews, Scorekeeper report |

Most flags wait for Sunday. Only urgent ones trigger a mid-week CIO run, at most once a day: a holding falling 15% or more, a price hitting my buy zone, or the case for a stock breaking down.

---

## 6. Safety rails

| Rail | How |
|---|---|
| Friday never trades | No broker connection. Suggestions only |
| AI can't break my rules | Limits are checked in code when a suggestion is saved |
| A manipulated web page can't create a suggestion | Agents that browse the web can't create suggestions. The CIO, which can, doesn't browse |
| No surprise bills | One Claude job at a time, with a spending cap per run |
| Unattended runs can't do anything unexpected | Each run gets an allowlist of tools. Anything else is refused, not waited on |
| Stale data isn't used | Data Health pauses the CIO if prices are old or wrong |

---

## 7. How it maps onto Claude Code

| Friday concept | Claude Code feature | Where |
|---|---|---|
| Rules every agent follows | `CLAUDE.md` | Repo root |
| AI agents | Subagents (own model, tools, memory) | `.claude/agents/*.md` |
| Workflows (`/weekly-review`, `/research <symbol>`, `/deploy-cash`, …) | Skills, used as slash commands | `.claude/skills/<name>/SKILL.md` |
| Know-how (valuation framework, fund checklist, India tax and LRS rules) | Background skills, preloaded into the agents that need them | `.claude/skills/` |
| Tools (`get_holdings`, `xirr`, `create_suggestion`, …) | Local MCP server over the database and calculation code | `.mcp.json` → `friday/mcp_server.py` |
| Scheduled AI runs | `friday tick` starts `claude -p "/<skill>"` with a tool allowlist | OS scheduler → `friday/orchestrator.py` |
| Manual AI runs | Interactive `claude` in the project folder | — |

Full mapping, subagent list and project layout: `agents.md` section 3.13.

---

## 8. User journeys

### J1. First-time setup
1. **Me:** enter holdings as individual purchases (date, quantity, price), my cash accounts (each tagged *emergency*, *deployable* or *reserved*), past remittances to the US, and my policy (target mix, limits).
2. **Me:** add stocks and funds to the watchlist, each with a line on *why* I'm watching it.
3. **Friday:** downloads price history and runs a first research pass on each watchlist item.
4. **I see:** the portfolio dashboard with allocation, returns (XIRR) and drift, plus a research note on every watchlist item.

### J2. Adding a stock to the watchlist
1. **Me:** add `NVDA` with "AI capex leader, buy on dips".
2. **Friday (next tick):** fetches its financials and runs `/research NVDA` with the Fundamental Analyst.
3. **I see:** the note within about 15–30 minutes: business quality, valuation, red flags, and why it beats or doesn't beat just buying the index.
4. It feeds into the next Sunday review.

### J3. Sunday weekly review (the core loop)
1. **Friday, Sunday 09:00:** Portfolio Doctor → Rebalancer and Cash Deployer if needed → CIO → Risk Guard → weekly letter.
2. **Me, Sunday or Monday:** open the Suggestions tab, e.g. *"Add ₹50k to Nifty index fund, 4 weekly parts. Confidence: medium. Wrong if: …"*.
3. **Me:** accept, reject or snooze each one. If I accept, I place the trade at my broker and record it in Friday.
4. **Friday:** starts tracking that suggestion's result for the Scorekeeper.

### J4. Salary or bonus arrives
1. **Me:** update the bank balance.
2. **Friday:** the Cash Monitor sees deployable cash over the threshold. The Cash Deployer plans India vs US, all at once vs spread over weeks, and where to park the money meanwhile.
3. **I see on Sunday:** a "Deploy cash" suggestion. If it involves the US, it accounts for TCS and the currency spread.

### J5. Market falls sharply
1. **Friday (after close):** the Sentinel sees a holding down 18% from its high. That counts as **urgent**.
2. **Friday:** the Fundamental Analyst re-checks the case for the stock (business problem, or just price?). Then a mid-week CIO run.
3. **I see:** an alert, e.g. *"HOLD, thesis intact"* or *"ADD, within limits"* or *"EXIT, thesis broken"*, with reasons.

### J6. Results season
1. **Friday (evening):** a held stock reports results. Triage marks it as important.
2. **Friday:** refreshes the financials, and the analyst updates the stock's note.
3. **I see:** the updated note, and a "what changed" line in Sunday's letter. A suggestion only appears if the case changed.

### J7. Sending money to the US (LRS)
1. **Me:** log a remittance (INR sent, USD received, TCS paid).
2. **Friday:** the LRS & Tax Ledger updates the year's totals.
3. **I see:** warnings when I'm near the TCS threshold, the LRS limit, or US estate-tax exposure. The Cash Deployer uses these when choosing India vs US.

### J8. Asking Friday something
1. **Me:** open `claude` in the project and ask "Why did you suggest trimming HDFC?", or run `/research TSLA`, or `/deploy-cash 200000`.
2. **Claude:** answers from my stored notes and data, or runs the same agents on demand.

### J9. Laptop was asleep
1. **Me:** close the lid on Friday night and open it on Sunday afternoon.
2. **Friday (on wake):** the tick sees missed jobs, runs each one once, then runs the weekly review.
3. **I see:** everything up to date, nothing duplicated.

### J10. Is Friday actually any good?
1. **Friday (monthly):** the Scorekeeper grades every past suggestion at 1, 3, 6 and 12 months against Nifty and the S&P 500.
2. **I see:** hit rate per agent, and Friday's results vs my 5–10% outperformance goal. This tells me whether to keep trusting it, or just buy the index.
