# Friday — Build Phases

> How the v1.2 architecture ([`architecture.md`](architecture.md), [`agents.md`](../agents.md)) gets built, one usable step at a time.
> Component IDs (`D1`, `R1`, `C1`, …) and decision IDs (`D-###`) refer to `agents.md`.

**Approved:** 2026-10-24 (D-021) · **Matches plan:** v1.2

---

## Principles

1. **Data before AI.** The AI is only as good as the numbers it's given.
2. **Run the AI by hand before letting it run on its own.** Judge its quality while watching, then trust it unattended.
3. **Each phase is usable by itself.** Value at every step, not only at the end.

## Overview

| Phase | Name | One-line goal | AI? | Automatic? |
|-------|------|---------------|-----|------------|
| 1 | Tracker | Know where I stand | No | Prices only (cron) |
| 2 | Research on demand | Ask Friday about a stock or fund | Yes, run by me | No |
| 3 | Suggestions on demand | Tell me what to do | Yes, run by me | No |
| 4a | Watchers & alerts | Friday notices things and tells me | No (alerts only) | Yes, Python jobs |
| 4b | Automatic AI runs | Friday thinks on its own schedule | Yes, automatic | Yes, everything |
| 5 | Wider view & feedback | Sees more, explains more, grades itself | Yes | Yes |
| Later | v2 and beyond | See roadmap | — | — |

---

## Phase 1: Tracker ("know where I stand")

| | |
|---|---|
| **Goal** | See my whole portfolio in one place with correct numbers |
| **Builds** | Project skeleton and SQLite database · screens to enter holdings (tax lots), cash accounts (with earmarks), US remittances and the watchlist · fetchers for India prices, fund NAVs, US prices and USD/INR (D1–D4), scheduled with plain **cron** (or the OS equivalent), plus a "Refresh prices" button · portfolio maths: allocation, P&L, XIRR, INR and USD views · basic LRS totals per financial year (P4, lite) |
| **Detail** | cron skips runs while the laptop sleeps, so each fetcher fills in every missing date since its last successful run (D-022) |
| **Not yet** | Any AI, watchers, alerts, catch-up logic beyond backfill |
| **Journeys** | J1 (without research), J7 (totals only) |
| **Done when** | All my real holdings are in, prices update daily by themselves, and the numbers match my broker statements |
| **Stack** | React + FastAPI (D-023), details in `agents.md` 3.14 |

## Phase 2: Research on demand ("ask Friday about a stock")

| | |
|---|---|
| **Goal** | Get a solid research note on any watchlist stock or fund when I ask |
| **Builds** | `CLAUDE.md` · Friday MCP server: read tools, calculation tools, `write_research_note` · financials fetcher (D5) · subagents `fundamental-analyst` (R1) and `fund-analyst` (R2) · skill `/research <symbol>` · know-how skills: valuation framework, fund checklist, note format · research notes in the UI, with expiry |
| **How I use it** | Open `claude` in the project → `/research INFY` → read the note in the UI, ask follow-up questions |
| **Not yet** | Suggestions, automatic runs |
| **Journeys** | J1 (complete), J2 (by hand), J8 |
| **Done when** | My whole watchlist has notes, and spot checks show they're accurate and useful |

## Phase 3: Suggestions on demand ("tell me what to do")

| | |
|---|---|
| **Goal** | Get ranked, rule-checked suggestions when I ask |
| **Builds** | Policy (IPS) screen: target mix, drift bands, limits · subagents `portfolio-doctor` (P1), `rebalancer` (P2), `cash-deployer` (P3), `cio` (C1) · Risk Guard hard rules checked in code inside `create_suggestion` (C2, D-019) · Suggestions tab: accept, reject, snooze, history · skills `/weekly-review`, `/deploy-cash`, `/rebalance-check`, India tax/LRS know-how · each suggestion stores its starting price for later grading |
| **How I use it** | Run `/weekly-review` myself on Sunday, then act on the suggestions |
| **Not yet** | Automatic runs, weekly letter, macro view |
| **Journeys** | J3 (by hand), J4 (by hand), J7 (used in cash plans), J10 (starting prices stored) |
| **Done when** | I've run 3–4 weekly reviews by hand and trust the output and the rules |
| **Needs from me** | Policy numbers: target mix, maximum loss I'd tolerate, limits |

