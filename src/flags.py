"""Custom red flags, Beneish zones and the combined risk score for FY2026.

Reads the cleaned financials, ratios, scores and company list, and writes
data/processed/final_scores.csv: one row per company, sorted by risk score (highest first).
Run from the project root with: python src/flags.py
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
# Lets `from src.ratios import ...` work when this file is run as `python src/flags.py`.
sys.path.insert(0, str(PROJECT_ROOT))

from src.ratios import add_prior_year, safe_divide  # noqa: E402
from src.scores import as_test  # noqa: E402

FINANCIALS_PATH = PROJECT_ROOT / "data" / "processed" / "financials_clean.csv"
RATIOS_PATH = PROJECT_ROOT / "data" / "processed" / "ratios.csv"
SCORES_PATH = PROJECT_ROOT / "data" / "processed" / "scores.csv"
COMPANIES_PATH = PROJECT_ROOT / "data" / "companies.csv"
NOTES_PATH = PROJECT_ROOT / "data" / "analyst_notes.csv"
OUTPUT_PATH = PROJECT_ROOT / "data" / "processed" / "final_scores.csv"

FLAG_YEAR = 2026
CASH_YEARS = [2024, 2025, 2026]

FLAG_COLUMNS = [
    "f1_receivables_outpacing_sales",
    "f2_weak_cash_conversion",
    "f3_inventory_buildup",
    "f4_debt_stress",
    "f5_low_interest_cover",
]


def build_flag_table(financials, ratios):
    """Return one row per company and fiscal year with the inputs and prior-year values the flags need.

    Adds inventory_days and interest_coverage from ratios. cfo_below_net_income is 1 when
    operating cash flow is below net income, 0 when not, and NaN when either is missing.
    The prior_ columns are the same quantity one fiscal year earlier, NaN if that year is missing.
    The "_prior2" column is the same quantity two fiscal years earlier.
    """
    df = financials.sort_values(["ticker", "fiscal_year"]).reset_index(drop=True)
    df = df.merge(
        ratios[["ticker", "fiscal_year", "inventory_days", "interest_coverage"]],
        on=["ticker", "fiscal_year"],
        how="left",
    )
    df["cfo_below_net_income"] = as_test(
        df["operating_cash_flow"] < df["net_income"], df["operating_cash_flow"], df["net_income"]
    )
    for column in [
        "receivables",
        "revenue",
        "inventory_days",
        "total_debt",
        "interest_coverage",
        "cfo_below_net_income",
    ]:
        df[f"prior_{column}"] = add_prior_year(df, column)
    df["cfo_below_net_income_prior2"] = add_prior_year(df, "prior_cfo_below_net_income")
    return df


def receivables_growth(df):
    """Receivables growth = receivables_t / receivables_(t-1) - 1. NaN if either year is missing."""
    return safe_divide(df["receivables"], df["prior_receivables"]) - 1


def revenue_growth(df):
    """Revenue growth = revenue_t / revenue_(t-1) - 1. NaN if either year is missing."""
    return safe_divide(df["revenue"], df["prior_revenue"]) - 1


def inventory_days_change(df):
    """Change in inventory days = inventory_days_t - inventory_days_(t-1). NaN if either year is missing."""
    return df["inventory_days"] - df["prior_inventory_days"]


def cfo_years_below(df):
    """Count of FY2024, FY2025 and FY2026 years in which operating cash flow was below net income.

    Missing years are not counted. Uses the raw values, so loss-making years are compared directly.
    """
    years = df[["cfo_below_net_income", "prior_cfo_below_net_income", "cfo_below_net_income_prior2"]]
    return (years == 1).sum(axis=1)


def flag_receivables_outpacing_sales(df):
    """F1: 1 if receivables growth exceeds revenue growth by more than 10 percentage points.

    Formula: flag = 1 if receivables growth > revenue growth + 0.10, else 0.
    NaN if either year is missing.
    """
    return as_test(
        receivables_growth(df) > revenue_growth(df) + 0.10,
        receivables_growth(df),
        revenue_growth(df),
    )


def flag_weak_cash_conversion(df):
    """F2: 1 if operating cash flow was below net income in at least 2 of FY2024, FY2025, FY2026.

    Formula: count = number of years with CFO < net income. Flag = 1 if count >= 2.
    Flag = 0 if count + missing years < 2, because 2 years can then never be reached.
    Otherwise NaN, because a missing year could still decide the flag.
    """
    below_count = cfo_years_below(df)
    years = df[["cfo_below_net_income", "prior_cfo_below_net_income", "cfo_below_net_income_prior2"]]
    missing_count = years.isna().sum(axis=1)
    conditions = [below_count >= 2, below_count + missing_count < 2]
    return pd.Series(np.select(conditions, [1.0, 0.0], default=np.nan), index=df.index)


def sector_median_inventory_days_change(df):
    """Median change in inventory days across all companies in df with a change available.

    This is the sector's shared trend. Computing it fresh from df (rather than hardcoding a
    number) means the flag adapts automatically if the whole sector's inventory days shift
    in a future year.
    """
    return inventory_days_change(df).median()


def flag_inventory_buildup(df):
    """F3: 1 if a company's change in inventory days is more than 15 days above the sector median change.

    Formula: inventory days = inventory / cost of revenue x 365 (from ratios.csv).
    change_t = inventory_days_t - inventory_days_(t-1).
    Flag = 1 if change_t > median(change across all companies) + 15, else 0. NaN if change_t is missing.

    Relative rule, not a fixed +15 days: the sector median change was +13.46 days (FY2026 vs
    FY2025, average +16.20), showing a sector-wide inventory build-up. A fixed threshold would
    flag companies merely for following that shared trend, so the flag instead measures how far
    a company's build-up is above its peers.
    """
    change = inventory_days_change(df)
    median = sector_median_inventory_days_change(df)
    return as_test(change > median + 15, change)


def flag_debt_stress(df):
    """F4: 1 if borrowings rose and interest cover fell, but only when debt is material.

    Formula: flag = 1 if total debt_t > total debt_(t-1)
                    AND interest coverage_t < interest coverage_(t-1)
                    AND total debt_t > 10% of total equity_t.
    Materiality rule: debt at or below 10% of equity does not count, so small borrowings
    cannot trigger the flag. If interest coverage is NaN in either year, F4 = 0.
    """
    debt_rose = df["total_debt"] > df["prior_total_debt"]
    coverage_fell = df["interest_coverage"] < df["prior_interest_coverage"]
    material = df["total_debt"] > 0.10 * df["total_equity"]
    result = as_test(
        debt_rose & coverage_fell & material,
        df["total_debt"],
        df["prior_total_debt"],
        df["total_equity"],
    )
    coverage_missing = df["interest_coverage"].isna() | df["prior_interest_coverage"].isna()
    return result.mask(coverage_missing, 0.0)


def flag_low_interest_cover(df):
    """F5: 1 if interest coverage is below 1.5, where coverage = EBIT / interest expense.

    A missing coverage (no interest expense) is 0, not flagged, because the comparison with NaN is False.
    """
    return (df["interest_coverage"] < 1.5).astype(float)


def add_flag_columns(df):
    """Add the growth helper columns and the five flag columns to a table of FY2026 rows."""
    df = df.copy()
    df["receivables_growth"] = receivables_growth(df)
    df["revenue_growth"] = revenue_growth(df)
    df["inventory_days_change"] = inventory_days_change(df)
    df["inventory_days_sector_median_change"] = sector_median_inventory_days_change(df)
    df["cfo_years_below"] = cfo_years_below(df)
    df[FLAG_COLUMNS[0]] = flag_receivables_outpacing_sales(df)
    df[FLAG_COLUMNS[1]] = flag_weak_cash_conversion(df)
    df[FLAG_COLUMNS[2]] = flag_inventory_buildup(df)
    df[FLAG_COLUMNS[3]] = flag_debt_stress(df)
    df[FLAG_COLUMNS[4]] = flag_low_interest_cover(df)
    return df


def beneish_zone(m):
    """Classify Beneish M: "Likely" if M > -1.78, "Watch" if -2.22 < M <= -1.78, "Unlikely" if M <= -2.22.

    Returns None when M is missing.
    """
    if pd.isna(m):
        return None
    if m > -1.78:
        return "Likely"
    if m > -2.22:
        return "Watch"
    return "Unlikely"


def score_components(row):
    """Return the (points, text) pairs that make up one company's risk score.

    Points: Altman Distress +2, Altman Grey +1; Beneish Likely +2, Watch +1;
    Piotroski F <= 3 +1; each custom flag that equals 1 gives +1.
    Each text ends with its points, e.g. "(+2)", so the reasons can be checked against the score.
    """
    parts = []
    if row["altman_zone"] == "Distress":
        parts.append((2, "Altman Distress (+2)"))
    elif row["altman_zone"] == "Grey":
        parts.append((1, "Altman Grey (+1)"))

    if row["beneish_zone"] == "Likely":
        parts.append((2, "Beneish Likely (+2)"))
    elif row["beneish_zone"] == "Watch":
        parts.append((1, "Beneish Watch (+1)"))

    if row["piotroski_f"] <= 3:
        parts.append((1, f"Piotroski F {int(row['piotroski_f'])} (+1)"))

    if row[FLAG_COLUMNS[0]] == 1:
        parts.append(
            (
                1,
                f"receivables grew {row['receivables_growth']:.0%} vs sales "
                f"{row['revenue_growth']:.0%} (+1)",
            )
        )
    if row[FLAG_COLUMNS[1]] == 1:
        parts.append(
            (1, f"operating cash flow below net income in {int(row['cfo_years_below'])} of 3 years (+1)")
        )
    if row[FLAG_COLUMNS[2]] == 1:
        parts.append(
            (
                1,
                f"inventory days up {row['inventory_days_change']:.0f} vs sector median "
                f"{row['inventory_days_sector_median_change']:.0f} (+1)",
            )
        )
    if row[FLAG_COLUMNS[3]] == 1:
        parts.append((1, "borrowings up and interest cover down, debt above 10% of equity (+1)"))
    if row[FLAG_COLUMNS[4]] == 1:
        parts.append((1, f"interest cover {row['interest_coverage']:.2f}x, below 1.5 (+1)"))
    return parts


def risk_score_and_reasons(row):
    """Return (risk_score, reasons) for one company.

    Score = sum of the points in score_components. Reasons join each text with "; ",
    or read "No flags" when no points were given.
    """
    parts = score_components(row)
    score = sum(points for points, _ in parts)
    reasons = "; ".join(text for _, text in parts) if parts else "No flags"
    return score, reasons


def risk_band(score):
    """Band the risk score: "Low" (0-1), "Watch" (2-3), "High" (4 or more)."""
    if score >= 4:
        return "High"
    if score >= 2:
        return "Watch"
    return "Low"


def build_final_scores(financials, ratios, scores, companies, notes):
    """Return one row per company for FY2026, with flags, risk score, reasons and analyst notes.

    Sorted by risk score (highest first), then by lower Altman Z'' first to break ties.
    """
    table = build_flag_table(financials, ratios)
    d = add_flag_columns(table[table["fiscal_year"] == FLAG_YEAR])

    score_columns = ["ticker", "altman_z", "altman_zone", "piotroski_f", "piotroski_band", "beneish_m", "score_notes"]
    d = d.merge(scores.loc[scores["fiscal_year"] == FLAG_YEAR, score_columns], on="ticker", how="left")
    d["beneish_zone"] = d["beneish_m"].map(beneish_zone)
    d = d.merge(companies[["ticker", "company_name"]], on="ticker", how="left")
    d = d.merge(notes, on="ticker", how="left")
    d["analyst_note"] = d["analyst_note"].fillna("")

    pairs = [risk_score_and_reasons(row) for _, row in d.iterrows()]
    d["risk_score"] = [score for score, _ in pairs]
    d["reasons"] = [reasons for _, reasons in pairs]
    d["risk_band"] = d["risk_score"].map(risk_band)

    for column in FLAG_COLUMNS:
        d[column] = d[column].astype("Int64")
    d["piotroski_f"] = d["piotroski_f"].astype("Int64")

    output_columns = [
        "ticker",
        "company_name",
        "altman_z",
        "altman_zone",
        "piotroski_f",
        "piotroski_band",
        "beneish_m",
        "beneish_zone",
        *FLAG_COLUMNS,
        "risk_score",
        "risk_band",
        "reasons",
        "score_notes",
        "analyst_note",
    ]
    return d[output_columns].sort_values(["risk_score", "altman_z"], ascending=[False, True]).reset_index(drop=True)


def main():
    financials = pd.read_csv(FINANCIALS_PATH)
    ratios = pd.read_csv(RATIOS_PATH)
    scores = pd.read_csv(SCORES_PATH)
    companies = pd.read_csv(COMPANIES_PATH)
    notes = pd.read_csv(NOTES_PATH).rename(columns={"note": "analyst_note"})
    final = build_final_scores(financials, ratios, scores, companies, notes)
    final.to_csv(OUTPUT_PATH, index=False)
    print(f"Saved {len(final)} rows to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
