"""Incomplete controls must be disclosed without bypassing candidate gates."""

import pytest

from crypto_factor_research.window_report import select_report_cases


def inventory(failed="random_1012"):
    return {
        "success": False,
        "primary_replay_identical": True,
        "registered_cases": 3,
        "cases": [
            {"case": "lightgbm", "bps": 5, "success": True},
            {"case": "primary_replay", "bps": 5, "success": True},
            {"case": failed, "bps": 5, "success": False, "error": "Nonpositive NAV"},
        ],
    }


def test_partial_controls_require_explicit_opt_in_and_retain_failure():
    summary = inventory()
    with pytest.raises(ValueError, match="cases failed"):
        select_report_cases(summary)
    cases, failed = select_report_cases(summary, True)
    assert len(cases) == 2 and failed == [summary["cases"][-1]]
    assert summary["success"] is False


@pytest.mark.parametrize("name", ["lightgbm", "equal_groups", "momentum60", "primary_replay"])
def test_candidate_or_replay_failure_cannot_be_bypassed(name):
    with pytest.raises(ValueError, match="cases failed"):
        select_report_cases(inventory(name), True)


def test_replay_inventory_and_summary_gates_remain_strict():
    summary = inventory()
    summary["primary_replay_identical"] = False
    with pytest.raises(ValueError, match="replay"):
        select_report_cases(summary, True)
    summary = inventory()
    summary["registered_cases"] = 4
    with pytest.raises(ValueError, match="inventory"):
        select_report_cases(summary, True)
    summary = inventory()
    summary["cases"][-1]["success"] = True
    with pytest.raises(ValueError, match="unsuccessful"):
        select_report_cases(summary, True)
