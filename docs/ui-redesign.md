# UI rework: user journeys and screens

> Tasks T1-21 and T1-22 (board: [`tasks/phase-1.md`](tasks/phase-1.md)). Approved 2026-10-25 as D-060 to D-067 in `agents.md`, all with the recommendations in section 9. **Built 2026-10-25**; section 1 describes the app before, section 10 lists where the build differs from this plan.
> Scope: what Phase 1 has built today. Later phases get their screens when they are built, not before.

---

## 1. What's wrong today

The app is organised the way it was built: **one nav item per task**. Each task added a page, explained itself on that page, and pointed at the tasks still to come. The result reads like a build log, not a product.

| Problem | Where it shows |
|---|---|
| **Nav mirrors the build plan, not my jobs.** 7 items; two are plumbing (Instruments, Data status) and two are halves of one idea (Buckets, Backtest) | `app/navigation.ts` |
| **The payoff is buried.** "I have ₹X, where does it go?" is the reason the app exists, and it sits inside Cash, between balance tiles and an accounts table | `CashPage.tsx` |
| **The key link is hidden.** Which bucket is my target is set in Cash → Plan settings → Change settings → a dropdown. Nothing on Buckets or Holdings says which one it is | `CashPage.tsx` `SettingsForm` |
| **One fund, two pages.** A fund has an Instrument page (NAVs, classification, identifiers) and a Holding page (lots, SIPs, sells). A bucket links to one, Holdings to the other | `InstrumentPage.tsx`, `HoldingPage.tsx` |
| **Screens do several jobs.** Cash = summary + planner + accounts + rules. Holding = stats + 3 forms swapped in place + SIP list + lots table with nested sales. Backtest = bucket picker + strategy form + saved runs + results | |
| **Paragraphs everywhere.** Every page opens with a muted paragraph; card descriptions explain algorithms (water-filling, Modified Dietz, SIP instalment dates); most inputs have a hint line under them | every page |
| **Build details leak into the UI.** Task IDs ("arrive with T1-17"), CLI commands (`just instruments`, `just navs`), data sources ("mfapi.in, with AMFI as the fallback"), "Plain arithmetic, no AI", a "Not built yet" placeholder page | `DashboardPage`, `HoldingsPage`, `InstrumentsPage`, `DataStatusPage`, `SectionPage` |
| **The dashboard has nothing to say.** Counts of buckets and tracked funds, and a getting-started list that leads to Instruments → Buckets → Backtest, not to my money | `DashboardPage.tsx` |
| **Forms push the page around.** New bucket opens a card at the top of the list; holding forms replace the action buttons; account form appears inside the table card. Deletes use the browser's `confirm()`. "Saved." appears as inline text | |
| **Noise in every row.** "AMFI 122639 · Direct · Growth" under every fund name; stocks and US listings in a mutual-fund-only phase | lists and tables |

---

## 2. Rules for every screen

These go into `CLAUDE.md` once approved, so later tasks don't drift back.

1. **One screen, one job.** If a screen needs a second heading of equal weight, it's two screens (or two tabs).
2. **No explanatory prose.** Page header = title + primary action. No subtitles, no card descriptions that explain. A term that needs a definition gets an **info icon** next to its label: one sentence, shown on hover, focus or tap.
3. **No build or roadmap talk.** No task IDs, CLI commands, data-source names, "coming soon" or placeholder pages. The nav shows only what works.
4. **Verbs on buttons, nouns on titles.** "Add transaction", not "Add a lump sum or SIP: fund name or AMFI scheme code".
5. **Small edits in a dialog, big ones on their own page.** Never an inline form that pushes content down. Optional fields sit behind "More options".
6. **Hints only for errors.** Under-field text appears when something is wrong, not by default. Formats go in placeholders ("10,000").
7. **Feedback is a toast** (saved, deleted, synced), with **Undo** where the API allows it. Destructive actions use a confirm dialog, not `window.confirm`.
8. **Empty state = icon, one short line, one button.**
9. **Numbers look like numbers.** Right-aligned, tabular figures, one table component everywhere. Row click opens the detail; row actions live in a `…` menu.
10. **Identity, not identifiers.** A fund row shows its name and plan ("Direct · Growth"). AMFI code, ISIN and friends live on the fund's Details tab.

