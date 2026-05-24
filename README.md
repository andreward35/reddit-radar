# 📡 Reddit Stock Radar

A daily stock intelligence report with three sections:

| Section | Source | Cadence |
|---|---|---|
| **Reddit Trending Picks** | r/wallstreetbets, r/smallstreetbets, r/stocks, r/investing, r/pennystocks, r/options | Daily |
| **Executive Branch Policy Trades** | U.S. Office of Government Ethics (OGE) Form 278-T filings | Rolling 7-day window |
| **Congressional STOCK Act Filings** | House & Senate periodic transaction reports | Rolling 14-day window, new filings only |

Runs automatically every weekday at 9:30 AM ET via GitHub Actions. Output is a self-contained HTML dashboard published to GitHub Pages.

---

## Setup (5 minutes)

### 1. Create a GitHub repo

- Go to [github.com/new](https://github.com/new)
- Name it `reddit-radar`
- Set to **Public** (required for free GitHub Pages)
- Upload `report.py` and `.github/workflows/daily_report.yml` (preserve the folder structure)

### 2. Add your Anthropic API key

- Repo → **Settings → Secrets and variables → Actions → New repository secret**
- Name: `ANTHROPIC_API_KEY`
- Value: your key from [console.anthropic.com](https://console.anthropic.com)

### 3. Enable GitHub Pages

- Repo → **Settings → Pages**
- Source: **Deploy from a branch** · Branch: `main` · Folder: `/reports`
- Save

Your report URL: `https://YOUR_USERNAME.github.io/reddit-radar/latest.html`

### 4. Test it

- **Actions** tab → **Daily Reddit Stock Radar** → **Run workflow**
- Wait ~2–3 minutes for all three API sections to complete

---

## Schedule

Runs at **9:30 AM Eastern (14:30 UTC) Monday–Friday**.

To change, edit the cron line in `.github/workflows/daily_report.yml`:

```yaml
- cron: "30 14 * * 1-5"   # 9:30 AM ET weekdays
- cron: "0 14 * * 1-5"    # 9:00 AM ET weekdays
- cron: "30 14 * * *"     # 9:30 AM ET every day
```

Use [crontab.guru](https://crontab.guru) for custom schedules.

---

## File structure

```
reddit-radar/
├── report.py                        # Main script (three sections)
├── .github/
│   └── workflows/
│       └── daily_report.yml         # GitHub Actions schedule
└── reports/
    ├── latest.html                  # Always the most recent report
    ├── 2026-05-24.html              # Archived daily reports (last 7 shown)
    └── ...
```

---

## Report sections

### 💬 Reddit Trending Picks
6–9 stocks with the most discussion volume across major Reddit finance communities. Each card shows sentiment, mention count, bull/bear case, catalysts, and analyst price target.

### 🏛 Executive Branch Policy Trades
Picks cross-referenced from OGE Form 278-T public disclosures filed by the President and cabinet. Each card documents the specific policy action that overlaps with the disclosed holding, filing date, conviction level, and analyst consensus target.

### 📋 Congressional STOCK Act Filings
New periodic transaction reports filed in the last 14 days by members of Congress, with emphasis on members sitting on committees with direct industry oversight (Armed Services, Finance, Banking, Intelligence, Commerce, Energy). Shows member name, committee role, trade date vs. filing date, amount range, and committee activity overlap.

---

## Costs

| | Cost |
|---|---|
| GitHub Actions | Free (uses ~3 min/day of the 2,000 free minutes) |
| Anthropic API | ~$0.05–0.10/day (3 calls with web search) |
| GitHub Pages | Free |

---

## Disclaimer

All government disclosure data is sourced from public OGE and STOCK Act filings.
This report is for informational purposes only. Nothing here constitutes financial advice.
