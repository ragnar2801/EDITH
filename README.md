# Friday

A personal portfolio tracker and analyst, running locally on one Windows laptop. Being built for **Indian mutual funds first** (D-043); stocks and US holdings come later.
Design and plan: [`agents.md`](agents.md) · overview: [`docs/architecture.md`](docs/architecture.md) · phases: [`docs/phases.md`](docs/phases.md) · tasks: [`docs/tasks/`](docs/tasks/README.md)

## Set up on Windows (once)

Install the tools with `winget` in a terminal:

```powershell
winget install Git.Git
winget install astral-sh.uv
winget install OpenJS.NodeJS.LTS
winget install Casey.Just
```

Open a new terminal so the tools are on `PATH`, then in the repo folder:

```powershell
just setup
```

This installs Python 3.14 (via uv) and all packages, creates `data/friday.db` and builds the UI.

## Use it

```powershell
just run
```

Open <http://localhost:8000>. Friday only listens on this laptop, not on your network.

Load the instrument lists once, and again whenever you want new listings and funds (takes under a minute):

```powershell
just instruments
```

This downloads the NSE, AMFI and Nasdaq Trader lists into `data/sources/` and updates Friday's instruments. If a site blocks the download, save the files from a browser into a folder and run `just instruments --from-dir C:\path\to\folder` (file names: `EQUITY_L.csv`, `eq_etfseclist.csv`, `symbolchange.csv`, `namechange.csv`, `NAVAll.txt`, `nasdaqlisted.txt`, `otherlisted.txt`).

Then, for your funds:

1. **Find a fund** in *Instruments* (name or AMFI scheme code) and press **Track NAVs** to download its whole NAV history.
2. **Build a bucket** in *Buckets*: your funds with target weights that add up to 100%, a rebalance policy and a benchmark (by default the UTI Nifty 50 Index Fund). Saving it downloads the NAVs of its funds.
3. **Backtest it** in *Backtest*: a lump sum, a SIP, an SWP or your own timeline of buys and sells, next to the same money in the benchmark. Drag across the chart to measure any window; save runs you want to keep.
4. **Keep NAVs up to date** with **Sync all NAVs** on the *Data status* page, or:

```powershell
just navs
```

You can also track funds from the terminal: `uv run --project backend friday navs track 122639 120716` (AMFI scheme codes).

## Commands

| Command | What it does |
|---------|--------------|
| `just run` | Run Friday for daily use at <http://localhost:8000> |
| `just dev` | Develop with hot reload: UI at <http://localhost:5173>, API on `:8000` |
| `just test` | Backend (pytest) and frontend (Vitest) tests |
| `just lint` | Lint, formatting and type checks |
| `just fmt` | Fix formatting |
| `just build` | Rebuild the UI that `just run` serves |
| `just api` | Regenerate the frontend's API types after changing an endpoint |
| `just migrate` | Upgrade the database (`just run` also does this on start) |
| `just revision "msg"` | Create a database migration from model changes |
| `just instruments` | Download the stock, ETF and fund lists and update instruments (`--source nse amfi us`, `--from-dir DIR`) |
| `just navs` | Download missing NAVs for every tracked fund, up to today (`--fund 122639` for one) |
| `just smoke` | Start a real server with a throwaway database and check it answers |

Settings can be overridden in a `.env` file (see `.env.example`). Data lives in `data/`, logs in `logs/`; neither is committed.
