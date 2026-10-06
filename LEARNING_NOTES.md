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

## Steps 6–9 (summary)

### Step 6: Ratios
- 11 ratios for all companies; previous-year values looked up per company with a check that years are consecutive (so a missing year never silently uses data from two years back).
- First pytest tests: code matched my Excel hand calculation for Cipla to 4 decimals.
- Decisions: cash conversion = NaN when net income <= 0 (the ratio's sign becomes misleading with losses); interest coverage = NaN when there's no interest expense.

### Step 7: The three scores in code
- Altman Z'', Piotroski F and Beneish M for all 20 companies; tests confirm Cipla matches my Excel (Z''=10.18, F=4, M=-2.40).
- Fixed a "No module named src" error: scripts that import other scripts must be run from the project root.
- Decomposed Beneish flags into each index's contribution vs the sector median:
  - Abbott (M=-1.66, flagged): driven by AQI; current and non-current assets moved in opposite directions while their total grew steadily, so likely deposits reclassified by maturity, i.e. a probable false positive.
  - Torrent (-1.78): AQI + DSRI from a debt-funded acquisition (acquisition artifact).
  - Ajanta (-1.80): DSRI + TATA. Verified on Screener: receivable days 93 -> 124, CFO/operating profit 117% -> 59%, borrowings 47 -> 260 cr. Genuine working-capital deterioration (partly a reversal of an unusually strong FY2025).
- Lesson: a hard cutoff misleads; the "flagged" company (Abbott) was likely fine, while an unflagged one (Ajanta) was the real concern.

### Step 8: Red flags and risk score
- Five custom flags (receivables vs sales, cash conversion 2 of 3 years, inventory build-up, debt stress, low interest cover) plus a combined risk score and Low / Watch / High bands.
- Added a Beneish "Watch" zone (-2.22 to -1.78) because of the Ajanta vs Abbott lesson.
- Materiality rule for debt stress (only if debt > 10% of equity) to avoid flagging trivial debt changes.
- Changed the inventory flag to be relative to the sector median: the median company added 13.5 inventory days, so a fixed threshold flagged 9 of 20 companies for a sector-wide trend. Decided on logic, not to get a preferred ranking (avoiding data snooping).
- Investigated Zydus: FY2026 acquisitions of Amplitude Surgical (EUR 256.8m) and Agenus' biologics facilities; borrowings 3,213 -> 12,496 cr. Receivable/inventory flags are partly consolidation artifacts, but the leverage increase is real.
- Analyst notes file adds my qualitative judgment next to the scores.

### Step 9: Charts
- Seven charts in a consistent research-report style with headline titles that state the conclusion.
- Design lessons: bars starting at 0 misled for negative M-scores (switched to a dot plot); dual-axis charts are misleading (split into two panels); color is never the only signal; quadrant labels must match the actual score bands.
- Key findings:
  - 3 of 20 companies screen High risk (Piramal, Zydus, Torrent); two of them because of acquisitions.
  - Piramal is the only company both financially weak (Altman Grey) and weakening (F=3), with interest cover of just 0.48x. Its debt has been flat for years; the problem is earnings too low to carry it.
  - Only Abbott crosses the Beneish threshold, and the driver looks benign.
  - Six companies trigger no red flags (Mankind, Sai Life, Lupin, IPCA, Sun Pharma, Cipla).
- Big lesson: a screener can't tell acquisition-driven growth from distress. Analyst judgment is essential.