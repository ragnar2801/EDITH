# Friday — Build Phases

> How the v1.2 architecture ([`architecture.md`](architecture.md), [`agents.md`](../agents.md)) gets built, one usable step at a time.
> Component IDs (`D1`, `R1`, `C1`, …) and decision IDs (`D-###`) refer to `agents.md`.

**Approved:** 2026-10-24 (D-021) · **Re-planned:** 2026-10-25, **mutual funds first** (D-043) · **Matches plan:** v1.2

---

## Principles

1. **Data before AI.** The AI is only as good as the numbers it's given.
2. **Run the AI by hand before letting it run on its own.** Judge its quality while watching, then trust it unattended.
3. **Each phase is usable by itself.** Value at every step, not only at the end.
4. **One asset type end to end first (D-043).** Mutual funds go through every layer (tracking, research, suggestions, alerts, automatic runs, feedback) before Indian stocks, ETFs and US holdings are added. Funds are the simplest asset (one free daily NAV file, no splits, no currency) and are what I mostly own.

## My strategy, in one paragraph

I keep a **target split** across a few funds (large cap, mid cap, small cap, flexi cap) plus an emergency amount in an arbitrage fund that is never invested. New cash goes to the funds furthest below their target, so I rarely sell. Large amounts are staggered through a liquid or arbitrage fund. A fund is replaced only when a rule says so (it trails its category and the index over rolling years, its manager or mandate changes). Most of this is arithmetic in code. Claude helps with the judgment calls: is each fund still a good pick, stagger or invest now, switch or hold, and explaining why.

## Overview

| Phase | Name | One-line goal | AI? | Automatic? |
|-------|------|---------------|-----|------------|
| 1 | Fund tracker and planner | Know where my funds stand, test my split, know where new cash goes | No | NAVs only |
| 2 | Fund research on demand | Ask Friday about a fund | Yes, run by me | No |
| 3 | Fund suggestions on demand | Tell me what to do with my funds | Yes, run by me | No |
| 4a | Watchers & alerts | Friday notices things and tells me | No (alerts only) | Yes, Python jobs |
| 4b | Automatic AI runs | Friday thinks on its own schedule | Yes, automatic | Yes, everything |
| 5 | Wider view & feedback | Sees the economy, writes a letter, grades itself | Yes | Yes |
| 6 | Indian stocks and ETFs | Add them across every layer above | Yes | Yes |
| 7 | US holdings and LRS | Add US stocks and ETFs, USD/INR and LRS across every layer | Yes | Yes |
| Later | v2 and beyond | See roadmap | — | — |

**Benchmark (D-043):** the **Nifty 50**, measured with a Nifty 50 index fund's NAV (dividends included), so "beat the index" is literally "beat the index fund I could have bought instead" (D-015). The S&P 500 half of D-011 waits for Phase 7.

---

## Phase 1: Fund tracker and planner ("know where I stand")

| | |
|---|---|
| **Goal** | See all my funds with correct numbers, test target splits on history, and know exactly where new cash should go |
| **Builds** | Instruments *(done: T1-02)* · daily and historical fund NAVs (D2) with catch-up · **buckets**: my target split with weights, rebalance policy and benchmark · **backtests** of a bucket: lump sum, SIP, SWP and a custom timeline, against the Nifty 50 (these three come from the earlier `ragnar2801/Friday` app, D-043) · fund holdings I type in (lump sums, SIPs, sells; one lot per buy) · cash accounts with an emergency earmark · "I have ₹X, where does it go?" plan towards the target split · portfolio view vs target: value, P&L, XIRR, drift · NAVs synced by hand (no scheduler until Phase 4a, D-068) |
| **Not yet** | Any AI, watchers, alerts |
| **Journeys** | J1 (without research), J4 (the plan is arithmetic, no AI yet) |
| **Done when** | All my real funds are in, a NAV sync brings every fund up to date, the numbers match my statements, and the cash plan matches a hand calculation |
| **Stack** | React + Python backend (D-023); details decided in the tasks |
| **Tasks** | [`tasks/phase-1.md`](tasks/phase-1.md) |

## Phase 2: Fund research on demand ("ask Friday about a fund")

