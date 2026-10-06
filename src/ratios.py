"""Financial ratios for each company and fiscal year.

Reads data/processed/financials_clean.csv and writes data/processed/ratios.csv.
Any ratio whose inputs are missing, or whose denominator is zero, is NaN.
"""

from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT_PATH = PROJECT_ROOT / "data" / "processed" / "financials_clean.csv"
OUTPUT_PATH = PROJECT_ROOT / "data" / "processed" / "ratios.csv"

RATIO_COLUMNS = [
    "current_ratio",
    "debt_to_equity",
    "interest_coverage",
    "roa",
    "roe",
    "gross_margin",
    "ebitda_margin",
    "asset_turnover",
    "receivable_days",
    "inventory_days",
    "cash_conversion",
]


def safe_divide(numerator, denominator):
    """Return numerator / denominator, or NaN where the denominator is zero or missing.

    Formula: result = numerator / denominator, with 0 in the denominator replaced by NaN
    so that division never raises an error or produces infinity.
    """
    return numerator / denominator.replace(0, np.nan)


def add_prior_year(df, column):
    """Return each company's value of `column` from the previous fiscal year.

    Rows are matched within the same ticker only. If the previous row is not exactly
    one fiscal year earlier (a gap), the result is NaN rather than a value from the wrong year.
    Rows must be sorted by ticker and fiscal_year before calling.
    """
    previous_value = df.groupby("ticker")[column].shift(1)
    previous_year = df.groupby("ticker")["fiscal_year"].shift(1)
    is_consecutive = df["fiscal_year"] - previous_year == 1
    return previous_value.where(is_consecutive)


def current_ratio(df):
    """Current ratio = current assets / current liabilities.

    Measures short-term liquidity: how many rupees of short-term assets cover each rupee
    of obligations due within a year. Below 1 means a possible cash squeeze.
    """
    return safe_divide(df["current_assets"], df["current_liabilities"])


def debt_to_equity(df):
    """Debt-to-equity = total debt / total equity.

    Measures leverage: how much borrowed money the company uses for each rupee of
    shareholder equity. Higher means more financial risk.
    """
    return safe_divide(df["total_debt"], df["total_equity"])


def interest_coverage(df):
    """Interest coverage = EBIT / |interest expense|.

    Measures how many times operating profit covers interest payments. Yahoo stores
    interest expense as a positive number, but abs() keeps the ratio correct if a
    negative sign ever appears. Below about 1.5 means interest is hard to pay.
    """
    return safe_divide(df["ebit"], df["interest_expense"].abs())


def roa(df):
    """Return on assets = net income / prior-year total assets.

    Uses beginning-of-year assets, because the profit was earned by the assets that
    existed at the start of the year. Measures how well assets generate profit.
    """
    return safe_divide(df["net_income"], df["prior_total_assets"])


def roe(df):
    """Return on equity = net income / total equity.

    Measures the profit earned on shareholders' money. Compare with ROA to see how
    much leverage is boosting returns.
    """
    return safe_divide(df["net_income"], df["total_equity"])


def gross_margin(df):
    """Gross margin = gross profit / revenue.

    Share of each rupee of sales left after the direct cost of making the product.
    Falling gross margin can signal pricing pressure or rising costs.
    """
    return safe_divide(df["gross_profit"], df["revenue"])


def ebitda_margin(df):
    """EBITDA margin = (EBIT + depreciation) / revenue.

    Operating profit before depreciation, as a share of revenue. Adding depreciation
    back removes the effect of past capital spending, so it shows cash-like operating
    profitability.
    """
    return safe_divide(df["ebit"] + df["depreciation"], df["revenue"])


def asset_turnover(df):
    """Asset turnover = revenue / prior-year total assets.

    Revenue generated per rupee of assets at the start of the year. Measures how hard
    the asset base is working. Low values can mean idle or overbuilt assets.
    """
    return safe_divide(df["revenue"], df["prior_total_assets"])


def receivable_days(df):
    """Receivable days = receivables / revenue x 365.

    Average number of days the company waits to collect payment from customers.
    A rising value can mean customers are paying more slowly, or that revenue is
    being booked before cash arrives.
    """
    return safe_divide(df["receivables"], df["revenue"]) * 365


def inventory_days(df):
    """Inventory days = inventory / cost of revenue x 365.

    Average number of days stock sits before it is sold. Uses cost of revenue, not
    sales, so that inventory is compared with what it cost. Rising values can mean
    unsold stock is building up.
    """
    return safe_divide(df["inventory"], df["cost_of_revenue"]) * 365


def cash_conversion(df):
    """Cash conversion = operating cash flow / net income.

    Share of reported profit that arrives as cash from operations. Values well below 1
    for several years can mean profits are not turning into cash, a common warning sign
    of earnings manipulation. Set to NaN when net income is zero or negative, because a
    negative ratio would look like a healthy sign when it actually reflects a loss.
    """
    profit_only = df["net_income"].where(df["net_income"] > 0)
    return safe_divide(df["operating_cash_flow"], profit_only)


RATIO_FUNCTIONS = {
    "current_ratio": current_ratio,
    "debt_to_equity": debt_to_equity,
    "interest_coverage": interest_coverage,
    "roa": roa,
    "roe": roe,
    "gross_margin": gross_margin,
    "ebitda_margin": ebitda_margin,
    "asset_turnover": asset_turnover,
    "receivable_days": receivable_days,
    "inventory_days": inventory_days,
    "cash_conversion": cash_conversion,
}


def build_ratios(financials):
    """Return one row per ticker and fiscal year with all ratio columns."""
    df = financials.sort_values(["ticker", "fiscal_year"]).reset_index(drop=True)
    df["prior_total_assets"] = add_prior_year(df, "total_assets")

    result = df[["ticker", "fiscal_year"]].copy()
    for name in RATIO_COLUMNS:
        result[name] = RATIO_FUNCTIONS[name](df)
        print(f"{name}: {result[name].isna().sum()} NaN out of {len(result)} rows")
    return result


def main():
    financials = pd.read_csv(INPUT_PATH)
    ratios = build_ratios(financials)
    ratios.to_csv(OUTPUT_PATH, index=False)
    print(f"Saved {len(ratios)} rows to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