---

## 3. Information architecture

### Before → after

| Today (7 items) | Proposed (4 items + header) |
|---|---|
| Dashboard | **Portfolio** (home): what I own, funds and cash |
| Holdings | → Portfolio (list) and the fund page (transactions) |
| Cash | accounts → Portfolio · Cash tab; planner → **Invest**; rules → **Settings** |
| Buckets | **Models** (name open, see decisions) |
| Backtest | → a tab on each model |
| Instruments | **Funds**: search and one page per fund (mutual funds only in Phase 1) |
| Data status | → header freshness indicator + Settings · Data |

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ Friday   Portfolio   Invest   Models   Funds        NAVs 24 Oct ⟳  [+ Add] ⚙ │
└──────────────────────────────────────────────────────────────────────────────┘
```

- **Top bar instead of a sidebar**: 4 items don't need a sidebar, and it frees width for tables and charts. On phones: the same 4 as a bottom tab bar, `+ Add` floats.
- **`+ Add`** (global): opens the Add transaction dialog from anywhere.
- **NAVs 24 Oct ⟳**: data freshness. Neutral when NAVs are as of the last business day, amber when older, red if the last sync failed or the backend is down (replaces the backend badge). Click to sync; failures link to Settings · Data.
- **⚙ Settings**: Invest rules, Data (NAV sync log, tracked funds, fund list status).

### Routes

| Route | Screen | Job |
|---|---|---|
| `/` | Portfolio · Funds tab | What do I own, how is it doing? |
| `/cash` | Portfolio · Cash tab | What cash do I have, and what is it for? |
| `/invest` | Invest | I have ₹X: what do I buy? |
| `/models` | Models list | Which splits do I have, which is my target? |
| `/models/new`, `/models/:id/edit` | Model editor | Build or change a split |
| `/models/:id` | Model · Overview tab | What's in it, vs my holdings |
| `/models/:id/backtest` | Model · Backtest tab | How would it have done? |
| `/funds` | Fund search | Find a fund |
| `/funds/:id` | Fund · Overview tab | NAV, returns, my position |
| `/funds/:id/transactions` | Fund · Transactions tab | My buys, SIPs and sells in this fund |
| `/funds/:id/details` | Fund · Details tab | Identifiers, classification, other plans |
| `/settings` | Settings · Invest rules / Data | Set once, rarely touched |

Old routes (`/holdings/:id`, `/instruments/:id`, `/buckets`, `/backtest/:id`, `/status`) redirect.

---

## 4. Journeys (Phase 1)

Each journey names the screens it touches and the clicks it takes. Today's count in brackets.

**J1 · First run.** Portfolio is empty → a setup checklist (not prose): ☐ Add your cash ☐ Add your funds ☐ Choose a target model. Each line is a button; done lines tick; the list disappears when all three are done. If the fund list was never downloaded, a single banner on top: "Fund list not downloaded · Download" (needs an endpoint, see decisions). [Today: Dashboard prose → Instruments → Buckets → Backtest, never reaching holdings or cash.]

**J2 · Record a purchase.** `+ Add` → fund (search) → type **Lump sum | SIP | Sell** → date, amount → Save. Toast: "₹10,000 added to Parag Parikh Flexi Cap · View". NAV and units overrides under "More options". **3 steps, no page change.** [Today: Holdings → search → navigates to fund page → "Add lump sum" → form → Save: 5 steps, 2 pages.]

**J3 · Sell.** Fund page → Transactions → `Sell` (or `+ Add` → Sell) → dialog: date, then purchases with units left and a units box each, "All" per row, running total of units → Sell. Undo in the toast.

**J4 · How am I doing?** Open the app. Portfolio shows the totals and every fund with value, weight and target weight. Click a fund → its page. [Today: no value anywhere; T1-17 fills this in, inside the new layout.]

**J5 · I have money to invest.** Invest → amount (pre-filled with investable cash) → result: emergency top-up, then a "Buy" table per fund, then the monthly transfer table if staggered. Rules are one click away (Settings · Invest rules), not on the same screen. [Today: Cash page, scroll past balances, planner is card 2 of 4.]

**J6 · Design and test a split.** Models → New model (full page) → name, funds, weights, rebalance, benchmark → Save → lands on the model → Backtest tab. "Set as target" on the model page and in the list's `…` menu; the target model wears a **Target** badge everywhere. [Today: inline card at top of Buckets; target chosen on the Cash page.]

**J7 · Look up a fund.** Funds → search → fund page. Or click any fund name anywhere: it always goes to the same page. [Today: two different pages depending on where I click.]

**J8 · Keep NAVs fresh.** Glance at the header. Amber → click → sync → toast. [Today: a whole nav item.]

---

## 5. Screens

### Portfolio (`/`, `/cash`)

```
Portfolio                                                   [Funds | Cash]
┌──────────┬──────────┬──────────┬──────────┐
│ Value    │ Invested │ Gain     │ XIRR     │   ← T1-17 fills value, gain, XIRR
└──────────┴──────────┴──────────┴──────────┘
Fund                        Units      Invested     Value    Weight  Target   ⋯
Parag Parikh Flexi Cap      1,234.567  ₹1,20,000  ₹1,45,210   38%     40%     ⋯
  Direct · Growth · SIP ₹10,000
