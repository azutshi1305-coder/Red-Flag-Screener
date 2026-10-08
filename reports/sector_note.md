# Nifty Pharma Financial Red-Flag Screen, FY2026
## Three of 20 companies screen High risk, two of them because of acquisitions
Annapurna Zutshi | October 2026 | Data: Yahoo Finance (consolidated), verified against Screener.in

## Summary
I screened all 20 Nifty Pharma companies for financial distress and earnings-quality risk using three established models (Altman Z'', Piotroski F-score and Beneish M-score) plus five custom red flags. The sector is financially healthy overall: 17 of 20 companies are in Altman's Safe zone and none are in Distress. Three companies screen High risk:
- Piramal Pharma: the only genuine financial-stress case. EBIT covers just 0.48x its interest cost.
- Zydus Lifesciences and Torrent Pharma: flagged mainly because of large, debt-funded acquisitions in FY2026. Many of their flags are consolidation effects, but their leverage increase is real.
The key lesson: a screener cannot tell acquisition-driven growth from distress. Every flag needs to be investigated before it is believed.

[CHART: 00_sector_summary.png]

## Methodology
- Universe: the 20 Nifty Pharma constituents; FY2026 (year ending 31 March 2026), compared with FY2025.
- Altman Z'' (non-manufacturing version) measures financial health: Safe above 2.6, Grey 1.1-2.6, Distress below 1.1.
- Piotroski F-score (0-9) measures whether fundamentals are improving. Adapted so debt-free companies are not penalised and share increases under 1% (employee stock options) do not count as equity raises.
- Beneish M-score flags possible earnings manipulation: Likely above -1.78, with a Watch zone from -2.22 to -1.78 so borderline cases are not missed.
- Five custom flags: receivables growing faster than sales, weak cash conversion, inventory build-up (relative to the sector median, since the median company added 13.5 inventory days), debt stress, and low interest cover.
- Flags combine into a risk score (Low 0-1, Watch 2-3, High 4+). The code is tested against a manual Excel calculation, and every data gap and decision is documented.

## Sector overview
The sector's balance sheets are strong: the median Altman Z'' is 6.1. Only Torrent (1.39), Piramal (1.95) and Biocon (2.51) fall in the Grey zone. Health and momentum are different things: Cipla has one of the strongest balance sheets (Z'' 10.2) but scores only 4 on Piotroski, because ROA fell from 16.1% to 10.4% in FY2026. At the other end, Laurus, Glenmark, Lupin, IPCA and Gland pass all nine Piotroski tests. Six companies trigger no red flags at all: Mankind, Sai Life, Lupin, IPCA, Sun Pharma and Cipla.

[CHART: 04_altman_vs_piotroski.png]

## Case studies
[TABLE: case_study_summary]

**1. Piramal Pharma: genuine financial stress (risk score 5, High).** Piramal is the only company that is both financially weak (Altman Grey) and weakening (F = 3). Its debt has been roughly flat at Rs 4,900-5,700 crore, so the problem is not new borrowing: EBIT now covers only 0.48x its interest cost (down from 1.99x in FY2025), and ROA is -2.1%. Inventory days also rose by 76.
View: the most concerning name in the screen.

**2. Zydus Lifesciences: acquisition-driven (risk score 5, High).** Zydus is Safe on Altman (4.44) but triggered four custom flags. In FY2026 it acquired 85.6% of Amplitude Surgical (France, EUR 256.8m) and Agenus's biologics manufacturing facilities (USA). Borrowings rose from Rs 3,213 to Rs 12,496 crore and fixed assets from Rs 13,134 to Rs 24,106 crore. Consolidating acquired receivables and inventory with only part-year sales inflates those flags.
View: partly an artifact, but debt/equity rising from 0.13 to 0.46 is a real change to monitor; the two known deals may not explain the whole increase.

**3. Torrent Pharma: acquisition-driven (risk score 4, High).** Torrent has the lowest Altman score (1.39) and sits on the Beneish threshold (-1.78). In January 2026 it completed the acquisition of a 46.39% stake in JB Chemicals & Pharmaceuticals, funded partly with debt: borrowings rose from Rs 3,202 to Rs 15,026 crore. New goodwill raises Beneish's asset-quality index (AQI 1.82), and consolidating JB's receivables raises DSRI (1.34).
View: an acquisition artifact rather than manipulation, but debt/equity of 1.79 is now the highest in the sector.

**4. Ajanta Pharma: working-capital deterioration (risk score 3, Watch).** Ajanta is not technically flagged by Beneish (-1.80), yet it shows the clearest earnings-quality warning: receivables grew 57% against sales growth of 18%, receivable days rose from 94 to 125 (a five-year high), cash from operations fell from Rs 1,157 to Rs 529 crore, and borrowings rose from Rs 47 to Rs 260 crore. Part of this reverses unusually strong FY2025 collections.
View: genuine deterioration worth monitoring; not evidence of manipulation.

**5. Abbott India: likely false positive (risk score 3, Watch).** Abbott is the only company above the Beneish threshold (-1.66), but the score is driven almost entirely by the asset-quality index (AQI 2.72). Current assets fell (Rs 4,763 to Rs 3,771 crore) while non-current assets rose (Rs 803 to Rs 2,398 crore), but their total grew steadily, consistent with cash deposits being reclassified by maturity rather than costs being capitalised.
View: likely a false positive caused by cash management; to be confirmed in the annual report.

[CHART: 06_case_studies.png]

[CHART: 03_beneish.png]

## What this shows about screening
- Hard cutoffs mislead: Abbott (-1.66) is flagged and Ajanta (-1.80) is not, even though Ajanta is clearly the more concerning case.
- Acquisitions mimic distress: two of the three High-risk names are acquisition stories.
- Sector context matters: a fixed inventory threshold flagged 9 of 20 companies; measuring against the sector median cut this to 6.

## Limitations
- About four years of data from Yahoo Finance; a few gaps were filled from Screener.in or by documented rules.
- The three models were built on US companies decades ago and are used here as screening tools, not predictions.
- A flag is a reason to investigate, never proof of fraud or failure.
- The Abbott explanation has not yet been confirmed in its annual report.

_For educational purposes only; not investment advice._