| | |
|---|---|
| **Goal** | Get a solid research note on any fund I hold or watch, when I ask |
| **Builds** | Watchlist (moved here from Phase 1) · **source check first**: what fund data is free and reliable · fund data (D8): expense ratio and fund size (AMFI), returns and rolling returns vs category peers and the Nifty 50 index fund (computed from NAVs), portfolio holdings parsed only for the AMCs I use · `CLAUDE.md` · Friday MCP server: read tools, calculation tools, `write_research_note` · subagent `fund-analyst` (R2) · skill `/research <fund>` · fund checklist and note format · research notes in the UI, with expiry |
| **How I use it** | Open `claude` in the project → `/research "Parag Parikh Flexi Cap"` → read the note in the UI |
| **Not yet** | Suggestions, automatic runs |
| **Journeys** | J1 (complete), J2 (by hand), J8 |
| **Done when** | Every fund I hold or watch has a note, and spot checks show it's accurate and useful |
| **Risk** | Fund holdings data comes from AMC Excel files in many formats. Overlap, style drift and look-through depend on it, so they cover only the AMCs I use |

## Phase 3: Fund suggestions on demand ("tell me what to do")

| | |
|---|---|
| **Goal** | Get ranked, rule-checked suggestions for my funds when I ask |
| **Builds** | Policy (IPS) screen: target split (from my bucket), drift bands, emergency amount, staggering rule · values for anything I hold outside Friday, typed in per asset class, so allocation advice sees the whole portfolio · fund tax and cost rules in `tax_rules` (equity vs debt fund taxation, the yearly tax-free long-term gain, exit loads, ELSS lock-in per instalment; values verified against official sources) · exit load and lock-in per fund, typed in · subagents `portfolio-doctor` (P1, with fund overlap), `rebalancer` (P2, new cash first, then tax- and exit-load-aware sells), `cash-deployer` (P3, lump sum vs staggered STP from liquid/arbitrage), `cio` (C1) · Risk Guard rules for funds in code (C2, D-019): emergency money never deployed, max per fund and per AMC, direct plans only · suggestion types for funds: deploy cash, rebalance, start/change/stop a SIP, switch fund, regular → direct, harvest gains, no action · Suggestions tab: accept, reject, snooze, history · each suggestion stores its starting NAV for grading |
| **How I use it** | Run `/monthly-review` myself, then act on the suggestions |
| **Cadence** | Suggestions **monthly**; fund decisions are few, so a weekly CIO run would mostly say "no action" |
| **Journeys** | J3 (by hand, monthly), J4 (by hand), J10 (starting NAVs stored) |
| **Done when** | I've run 2–3 monthly reviews by hand and trust the output and the rules |
| **Needs from me** | Policy numbers: target split, drift bands, emergency amount, limits |

## Phase 4a: Watchers & alerts ("Friday notices things")

| | |
|---|---|
| **Goal** | Friday watches my funds and tells me when something needs attention |
| **Builds** | `friday tick` and the first Task Scheduler entry (D-018, D-027; Phase 1 had none, D-068; Python jobs only): `job_runs`, catch-up after sleep, no duplicate runs, retries · watchers for funds: Drift Monitor (W2), Cash Monitor (W3), a big market fall (Nifty 50 index fund down a set % from its high), Data Health (W5) · `events` table with urgency · in-app notifications · Housekeeper: daily backups, expiring old notes (S2) · daily grading of suggestions (F1) |
| **How I use it** | Get an alert, then run the suggested command myself |
| **Journeys** | J4 (cash flagged), J5 (big fall alert), J9 (Python jobs), J10 (daily grading) |
| **Done when** | Two weeks with no missed or duplicated jobs, and alerts that are useful rather than noisy |

## Phase 4b: Automatic AI runs ("Friday thinks on its own")

| | |
|---|---|
| **Goal** | Research, monthly reviews and urgent checks happen without me starting them |
| **Builds** | The tick starts `claude -p "/<skill>"` for due AI work (D-018) · locked-down permissions (D-020) · one Claude job at a time, spending cap per run, logs and retries · automatic monthly `/monthly-review` · automatic `/research` on watchlist add and note expiry · the urgent flow for funds is only the big-market-fall rule, at most once a day (D-014) |
| **How I use it** | Open the Suggestions tab. Everything is already there |
| **Journeys** | J2, J3, J4, J5 (all automatic), J9 (including Claude runs) |
| **Done when** | Two months of unattended AI runs within budget, with no stuck or failed runs left unhandled |
| **Needs from me** | Subscription login vs API key for unattended runs |