```
- Before T1-17: Units, Invested (cost), Active SIP; Value/Weight/Target columns arrive with T1-17.
- Row `⋯`: Add purchase, Sell, Start SIP, Open fund.
- Cash tab: the accounts table (name, purpose, balance, updated) + `Add account` (dialog). Three tiles: Investable · Reserved · Emergency (with goal progress, e.g. "₹2,40,000 of ₹3,00,000"). **No planner, no settings here.**
- Removed: the "Lots" and "NAVs to" columns, the page paragraph, the search box doubling as an add button.

### Invest (`/invest`)

```
Invest
Amount  [ ₹ 1,50,000        ]  [Plan]          Target: Core 40/25/20/15 ⓘ
┌──────────────┬──────────────┬──────────────┬──────────────┐
│ Emergency    │ Into funds   │ Left as cash │ Investable   │
└──────────────┴──────────────┴──────────────┴──────────────┘
Fund                         Target   Now    Buy        After
Parag Parikh Flexi Cap        40%     36%   ₹62,000     39%
...
Monthly transfers (STP from <fund>) ⓘ
```
- One input, one result. No target set → empty state "Choose a target model" [Choose].
- Plan details ("why this fund got nothing") become info icons on the row, not a sentence under the table.
- Removed: the card description explaining water-filling; "Blank: all deployable cash" hint (the box is pre-filled instead).

### Models (`/models`, `/models/:id`)

- List: one row (or card) per model: name, **Target** badge, funds count, rebalance, benchmark. Row click → model. `…`: Set as target, Edit, Delete.
- Model page header: name, Target badge or `Set as target`, `Edit`. Tabs: **Overview** (funds and weights, benchmark; from T1-17, current vs target per fund for the target model) · **Backtest**.
- Backtest tab: the existing controls minus the bucket picker (the model is the page); saved runs in a `Saved runs` dropdown in the tab header, `Save run` next to results.
- Editor (full page): name, funds with weights and a live total, `Equal weights`, rebalance, benchmark. "Description" behind More options.
- Removed: the page paragraph, the "Funds only for now…" description, the benchmark explanation, the "Start with your current split, e.g. 40% flexi cap…" empty-state prose, the backtest results footnotes.

### Fund page (`/funds/:id`)

```
← Funds
Parag Parikh Flexi Cap Fund                       [+ Add purchase] [Sell] ⋯
Direct · Growth · Flexi Cap · Equity              NAV ₹82.4512  +0.42%  24 Oct
[Overview | Transactions | Details]
```
- **Overview**: my position (units, invested, value from T1-17), NAV chart with range presets, return stats (1Y, 3Y, 5Y, since launch, 52-week range).
- **Transactions**: SIPs (with Edit / End / Delete in `⋯`), then purchases with their sales nested; skip/edit/delete in `⋯`. Empty: "No transactions" [Add purchase].
- **Details**: identifiers, classification (with "Set my own" in a dialog), other plans and options, earlier names. This is where AMFI code, ISIN, fund house live.
- Tracking is automatic for held and model funds; "Track NAVs" only shows for funds that are neither, as a small button in the header `⋯`.
- Removed: NSE series, SEC CIK, "Last changed", "Inactive: no longer on its list, or no recent NAV" sentence (→ an `Inactive` badge with ⓘ), the NAV-history description sentence.

### Settings (`/settings`)

- **Invest rules**: target model, emergency goal, emergency fund, stagger fund, stagger from, stagger months, minimum per fund. Each label has an ⓘ; no hint lines. One `Save`.
- **Data**: last sync (time, NAVs added, failures), `Sync now`, tracked funds table, fund list status (and `Download` if the endpoint is added).

### Add transaction dialog (global)

```
Add transaction                                         ✕
Fund     [ Search fund…                               ]
Type     [ Lump sum | SIP | Sell ]
Date     [ 25-10-2026 ]   Amount  [ ₹ 10,000 ]
▸ More options   (NAV, units from statement, note)
                                     [Cancel] [Save]
