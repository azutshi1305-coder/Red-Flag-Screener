# Data Decisions

This file records design decisions made about data gaps found in Step 3
(`notebooks/01_explore.ipynb`, `data/processed/field_availability.csv`).
These decisions are **recorded here only** — they are implemented in Step 4.

## Decisions table

| Company | Field | Years missing | Decision | Reason/Source |`
|---|---|---|---|---|
| ABBOTINDIA.NS | Long Term Debt | All years in the 3-year window (FY2024, FY2025, FY2026) | Use Total Debt in place of Long Term Debt, for all years | Screener.in borrowings match Yahoo's Total Debt exactly (₹172 / 197 crore). Debt appears only from FY2020, consistent with Ind AS 116 lease liabilities, not bank loans. |
| DIVISLAB.NS | Long Term Debt | All years in the 3-year window (FY2024, FY2025, FY2026) | Use Total Debt in place of Long Term Debt, for all years | Screener.in borrowings match Yahoo's Total Debt exactly (₹4 / 7 crore). |
| AJANTPHARM.NS | Long Term Debt | FY2025, FY2026 (2 of 3 years) | Use Total Debt in place of Long Term Debt, for all years (including FY2024), so the field is defined consistently within the company | Screener.in borrowings match Yahoo's Total Debt exactly (₹35 / 47 / 260 crore). |
| AUROPHARMA.NS | Selling General And Administration (SG&A) | FY2025 | Set Beneish M-score SGAI = 1.0 (neutral) for FY2025 and FY2026; flag the company in output | No reliable Yahoo SG&A figure for FY2025; forcing the index to "unchanged" avoids inventing a number. |
| DRREDDY.NS | Depreciation | FY2024 | Manual value: ₹1,470 crore | Screener.in, consolidated P&L, March 2024. |
| TORNTPHARM.NS | Retained Earnings | FY2025, FY2026 (2 of 3 years) | Roll forward: RE(t) = RE(t-1) + Net Income(t) − Dividends Paid(t), using Yahoo figures throughout | Screener.in "Reserves" (₹6,687 crore, FY2024) does not match Yahoo's Retained Earnings (₹3,942 crore, FY2024), so the Screener figure is rejected in favour of an internally consistent, Yahoo-only roll-forward. |

## Verification against Screener.in

- ABBOTINDIA.NS: Screener.in borrowings = Yahoo Total Debt, ₹197 crore (FY2025) and ₹172 crore (FY2026).
- DIVISLAB.NS: Screener.in borrowings = Yahoo Total Debt, ₹4 crore (FY2025) and ₹7 crore (FY2026).
- AJANTPHARM.NS: Screener.in borrowings = Yahoo Total Debt, ₹35 crore (FY2024), ₹47 crore (FY2025), ₹260 crore (FY2026).
- TORNTPHARM.NS: Screener.in "Reserves" of ₹6,687 crore (FY2024) does **not** match Yahoo's Retained Earnings of ₹3,942 crore (FY2024) — these are different accounting line items, so Screener's figure is not used for the Retained Earnings roll-forward.
- DRREDDY.NS: Depreciation of ₹1,470 crore (FY2024) taken directly from Screener.in's consolidated P&L, March 2024.

## Notes for analysis

- Torrent Pharmaceuticals' (TORNTPHARM.NS) borrowings rose from ₹3,202 crore (FY2025) to ₹15,026 crore (FY2026) per Screener.in, likely due to a debt-funded acquisition. Its FY2026 scores (Altman Z'', Piotroski F, Beneish M) must be interpreted with this leverage jump in mind rather than taken at face value as organic deterioration.

## Step 4: cleaning

- **Years kept:** `data/processed/financials_clean.csv` keeps every fiscal year Yahoo reports, including FY2022, so it is a complete record. Scoring uses only FY2023–FY2026. Main scores are for FY2026, with FY2025 as a secondary year.
- **Dividend gaps left as NaN:** blank `dividends_paid` values (e.g. Mankind FY2023–FY2025, Wockpharma, Gland, Sai Life) are not filled with zero or estimated. Dividends are used only in the Torrent retained-earnings roll-forward.
- **Added Yahoo mappings:** `cost_of_revenue` uses the Yahoo row "Cost Of Revenue" (income statement). `dividends_paid` uses "Cash Dividends Paid" (cash flow), with "Common Stock Dividend Paid" as fallback. Neither was mapped in Step 3.

## Step 6: ratios

- **FY2022 kept in `ratios.csv`:** all fiscal years from the clean table are kept. Scoring uses FY2023–FY2026 only.
- **ROA and ROE keep their sign:** a loss gives a negative ROA or ROE, which is a real value.
- **Cash conversion is NaN when net income is zero or negative:** a negative ratio would look healthy when it actually reflects a loss. Decided by the project owner.
- **Interest coverage is NaN when interest expense is zero:** coverage is not meaningful without interest. Step 8's low-interest-coverage flag must treat NaN as "no flag".
- **Previous-year values need consecutive years:** ROA and asset turnover use the prior year's total assets only when the prior row is exactly one fiscal year earlier for the same company. A gap in years gives NaN, never a value from a different year or company.

## Step 7: scores

- **Piotroski test 5 debt-free rule:** a company with long-term debt of zero in both years passes test 5, even when the leverage ratio cannot be computed. A debt-free company should not be penalised for a leverage ratio that is zero before and after.
- **Piotroski test 7 tolerance:** shares outstanding count as "no new shares" if they rise by less than 1% (`shares_t <= shares_(t-1) * 1.01`). Small increases are usually employee share schemes, not equity raises.
- **Piotroski NaN handling:** a test whose inputs are missing is NaN, never 0, so missing data is not counted as a failed test. F is the sum of the available tests, and `piotroski_tests_available` records how many there were. The band is still shown, so read it together with that count.
- **Beneish neutral values:** an index that cannot be computed is set to its neutral value and listed in `score_notes`. The seven ratio indices (DSRI, GMI, AQI, SGI, DEPI, SGAI, LVGI) use 1.0, meaning no change. TATA is a difference, not a ratio, so its neutral value is 0.0.
- **AUROPHARMA SG&A:** FY2025 SG&A is missing, so SGAI is neutral for FY2025. FY2026 SGAI also needs FY2025 SG&A, so it is neutral too. This matches the Step 3 row above.

## Step 8: flags and risk score

- **F1 receivables outpacing sales:** flagged when receivables growth exceeds revenue growth by more than 10 percentage points (FY2026 vs FY2025).
- **F2 weak cash conversion:** compares raw operating cash flow with net income, not the cash-conversion ratio, so loss-making years are handled directly. Flagged when at least 2 of FY2024, FY2025 and FY2026 have cash flow below net income. If missing years could still decide the flag, it is NaN; if they cannot, it is 0.
- **F3 inventory buildup (relative rule):** flagged when a company's change in inventory days (FY2026 vs FY2025) is more than 15 days above the sector median change for the same two years. Originally a fixed +15 days against the company's own prior year. The sector median change was +13.46 days (average +16.20), showing a sector-wide inventory build-up, so the fixed rule flagged companies for following the shared trend rather than deviating from peers. The relative rule reduced F3 flags from 9 companies to 6, and it recomputes the median from the data each run, so it adapts automatically if the sector's trend shifts in a future year.
- **F4 debt stress:** flagged only when total debt rose, interest coverage fell, and total debt is above 10% of total equity in FY2026. The 10% rule is a materiality threshold, so small borrowings cannot trigger the flag. If interest coverage is NaN in either year, F4 = 0.
- **F5 low interest cover:** flagged when interest coverage is below 1.5. NaN coverage (no interest expense) is 0, not flagged.
- **Beneish zones:** "Likely" when M > -1.78; "Watch" when -2.22 < M <= -1.78; "Unlikely" when M <= -2.22. The Watch zone exists because Ajanta (M = -1.80) and Abbott (M = -1.66) sit close to the -1.78 cut-off, and the single cut-off gives a flag that depends on a rounding-size difference.
- **Risk score:** Altman Distress +2, Altman Grey +1; Beneish Likely +2, Watch +1; Piotroski F <= 3 +1; each custom flag +1. Missing flags add nothing. Bands: 0-1 "Low", 2-3 "Watch", 4 or more "High".
- **Ties:** companies with the same risk score are ordered by lower Altman Z'' first (more distressed first).
- **Analyst notes:** `data/analyst_notes.csv` holds the project owner's notes, joined unchanged. The Ajanta note originally quoted figures that did not match the cleaned data; this was resolved by rewriting the note to use the project's own data (receivable days 94 -> 125, CFO/EBIT 96% -> 38%), cross-checked against Screener.in's receivables and sales growth figures.