## Phase 4a: Watchers & alerts ("Friday notices things")

| | |
|---|---|
| **Goal** | Friday watches the portfolio 24/7 and tells me when something needs attention |
| **Builds** | `friday tick` replaces cron (D-018, Python jobs only): `job_runs` table, catch-up after sleep, no duplicate runs, retries · watchers: Watchlist Sentinel (W1), Drift Monitor (W2), Cash Monitor (W3), Data Health (W5) · `events` table with urgency · in-app notifications ("NVDA hit your buy zone, run `/research NVDA`") · Housekeeper: daily backups, expiring old notes (S2) · daily grading of suggestions (F1) |
| **How I use it** | Get an alert, then run the suggested command myself |
| **Not yet** | Claude runs by itself |
| **Journeys** | J4 (cash flagged), J5 (alert, research by hand), J9 (for Python jobs), J10 (daily grading) |
| **Done when** | Two weeks with no missed or duplicated jobs, and alerts that are useful rather than noisy |
| **Needs from me** | Laptop OS |

## Phase 4b: Automatic AI runs ("Friday thinks on its own")

| | |
|---|---|
| **Goal** | Research, weekly reviews and urgent checks happen without me starting them |
| **Builds** | The tick starts `claude -p "/<skill>"` for due AI work (D-018) · locked-down permissions: `--permission-mode dontAsk` plus allowlist (D-020) · one Claude job at a time, spending cap per run, logs and retries · automatic Sunday `/weekly-review` · automatic `/research` on watchlist add and note expiry · urgent mid-week flow: thesis check → CIO, at most once a day (D-014) |
| **How I use it** | Open the Suggestions tab. Everything is already there |
| **Journeys** | J2, J3, J4, J5 (all automatic), J9 (including Claude runs) |
| **Done when** | Two weeks of unattended AI runs within budget, with no stuck or failed runs left unhandled |
| **Needs from me** | Subscription login vs API key for unattended runs |

## Phase 5: Wider view & feedback ("sees more, grades itself")

| | |
|---|---|
| **Goal** | Friday reacts to results and the economy, explains itself weekly, and shows whether it's any good |
| **Builds** | Company announcements fetcher (D6) + Filing Triage (W4) → results trigger research · economy data (D7) + `macro-strategist` (R3) + `/macro-update` · fund holdings data (D8) + monthly `/fund-review` + overlap across funds · weekly letter (F2) · monthly Scorekeeper report (F1) · agent memory · full LRS, TCS and US estate-tax warnings (P4) |
| **Journeys** | J3 (with letter), J6, J7 (full warnings), J10 (report) |
| **Done when** | The letter arrives every Sunday and the first Scorekeeper report is out |

## Later (v2 and beyond)

Full Tax Agent · screener / idea scout and external tips (D-007) · technical and sentiment agents · CAS or broker statement import · email and Telegram alerts · backtesting the CIO. See `agents.md` section 4.

---

## When each user journey starts working

| Journey | P1 | P2 | P3 | P4a | P4b | P5 |
|---------|----|----|----|-----|-----|----|
| J1 First-time setup | ◐ no research | ● | | | | |
| J2 Add to watchlist → research | | ◐ by hand | | | ● automatic | |
| J3 Sunday weekly review | | | ◐ by hand | | ● automatic | ● + letter |
| J4 Salary arrives → deploy cash | | | ◐ by hand | ◐ cash flagged | ● automatic | |
| J5 Market falls → urgent check | | | | ◐ alert, research by hand | ● automatic | |
| J6 Results season | | | | | | ● |
| J7 Sending money to the US (LRS) | ◐ totals | | ◐ used in cash plans | | | ● warnings |
| J8 Ask Friday | | ● | | | | |
| J9 Laptop asleep → catch-up | ◐ price backfill | | | ● Python jobs | ● incl. AI runs | |
| J10 Is Friday any good? | | | ◐ starting prices stored | ◐ daily grading | | ● report |

◐ = partly works · ● = fully works

## Decisions needed, by phase

| Phase | Decision | Open question in `agents.md` |
|-------|----------|------------------------------|
| 1 | ~~Tech stack~~ → decided (D-023) | #4 (resolved) |
| 3 | Policy numbers (target mix, max loss, limits) | #2 |
| 4a | Laptop OS | #8 |
| 4b | Subscription login vs API key | #1 |
