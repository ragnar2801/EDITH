# Friday

A personal portfolio tracker and analyst, running locally on one Windows laptop.

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

This installs Python 3.14 (via uv) and all packages, creates the database in `%LOCALAPPDATA%\Friday\data` and builds the UI.

## Use it

```powershell
just run
```

Open <http://localhost:8000>. Friday only listens on this laptop, not on your network.

On first run, Portfolio shows **Fund list not downloaded · Download**: press it (or run `just instruments`, which also fetches the NSE and US lists). **Settings · Data · Download lists** refreshes them later. If a site blocks the download, save the files from a browser into a folder and run `just instruments --from-dir C:\path\to\folder` (file names: `EQUITY_L.csv`, `eq_etfseclist.csv`, `symbolchange.csv`, `namechange.csv`, `NAVAll.txt`, `SchemeData.csv` (AMFI's scheme master, which names the plan and option of funds `NAVAll.txt` leaves blank), `nasdaqlisted.txt`, `otherlisted.txt`).

Then follow the checklist on *Portfolio*. The app has four screens, one job each:

- **Portfolio**: the funds you own, with their value, realised and unrealised gain and XIRR next to the same money in the Nifty 50 index fund, your allocation, and a *Cash* tab with your accounts. **+ Add** (top bar, or the round button on a phone) records a lump sum, a SIP or a sale from anywhere.
- **Invest**: type an amount (it starts at your investable cash) and see what to buy towards your target model.
- **Models**: your target splits. Open one for its funds and a *Backtest* tab (lump sum, SIP, SWP or your own timeline vs the benchmark); **Set as target** makes it the split Invest works towards.
- **Funds**: find any mutual fund; every fund has one page with its NAVs, your transactions and its details.

The NAV date in the top bar turns amber when NAVs are behind; click it to sync, or run:

```powershell
just navs
```

*Settings* holds the invest rules (emergency goal, staggering, minimum per fund) and the data status.

You can also track funds from the terminal: `uv run --project backend friday navs track 122639 120716` (AMFI scheme codes).

## Purchases from FM on your phone

Friday keeps a read-only copy of the fund purchases and sales you record in the FM app. FM's **Sync to Friday** sends every investment purchase with its sales (nothing else) over your home Wi-Fi; each sync replaces the FM purchases here, and purchases you entered in Friday stay. Change FM's purchases in FM.

1. `just run`. The first time, Windows asks whether Python may use the network: allow it on **private** networks only.
2. In FM on the phone, open **Backup & sync › Sync to Friday** and enter the address, port and token from Friday's **Settings · Data · Phone sync**. Press **Test**, then **Sync to Friday**.

## Commands

| Command | What it does |
|---------|--------------|
| `just run` | Rebuild the UI and run Friday for daily use at <http://localhost:8000> |
| `just dev` | Develop with hot reload on made-up data: UI at <http://localhost:5173>, API on `:8001` |
| `just demo` | Rebuild the made-up database `just dev` uses |
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

Settings can be overridden in a `.env` file (see `.env.example`). Your data and logs live in `%LOCALAPPDATA%\Friday`, outside the repo, so nothing working on the code comes across them. `just dev` runs on a made-up database in `dev/` instead (real funds and NAVs, invented holdings and cash), so it can run next to the real Friday.
