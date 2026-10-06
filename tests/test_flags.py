import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# Make the project root importable so `src` can be found when pytest runs from anywhere.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.flags import (  # noqa: E402
    FINANCIALS_PATH,
    FLAG_COLUMNS,
    NOTES_PATH,
    RATIOS_PATH,
    SCORES_PATH,
    COMPANIES_PATH,
    add_flag_columns,
    beneish_zone,
    build_final_scores,
    build_flag_table,
    flag_debt_stress,
    flag_inventory_buildup,
    flag_low_interest_cover,
    flag_receivables_outpacing_sales,
    flag_weak_cash_conversion,
    risk_band,
    score_components,
)

FINANCIAL_FIELDS = ["receivables", "revenue", "operating_cash_flow", "net_income", "total_debt", "total_equity"]
RATIO_FIELDS = ["inventory_days", "interest_coverage"]

BASE_YEAR = {
    "receivables": 100.0,
    "revenue": 1000.0,
    "operating_cash_flow": 200.0,
    "net_income": 100.0,
    "total_debt": 0.0,
    "total_equity": 1000.0,
    "inventory_days": 100.0,
    "interest_coverage": 10.0,
}


def fy2026_row(years):
    """Build the flag table for one synthetic company and return its FY2026 row with flags added.

    `years` maps fiscal year to the values for that year. Missing fields default to BASE_YEAR.
    """
    financial_rows, ratio_rows = [], []
    for year, values in years.items():
        merged = {**BASE_YEAR, **values}
        financial_rows.append(
            {"ticker": "A", "fiscal_year": year, **{field: merged[field] for field in FINANCIAL_FIELDS}}
        )
        ratio_rows.append({"ticker": "A", "fiscal_year": year, **{field: merged[field] for field in RATIO_FIELDS}})
    table = build_flag_table(pd.DataFrame(financial_rows), pd.DataFrame(ratio_rows))
    return add_flag_columns(table[table["fiscal_year"] == 2026]).iloc[0]


def test_f1_triggers_when_receivables_outpace_sales_by_more_than_10_points():
    row = fy2026_row({2025: {}, 2026: {"receivables": 150.0, "revenue": 1000.0}})
    assert row[FLAG_COLUMNS[0]] == 1


def test_f1_does_not_trigger_within_10_points():
    row = fy2026_row({2025: {}, 2026: {"receivables": 105.0, "revenue": 1000.0}})
    assert row[FLAG_COLUMNS[0]] == 0


def test_f2_triggers_when_two_of_three_years_have_cfo_below_profit():
    row = fy2026_row(
        {
            2024: {"operating_cash_flow": 50.0, "net_income": 100.0},
            2025: {"operating_cash_flow": 50.0, "net_income": 100.0},
            2026: {"operating_cash_flow": 200.0, "net_income": 100.0},
        }
    )
    assert row[FLAG_COLUMNS[1]] == 1


def test_f2_does_not_trigger_with_only_one_weak_year():
    row = fy2026_row(
        {
            2024: {"operating_cash_flow": 200.0, "net_income": 100.0},
            2025: {"operating_cash_flow": 200.0, "net_income": 100.0},
            2026: {"operating_cash_flow": 50.0, "net_income": 100.0},
        }
    )
    assert row[FLAG_COLUMNS[1]] == 0


def test_f2_is_nan_when_a_missing_year_could_still_decide_it():
    row = fy2026_row(
        {
            2024: {"net_income": np.nan},
            2025: {"operating_cash_flow": 50.0, "net_income": 100.0},
            2026: {"operating_cash_flow": 200.0, "net_income": 100.0},
        }
    )
    assert np.isnan(row[FLAG_COLUMNS[1]])


def test_f2_is_zero_when_missing_years_cannot_reach_two():
    row = fy2026_row(
        {
            2024: {"net_income": np.nan},
            2025: {"operating_cash_flow": 200.0, "net_income": 100.0},
            2026: {"operating_cash_flow": 200.0, "net_income": 100.0},
        }
    )
    assert row[FLAG_COLUMNS[1]] == 0


