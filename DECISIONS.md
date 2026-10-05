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