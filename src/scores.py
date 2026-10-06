"""Altman Z'', Piotroski F-score and Beneish M-score for each company and fiscal year.

Reads data/processed/financials_clean.csv and writes data/processed/scores.csv for
fiscal years 2025 (secondary) and 2026 (main). Previous years are used for comparisons,
so the full clean table is read first and filtered at the end.
Run from the project root with: python src/scores.py
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
# Lets `from src.ratios import ...` work when this file is run as `python src/scores.py`.
sys.path.insert(0, str(PROJECT_ROOT))

from src.ratios import add_prior_year, safe_divide  # noqa: E402

INPUT_PATH = PROJECT_ROOT / "data" / "processed" / "financials_clean.csv"
OUTPUT_PATH = PROJECT_ROOT / "data" / "processed" / "scores.csv"
SCORE_YEARS = [2025, 2026]

PIOTROSKI_TESTS = [
    "p1_roa_positive",
    "p2_cfo_positive",
    "p3_roa_improved",
    "p4_cfo_above_net_income",
    "p5_leverage_fell",
    "p6_current_ratio_improved",
    "p7_no_new_shares",
    "p8_gross_margin_improved",
    "p9_asset_turnover_improved",
]

BENEISH_INDICES = ["dsri", "gmi", "aqi", "sgi", "depi", "sgai", "lvgi", "tata"]

# Neutral value used when an index cannot be computed. Ratio indices are neutral at 1.0
# (no change from last year). TATA is a difference, not a ratio, so its neutral value is 0.
BENEISH_NEUTRAL = {
    "dsri": 1.0,
    "gmi": 1.0,
    "aqi": 1.0,
    "sgi": 1.0,
    "depi": 1.0,
    "sgai": 1.0,
    "lvgi": 1.0,
    "tata": 0.0,
}

# Columns that need the previous year's value for the score formulas.
LAGGED_COLUMNS = [
    "revenue",
    "net_income",
    "current_assets",
    "current_liabilities",
    "net_ppe",
    "depreciation",
    "sga",
    "long_term_debt",
    "shares_outstanding",
    "total_assets",
]


def as_test(passed, *inputs):
    """Return 1.0 if the test passes, 0.0 if it fails, and NaN if any input is missing.

    A test with missing inputs must be NaN, not 0, so missing data is never counted as a
    failed test. Comparisons with NaN are False in pandas, so the NaN check is needed.
    """
    all_present = pd.concat(inputs, axis=1).notna().all(axis=1)
    return pd.Series(np.where(all_present, passed.astype(float), np.nan), index=passed.index)


def add_lagged_columns(df):
    """Add the intermediate ratios and their previous-year values used by the scores.

    Each "prior_" column is the same quantity one fiscal year earlier for the same company,
    NaN if that year is missing. Rows must be sorted by ticker and fiscal_year.
    """
    df = df.copy()
    for column in LAGGED_COLUMNS:
        df[f"prior_{column}"] = add_prior_year(df, column)

    # Piotroski ratios. ROA and asset turnover use the start-of-year total assets.
    df["roa"] = safe_divide(df["net_income"], df["prior_total_assets"])
    df["prior_roa"] = add_prior_year(df, "roa")
    df["current_ratio"] = safe_divide(df["current_assets"], df["current_liabilities"])
    df["prior_current_ratio"] = add_prior_year(df, "current_ratio")
    df["gross_margin"] = safe_divide(df["gross_profit"], df["revenue"])
    df["prior_gross_margin"] = add_prior_year(df, "gross_margin")
    df["asset_turnover"] = safe_divide(df["revenue"], df["prior_total_assets"])
    df["prior_asset_turnover"] = add_prior_year(df, "asset_turnover")

    # Piotroski leverage: long-term debt over average total assets.
    average_assets = (df["total_assets"] + df["prior_total_assets"]) / 2
    df["leverage"] = safe_divide(df["long_term_debt"], average_assets)
    df["prior_leverage"] = add_prior_year(df, "leverage")

    # Beneish building blocks.
    df["receivable_share"] = safe_divide(df["receivables"], df["revenue"])
    df["sga_share"] = safe_divide(df["sga"], df["revenue"])
    df["asset_quality"] = 1 - safe_divide(df["current_assets"] + df["net_ppe"], df["total_assets"])
    df["depreciation_rate"] = safe_divide(df["depreciation"], df["depreciation"] + df["net_ppe"])
    df["liabilities_to_assets"] = safe_divide(
        df["current_liabilities"] + df["long_term_debt"], df["total_assets"]
    )
    for column in ["receivable_share", "sga_share", "asset_quality", "depreciation_rate",
                   "liabilities_to_assets"]:
        df[f"prior_{column}"] = add_prior_year(df, column)
    return df


def altman_z(df):
    """Return X1..X4 and the Altman Z'' score as a DataFrame.

    X1 = (current assets - current liabilities) / total assets   (liquidity buffer)
    X2 = retained earnings / total assets                        (cumulated profitability)
    X3 = EBIT / total assets                                     (operating profitability)
    X4 = total equity / total liabilities                        (equity cushion)
    Z'' = 6.56*X1 + 3.26*X2 + 6.72*X3 + 1.05*X4
    """
    result = pd.DataFrame(index=df.index)
    result["x1"] = safe_divide(df["current_assets"] - df["current_liabilities"], df["total_assets"])
    result["x2"] = safe_divide(df["retained_earnings"], df["total_assets"])
    result["x3"] = safe_divide(df["ebit"], df["total_assets"])
    result["x4"] = safe_divide(df["total_equity"], df["total_liabilities"])
    result["altman_z"] = (
        6.56 * result["x1"] + 3.26 * result["x2"] + 6.72 * result["x3"] + 1.05 * result["x4"]
    )
    return result


def altman_zone(z):
    """Classify Z'' as "Safe" (Z > 2.6), "Grey" (1.1 <= Z <= 2.6) or "Distress" (Z < 1.1).

    Returns None when Z is missing.
    """
    if pd.isna(z):
        return None
    if z > 2.6:
        return "Safe"
    if z >= 1.1:
        return "Grey"
    return "Distress"


def piotroski_tests(df):
    """Return the nine Piotroski tests as a DataFrame of 1.0, 0.0 or NaN.

    1. ROA_t > 0, where ROA_t = net income_t / total assets_(t-1)
    2. Operating cash flow_t > 0
    3. ROA_t > ROA_(t-1)
    4. Operating cash flow_t > net income_t (profits backed by cash)
    5. Leverage fell: LTD_t / avg assets_(t,t-1) < LTD_(t-1) / avg assets_(t-1,t-2).
       A debt-free company (LTD = 0 in both years) passes.
    6. Current ratio_t > current ratio_(t-1)
    7. Shares_t <= shares_(t-1) * 1.01 (increases under 1% are ESOPs, not equity raises)
    8. Gross margin_t > gross margin_(t-1)
    9. Asset turnover_t > asset turnover_(t-1), where turnover_t = revenue_t / assets_(t-1)
    """
    tests = pd.DataFrame(index=df.index)
    tests[PIOTROSKI_TESTS[0]] = as_test(df["roa"] > 0, df["roa"])
    tests[PIOTROSKI_TESTS[1]] = as_test(df["operating_cash_flow"] > 0, df["operating_cash_flow"])
    tests[PIOTROSKI_TESTS[2]] = as_test(df["roa"] > df["prior_roa"], df["roa"], df["prior_roa"])
    tests[PIOTROSKI_TESTS[3]] = as_test(
        df["operating_cash_flow"] > df["net_income"], df["operating_cash_flow"], df["net_income"]
    )

    debt_free = (df["long_term_debt"] == 0) & (df["prior_long_term_debt"] == 0)
    leverage_fell = df["leverage"] < df["prior_leverage"]
    leverage_test = as_test(leverage_fell, df["leverage"], df["prior_leverage"])
    tests[PIOTROSKI_TESTS[4]] = leverage_test.mask(debt_free, 1.0)

    tests[PIOTROSKI_TESTS[5]] = as_test(
        df["current_ratio"] > df["prior_current_ratio"], df["current_ratio"], df["prior_current_ratio"]
    )
    tests[PIOTROSKI_TESTS[6]] = as_test(
        df["shares_outstanding"] <= df["prior_shares_outstanding"] * 1.01,
        df["shares_outstanding"],
        df["prior_shares_outstanding"],
    )
    tests[PIOTROSKI_TESTS[7]] = as_test(
        df["gross_margin"] > df["prior_gross_margin"], df["gross_margin"], df["prior_gross_margin"]
    )
    tests[PIOTROSKI_TESTS[8]] = as_test(
        df["asset_turnover"] > df["prior_asset_turnover"], df["asset_turnover"], df["prior_asset_turnover"]
    )
    return tests


def piotroski_band(f):
    """Band the Piotroski F-score: "Strong" (8-9), "Average" (4-7), "Weak" (0-3).

    Returns None when F is missing.
    """
    if pd.isna(f):
        return None
    if f >= 8:
        return "Strong"
    if f >= 4:
        return "Average"
    return "Weak"


def beneish_indices(df):
    """Return the eight Beneish indices as a DataFrame. Each index compares year t with t-1.

    DSRI = (receivables/revenue)_t / (receivables/revenue)_(t-1)   (receivables growing faster than sales)
    GMI  = gross margin_(t-1) / gross margin_t                      (margin deterioration)
    AQI  = asset quality_t / asset quality_(t-1), where asset quality = 1 - (current assets + net PPE) / total assets
    SGI  = revenue_t / revenue_(t-1)                                (growth pressure)
    DEPI = depreciation rate_(t-1) / depreciation rate_t, where rate = depreciation / (depreciation + net PPE)
    SGAI = (SG&A/revenue)_t / (SG&A/revenue)_(t-1)                  (overhead falling relative to sales)
    LVGI = liabilities-to-assets_t / liabilities-to-assets_(t-1), where liabilities-to-assets = (current liabilities + LTD) / total assets
    TATA = (net income_t - operating cash flow_t) / total assets_t  (accruals: profit not yet in cash)
    """
    indices = pd.DataFrame(index=df.index)
    indices["dsri"] = safe_divide(df["receivable_share"], df["prior_receivable_share"])
    indices["gmi"] = safe_divide(df["prior_gross_margin"], df["gross_margin"])
    indices["aqi"] = safe_divide(df["asset_quality"], df["prior_asset_quality"])
    indices["sgi"] = safe_divide(df["revenue"], df["prior_revenue"])
    indices["depi"] = safe_divide(df["prior_depreciation_rate"], df["depreciation_rate"])
    indices["sgai"] = safe_divide(df["sga_share"], df["prior_sga_share"])
    indices["lvgi"] = safe_divide(df["liabilities_to_assets"], df["prior_liabilities_to_assets"])
    indices["tata"] = safe_divide(df["net_income"] - df["operating_cash_flow"], df["total_assets"])
    return indices


def fill_neutral_indices(indices):
    """Replace each missing Beneish index with its neutral value and list it in a notes column.

    Returns (filled_indices, notes). The notes are an empty string when nothing was filled.
    """
    filled = indices.copy()
    notes = pd.Series("", index=indices.index)
    for name in BENEISH_INDICES:
        missing = filled[name].isna()
        filled.loc[missing, name] = BENEISH_NEUTRAL[name]
        notes[missing] = notes[missing] + f"{name} neutral ({BENEISH_NEUTRAL[name]}); "
    return filled, notes.str.rstrip("; ")


def beneish_m(indices):
    """Return the Beneish M-score from the eight indices.

    M = -4.84 + 0.920*DSRI + 0.528*GMI + 0.404*AQI + 0.892*SGI + 0.115*DEPI
        - 0.172*SGAI + 4.679*TATA - 0.327*LVGI
    """
    return (
        -4.84
        + 0.920 * indices["dsri"]
        + 0.528 * indices["gmi"]
        + 0.404 * indices["aqi"]
        + 0.892 * indices["sgi"]
        + 0.115 * indices["depi"]
        - 0.172 * indices["sgai"]
        + 4.679 * indices["tata"]
        - 0.327 * indices["lvgi"]
    )


def beneish_verdict(m):
    """Return "Likely manipulator" if M > -1.78, else "Unlikely manipulator". None if M is missing."""
    if pd.isna(m):
        return None
    if m > -1.78:
        return "Likely manipulator"
    return "Unlikely manipulator"


def build_scores(financials):
    """Return one row per ticker and fiscal year (FY2025, FY2026) with all score components."""
    df = financials.sort_values(["ticker", "fiscal_year"]).reset_index(drop=True)
    df = add_lagged_columns(df)

    altman = altman_z(df)
    tests = piotroski_tests(df)
    indices, notes = fill_neutral_indices(beneish_indices(df))
    m_score = beneish_m(indices)

    result = df[["ticker", "fiscal_year"]].copy()
    result = pd.concat([result, altman, tests], axis=1)
    result["altman_zone"] = altman["altman_z"].map(altman_zone)
    result["piotroski_f"] = tests.sum(axis=1, min_count=1)
    result["piotroski_tests_available"] = tests.notna().sum(axis=1)
    result["piotroski_band"] = result["piotroski_f"].map(piotroski_band)
    result = pd.concat([result, indices.add_prefix("beneish_")], axis=1)
    result["beneish_m"] = m_score
    result["beneish_verdict"] = m_score.map(beneish_verdict)
    result["score_notes"] = notes

    return result[result["fiscal_year"].isin(SCORE_YEARS)].reset_index(drop=True)


def main():
    financials = pd.read_csv(INPUT_PATH)
    scores = build_scores(financials)
    scores.to_csv(OUTPUT_PATH, index=False)
    print(f"Saved {len(scores)} rows to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