```
- SIP: amount, day, start, end (optional). Sell: date, then purchases with units left.
- Opened from a fund page or row menu, the fund is pre-filled.

---

## 6. Component kit

`radix-ui` is already a dependency, so everything below is shadcn components added by hand (the registry is blocked in the build environment, as in T1-01). No new libraries except possibly `sonner` for toasts (see decisions).

| Component | Replaces |
|---|---|
| `PageHeader` (title, back link, actions, tabs) | the `<h1>` + paragraph block on every page |
| `InfoTip` (ⓘ, Tooltip on hover/focus, Popover on tap) | every hint line and card description |
| `Dialog`, `AlertDialog` | inline forms, `window.confirm` |
| `Tabs` (route-backed) | stacked cards on one page |
| `DropdownMenu` (row `⋯`) | 2–3 ghost buttons per row |
| `DataTable` (plain, no library) | about 10 hand-written tables |
| `EmptyState` | empty-state cards with prose |
| `Toast` | "Saved." text, success lines |
| `Skeleton` | "Loading…" text |
| `Field` (label, ⓘ, control, error) | 3 copies of `Field` in pages |

---

## 7. Copy

### Remove

Every page subtitle; every `CardDescription` that explains; all task IDs; `just …` commands; "mfapi.in", "AMFI as the fallback"; "Plain arithmetic, no AI"; `SectionPage` ("Not built yet"); the Dashboard getting-started prose; backtest footnotes ("CAGR and drawdown measure the funds themselves…", "Money-weighted return over the window (Modified Dietz)…").

### Info tips (the only explanations left)

| Label | Tip |
|---|---|
| Investable / Reserved / Emergency | What the plan may use / Set aside, never invested / Topped up first, never invested |
| Emergency fund | Its value counts towards the emergency goal |
| Stagger from | Amounts this big are moved in monthly over the stagger months |
| Minimum per fund | Smaller amounts are skipped and shared out |
| NAV, Units (More options) | Leave blank to use the NAV on that date / amount ÷ NAV |
| XIRR · CAGR · Max drawdown · Sharpe · Sortino | One-line definitions |
| Return in window | Money in or out isn't counted as gain |
| Benchmark | The same money, on the same dates, in this fund |
| Target | The model new cash moves you towards |

### Words (candidates, see decisions)

| Today | Proposed | Why |
|---|---|---|
| Bucket | Model | It's a model portfolio; "bucket" also reads as a cash bucket |
| Lot | Purchase | What I actually did; "lot" is bookkeeping |
| Earmark | Purpose | Plain word for the same thing |
| Deployable | Investable | Same |
| Plan settings | Invest rules | "Plan" already means Direct/Regular |
| Cash plan / "I have ₹X" | Invest | The verb I came to do |
| Instruments | Funds | Phase 1 is funds only |

---

## 8. Rollout

Two tasks, both before T1-17 so the portfolio view is built once, in its final place.

1. **T1-21 · UI kit and copy clean-up.** Components in section 6, rules in section 2 into `CLAUDE.md`, every screen stripped of prose and build talk, info tips in. Same routes and screens. Small, mechanical, quick to review.
2. **T1-22 · Journeys: new navigation and screens.** Top bar, header freshness indicator, global Add transaction dialog, Portfolio (Funds | Cash), Invest, Models with Backtest tab and target badge, one fund page, Settings, redirects, setup checklist.
3. **T1-17** then fills Portfolio and the model Overview with value, P&L, XIRR and drift.

No backend logic changes, apart from the optional fund-list download endpoint.

---

## 9. Decisions to make

| # | Question | Candidates | Recommendation |
|---|---|---|---|
| 1 | Screen rules (section 2) into `CLAUDE.md` | yes / edit first | Yes |
| 2 | Navigation | top bar with 4 items (A) · keep sidebar with 4 items (B) | A |
| 3 | Name for buckets | Model · Model portfolio · Split · keep Bucket | Model |
| 4 | Name for lots in the UI | Purchase · Transaction · keep Lot | Purchase (code keeps `lot`) |
| 5 | Earmark and Deployable | Purpose + Investable · keep | Purpose + Investable |
| 6 | Where cash accounts live | Portfolio · Cash tab · own nav item | Portfolio tab |
| 7 | Toasts | Radix Toast (no new dep) · sonner | sonner (shadcn's default; simpler API) |
| 8 | Fund list download from the UI | new `POST /instruments/refresh` + button in Settings · Data · keep CLI only | Add it: first run shouldn't need a terminal |
| 9 | Stocks and US listings in fund search | hide in Phase 1 (search `kind=mutual_fund` everywhere) · keep | Hide |
| 10 | Order | T1-21 → T1-22 → T1-17 · fold into T1-17 | T1-21 → T1-22 → T1-17 |

---

## 10. As built

Where T1-21 and T1-22 differ from the plan above:

- **Portfolio's tiles and value columns came with T1-17** (D-070, D-071): Value, Invested, Gain and XIRR, with the benchmark's figures as the second line; the table adds Value, Gain, Weight and Target, and active SIPs moved into the fund's second line. Allocation bars sit under the table; drift is on the target model's Overview.
- **Models is a table**, not cards: name with the Target badge, funds, rebalance, benchmark, and a `⋯` menu (Set as target, Backtest, Edit, Delete).
- **"Track NAVs" stays in the fund's NAV history section** (as an empty state) instead of the header `⋯`; the header has Add lump sum, Sell (when there are units) and `⋯` → Start a SIP.
- **Dates in the transaction dialogs start at the fund's latest NAV date**, not today: today has no NAV until the evening, nor on weekends, so a blank NAV couldn't be looked up.
- **Purchases are listed newest first.**
- **Funds** lists the funds Friday follows under the search (held, in a model, a benchmark, or tracked by hand).
- **The editor for a new model saves to its Backtest tab**; editing an existing one returns to the model.

