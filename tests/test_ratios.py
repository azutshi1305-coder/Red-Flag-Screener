import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# Make the project root importable so `src` can be found when pytest runs from anywhere.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.ratios import INPUT_PATH, add_prior_year, build_ratios, cash_conversion, safe_divide  # noqa: E402

TOLERANCE = 0.0001

# Manual Excel calculations for CIPLA.NS.
CIPLA_EXPECTED = [
    ("CIPLA.NS", 2026, "roa", 0.103758682),
    ("CIPLA.NS", 2026, "current_ratio", 3.442891586),
    ("CIPLA.NS", 2026, "gross_margin", 0.622827406),
    ("CIPLA.NS", 2026, "asset_turnover", 0.741211126),
    ("CIPLA.NS", 2025, "roa", 0.161151324),
    ("CIPLA.NS", 2025, "current_ratio", 4.246661172),
    ("CIPLA.NS", 2025, "gross_margin", 0.640353798),
    ("CIPLA.NS", 2025, "asset_turnover", 0.829682418),
]


@pytest.fixture(scope="module")
def ratios():
    return build_ratios(pd.read_csv(INPUT_PATH))


@pytest.mark.parametrize("ticker, year, ratio, expected", CIPLA_EXPECTED)
def test_cipla_matches_manual_excel(ratios, ticker, year, ratio, expected):
    row = ratios[(ratios["ticker"] == ticker) & (ratios["fiscal_year"] == year)]
    actual = row[ratio].iloc[0]
    assert abs(actual - expected) <= TOLERANCE


def test_safe_divide_zero_denominator_gives_nan():
    result = safe_divide(pd.Series([10.0]), pd.Series([0.0]))
    assert np.isnan(result.iloc[0])


def test_safe_divide_missing_input_gives_nan():
    result = safe_divide(pd.Series([np.nan, 10.0]), pd.Series([5.0, np.nan]))
    assert result.isna().all()


def test_add_prior_year_never_crosses_companies():
    df = pd.DataFrame(
        {
            "ticker": ["A", "A", "B", "B"],
            "fiscal_year": [2024, 2025, 2024, 2025],
            "total_assets": [100.0, 110.0, 500.0, 550.0],
        }
    )
    prior = add_prior_year(df, "total_assets")
    assert np.isnan(prior.iloc[0])
    assert prior.iloc[1] == 100.0
    assert np.isnan(prior.iloc[2])
    assert prior.iloc[3] == 500.0


def test_cash_conversion_nan_when_net_income_not_positive():
    df = pd.DataFrame(
        {
            "ticker": ["A", "B", "C"],
            "fiscal_year": [2025, 2025, 2025],
            "operating_cash_flow": [50.0, 50.0, 50.0],
            "net_income": [100.0, 0.0, -20.0],
        }
    )
    result = cash_conversion(df)
    assert result.iloc[0] == 0.5
    assert np.isnan(result.iloc[1])
    assert np.isnan(result.iloc[2])


def test_add_prior_year_gap_in_years_gives_nan():
    df = pd.DataFrame(
        {
            "ticker": ["A", "A"],
            "fiscal_year": [2023, 2025],
            "total_assets": [100.0, 110.0],
        }
    )
    prior = add_prior_year(df, "total_assets")
    assert np.isnan(prior.iloc[1])
