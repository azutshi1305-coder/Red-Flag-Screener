import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# Make the project root importable so `src` can be found when pytest runs from anywhere.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.scores import INPUT_PATH, as_test, build_scores  # noqa: E402

TOLERANCE = 0.0001

# Manual Excel calculations for CIPLA.NS, FY2026.
CIPLA_EXPECTED = {
    "x1": 0.4031779,
    "x2": 0.66396869,
    "x3": 0.1240555,
    "x4": 4.31708531,
    "altman_z": 10.1759775,
    "beneish_dsri": 0.999788236,
    "beneish_gmi": 1.028140047,
    "beneish_aqi": 1.23357955,
    "beneish_sgi": 1.020861361,
    "beneish_depi": 1.081521984,
    "beneish_sgai": 1.023059983,
    "beneish_lvgi": 1.141524775,
    "beneish_tata": -0.001430488,
    "beneish_m": -2.39992555,
}

CIPLA_PIOTROSKI_TESTS = [1, 1, 0, 1, 0, 0, 1, 0, 0]


@pytest.fixture(scope="module")
def scores():
    return build_scores(pd.read_csv(INPUT_PATH))


def cipla_2026(scores):
    row = scores[(scores["ticker"] == "CIPLA.NS") & (scores["fiscal_year"] == 2026)]
    return row.iloc[0]


@pytest.mark.parametrize("column, expected", list(CIPLA_EXPECTED.items()))
def test_cipla_matches_manual_excel(scores, column, expected):
    actual = cipla_2026(scores)[column]
    assert abs(actual - expected) <= TOLERANCE


def test_cipla_altman_zone_is_safe(scores):
    assert cipla_2026(scores)["altman_zone"] == "Safe"


def test_cipla_piotroski_tests_in_order(scores):
    row = cipla_2026(scores)
    tests = [row[name] for name in row.index if name.startswith("p") and name[1].isdigit()]
    assert tests == CIPLA_PIOTROSKI_TESTS


def test_cipla_piotroski_f_is_four(scores):
    row = cipla_2026(scores)
    assert row["piotroski_f"] == 4
    assert row["piotroski_tests_available"] == 9
    assert row["piotroski_band"] == "Average"


def test_cipla_beneish_verdict(scores):
    assert cipla_2026(scores)["beneish_verdict"] == "Unlikely manipulator"


def test_auropharma_fy2025_sgai_is_neutral_with_note(scores):
    row = scores[(scores["ticker"] == "AUROPHARMA.NS") & (scores["fiscal_year"] == 2025)].iloc[0]
    assert row["beneish_sgai"] == 1.0
    assert "sgai" in row["score_notes"]


def test_missing_input_gives_nan_not_zero():
    passed = pd.Series([True, False, True])
    value = pd.Series([1.0, np.nan, 3.0])
    result = as_test(passed, value)
    assert result.iloc[0] == 1.0
    assert result.iloc[1] != result.iloc[1]  # NaN check
    assert result.iloc[2] == 1.0