def test_f3_triggers_when_inventory_days_rise_more_than_15():
    row = fy2026_row({2025: {"inventory_days": 100.0}, 2026: {"inventory_days": 116.0}})
    assert row[FLAG_COLUMNS[2]] == 1


def test_f3_does_not_trigger_at_10_days():
    row = fy2026_row({2025: {"inventory_days": 100.0}, 2026: {"inventory_days": 110.0}})
    assert row[FLAG_COLUMNS[2]] == 0


def test_f4_triggers_when_debt_is_material_and_coverage_falls():
    row = fy2026_row(
        {
            2025: {"total_debt": 100.0, "interest_coverage": 10.0},
            2026: {"total_debt": 200.0, "interest_coverage": 5.0, "total_equity": 1000.0},
        }
    )
    assert row[FLAG_COLUMNS[3]] == 1


def test_f4_materiality_blocks_small_debt():
    row = fy2026_row(
        {
            2025: {"total_debt": 100.0, "interest_coverage": 10.0},
            2026: {"total_debt": 200.0, "interest_coverage": 5.0, "total_equity": 3000.0},
        }
    )
    assert row[FLAG_COLUMNS[3]] == 0


def test_f4_is_zero_when_interest_coverage_is_nan():
    row = fy2026_row(
        {
            2025: {"total_debt": 100.0, "interest_coverage": 10.0},
            2026: {"total_debt": 200.0, "interest_coverage": np.nan},
        }
    )
    assert row[FLAG_COLUMNS[3]] == 0


def test_f5_triggers_below_1_5_cover():
    row = fy2026_row({2026: {"interest_coverage": 1.2}})
    assert row[FLAG_COLUMNS[4]] == 1


def test_f5_does_not_trigger_at_2x_cover():
    row = fy2026_row({2026: {"interest_coverage": 2.0}})
    assert row[FLAG_COLUMNS[4]] == 0


def test_f5_nan_cover_is_zero_not_flagged():
    row = fy2026_row({2026: {"interest_coverage": np.nan}})
    assert row[FLAG_COLUMNS[4]] == 0


@pytest.mark.parametrize(
    "m, zone",
    [(-1.66, "Likely"), (-1.78, "Watch"), (-1.80, "Watch"), (-2.21, "Watch"), (-2.22, "Unlikely"), (-2.30, "Unlikely"), (np.nan, None)],
)
def test_beneish_zone_boundaries(m, zone):
    assert beneish_zone(m) == zone


@pytest.mark.parametrize("score, band", [(0, "Low"), (1, "Low"), (2, "Watch"), (3, "Watch"), (4, "High")])
def test_risk_band_boundaries(score, band):
    assert risk_band(score) == band


def test_score_components_add_up_for_a_high_risk_row():
    row = pd.Series(
        {
            "altman_zone": "Distress",
            "beneish_zone": "Likely",
            "piotroski_f": 2,
            "f1_receivables_outpacing_sales": 1,
            "f2_weak_cash_conversion": 0,
            "f3_inventory_buildup": 0,
            "f4_debt_stress": 0,
            "f5_low_interest_cover": 0,
            "receivables_growth": 0.5,
            "revenue_growth": 0.1,
        }
    )
    parts = score_components(row)
    assert sum(points for points, _ in parts) == 2 + 2 + 1 + 1


@pytest.fixture(scope="module")
def final_scores():
    return build_final_scores(
        pd.read_csv(FINANCIALS_PATH),
        pd.read_csv(RATIOS_PATH),
        pd.read_csv(SCORES_PATH),
        pd.read_csv(COMPANIES_PATH),
        pd.read_csv(NOTES_PATH).rename(columns={"note": "analyst_note"}),
    )


def test_ajantpharm_fy2026_receivables_flag_is_one(final_scores):
    row = final_scores[final_scores["ticker"] == "AJANTPHARM.NS"].iloc[0]
    assert row["f1_receivables_outpacing_sales"] == 1


def test_risk_score_equals_sum_of_reasons_for_every_company(final_scores):
    for _, row in final_scores.iterrows():
        points = [int(p) for p in re.findall(r"\(\+(\d+)\)", row["reasons"])]
        assert sum(points) == row["risk_score"], row["ticker"]