## Phase 5: Wider view & feedback ("sees more, grades itself")

| | |
|---|---|
| **Goal** | Friday reads the Indian economy, explains itself weekly, and shows whether it's any good |
| **Builds** | Economy data for India (D7: rates, inflation, Nifty P/E) + `macro-strategist` (R3, India only) + `/macro-update` · weekly letter (F2) · monthly Scorekeeper report vs the Nifty 50 index fund (F1) · monthly `/fund-review` of all held and watched funds · agent memory |
| **Journeys** | J3 (with letter), J10 (report) |
| **Done when** | The letter arrives every Sunday and the first Scorekeeper report is out |

## Phase 6: Indian stocks and ETFs

| | |
|---|---|
| **Goal** | Add NSE stocks and ETFs to every layer above |
| **Builds** | Stock holdings with corporate actions (splits, bonuses, mergers, demergers) · NSE end-of-day prices with a fallback, and the NSE holiday calendar (D1) · REITs, InvITs and BSE-only stocks (was T1-11) · fundamentals (D5), corporate events (D6) and Filing Triage (W4) · `fundamental-analyst` (R1) and the results-season flow · stock rules: max single stock, max sector, no buys just before results |
| **Journeys** | J6 (results season) |
| **Carries over** | The content of dropped Phase 1 tasks T1-03, T1-05, T1-07 (stocks part) and T1-11 |

## Phase 7: US holdings and LRS

| | |
|---|---|
| **Goal** | Add US stocks and ETFs, USD/INR and the LRS rules to every layer above |
| **Builds** | US end-of-day prices (D3) and USD/INR (D4) · remittances with LRS and TCS totals per financial year (P4) · INR and USD views, and the part of a return caused by USD/INR · US half of the benchmark (S&P 500, D-011) · US macro · US estate-tax and LRS warnings |
| **Journeys** | J7 (sending money to the US) |
| **Carries over** | The content of dropped Phase 1 tasks T1-04 (remittances part), T1-06 and T1-08 (USD part) |

## Later (v2 and beyond)

Full Tax Agent · screener / idea scout and external tips (D-007) · technical and sentiment agents · CAS or broker statement import · email and Telegram alerts · backtesting the CIO. See `agents.md` section 4.

---

## When each user journey starts working

| Journey | P1 | P2 | P3 | P4a | P4b | P5 | P6 | P7 |
|---------|----|----|----|-----|-----|----|----|----|
| J1 First-time setup | ◐ no research | ● | | | | | | |
| J2 Add to watchlist → research | | ◐ by hand | | | ● automatic | | | |
| J3 Review (monthly for funds) | | | ◐ by hand | | ● automatic | ● + letter | | |
| J4 Salary arrives → deploy cash | ◐ plan, no AI | | ◐ by hand | ◐ cash flagged | ● automatic | | | |
| J5 Market falls → urgent check | | | | ◐ alert | ● automatic | | | |
| J6 Results season | | | | | | | ● | |
| J7 Sending money to the US (LRS) | | | | | | | | ● |
| J8 Ask Friday | | ● | | | | | | |
| J9 Laptop asleep → catch-up | ◐ NAV catch-up | | | ● Python jobs | ● incl. AI runs | | | |
| J10 Is Friday any good? | | | ◐ starting NAVs stored | ◐ daily grading | | ● report | | |

◐ = partly works · ● = fully works

## Decisions needed, by phase

| Phase | Decision | Open question in `agents.md` |
|-------|----------|------------------------------|
| 1 | Data sources, data model, rule values → decided inside the tasks in [`tasks/phase-1.md`](tasks/phase-1.md) | #4 |
| 2 | Which fund data sources work (source check) | — |
| 3 | Policy numbers (target split, drift bands, emergency amount, limits); fund tax values | #2, #3 |
| 4b | Subscription login vs API key | #1 |
| 7 | Which US broker, historical FX for old lots | #7 |
