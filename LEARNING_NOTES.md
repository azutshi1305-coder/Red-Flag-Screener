# Learning Notes

After each step, write 3-5 lines IN MY OWN WORDS: what I did, why, and what I learned.
This is my interview prep sheet.

## Setup

**Tools I installed and why**
- Python 3.14: the language the project is written in. Installed through the Python install manager.
- VS Code: where I write, run and view code. Added the Python, Jupyter and Claude Code extensions.
- Git: tracks every version of my project so I can go back if something breaks,
  and uploads my code to GitHub where recruiters can see it.
- Claude Code: an AI coding assistant that works inside my project folder. It writes and
  runs code when I ask, but asks my permission first. I make the decisions and check its work.

**Virtual environment (.venv)**
- A private set of Python libraries just for this project, so different projects
  don't clash over library versions.
- Created with `python -m venv .venv`, activated with `.venv\Scripts\activate`.
- `(.venv)` at the start of the terminal line means it's active. Always check for it.

**Libraries and requirements.txt**
- Installed pandas (tables), numpy (math), yfinance (financial data), openpyxl (Excel),
  matplotlib (charts), jupyter (notebooks), pytest (testing calculations).
- `pip freeze > requirements.txt` records exact versions, so anyone can recreate my setup
  with `pip install -r requirements.txt`. This makes the project reproducible.

**Project structure**
- Separate folders for raw data, processed data, code (src), notebooks, tests, outputs
  and reports. Raw data is never edited, so I can always trace results back to the source.

**.gitignore**
- Tells Git what NOT to upload: .venv (large and recreatable), data/raw (downloaded data
  I don't own; my script can re-download it), and temporary Python/Jupyter files.

**CLAUDE.md**
- A briefing file Claude Code reads at the start of every session: project goal, my rules
  (explain everything, never invent data, ask before design decisions).

**Problems I hit and how I fixed them**
- `>>` in PowerShell: the command was incomplete (a pasted hidden character). Fixed by
  cancelling with Ctrl+C and typing the command manually.
- `git` not recognized: Git wasn't installed. Installed it with winget.
- "Running scripts is disabled": Windows blocks scripts by default. Fixed with
  `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, which allows local scripts.
- requirements.txt saved as UTF-16: PowerShell's default encoding. Re-saved as UTF-8 in VS Code
  so GitHub displays it properly.
  ## Steps 1–5 (summary)

### Step 1: Choosing companies
- Used the official Nifty Pharma index (20 companies) rather than picking companies myself, so the selection is objective.
- One sector only, because ratios are only comparable between similar businesses (e.g. inventory levels differ hugely across sectors).
- Excluded banks/NBFCs: Altman, Piotroski and Beneish were designed for non-financial companies.
- Tickers = NSE symbol + ".NS" (Yahoo Finance's code for NSE). Checked all 20 with a script: 20/20 valid.

### Step 2: Downloading data
- Script downloads balance sheet, income statement and cash flow for each company from Yahoo Finance: 60/60 files.
- About 4 complete years (FY2023–FY2026). Values in rupees, so later converted to Rs crore.
- Raw files are never edited and are gitignored; anyone can re-download them by running the script.

### Step 3: Exploring data and making decisions
- Checked 20 required fields for each company over 3 years: 14/20 companies complete.
- Verified every gap against Screener.in (consolidated figures) before deciding:
  - Abbott, Divi's, Ajanta: Long-Term Debt missing → used Total Debt (matched Screener exactly). Abbott's "debt" only appears from FY2020: that's Ind AS 116 lease liabilities, not bank loans.
  - Dr Reddy's FY2024 depreciation: filled manually (1,470 cr, Screener).
  - Torrent retained earnings FY2025–26: rolled forward (RE last year + net income − dividends), because Screener's "Reserves" is a different line item.
  - Aurobindo SG&A FY2025: Beneish SGAI set to 1.0 (neutral) instead of inventing a number.
- Found that Torrent's borrowings jumped from 3,202 to 15,026 cr in FY2026 (likely a debt-funded acquisition), so its scores need careful interpretation.
- Lesson: an AI summary said "1 of 3 years missing" when it was actually 2 of 3. Always check the actual numbers.

### Step 4: Cleaning data
- Built one "tidy" table: one row per company per year, one column per field, all in Rs crore.
- Applied all Step 3 decisions, with a data_notes column recording each adjustment.
- Balance-sheet check (assets = liabilities + equity) passed for every row where it could be run.
- Kept all years in the clean table; scoring will use FY2023–FY2026 (main year FY2026).

### Step 5: Hand calculation (Cipla, FY2026)
- Altman Z'' = 10.18 → Safe (equity is 4x liabilities, strongly profitable).
- Piotroski F = 4 → average. A very healthy company, but FY2026 momentum weakened: ROA fell from 16% to 10%, margins and asset turnover fell.
- Beneish M = −2.40 → unlikely manipulator (threshold −1.78); cash flow exceeds profit (negative TATA).
- Key insight: Altman measures the LEVEL of health, Piotroski measures the DIRECTION of change, so a strong company can have a weak F-score.
- Design decisions: Piotroski test 5 gives a point to companies with zero debt in both years; test 7 allows share increases under 1% (ESOPs aren't equity raises).
- Found a bug in my own spreadsheet (the Beneish verdict pointed at the wrong cell). Lesson: check results against expectations.
- This spreadsheet is the answer key for testing the Python code later.