"""Dated exclusions retain prior episodes and cannot see future holding problems."""

import numpy as np
import pandas as pd

from crypto_factor_research.capacity import dated_candidates, holding_audit, nominal_breaks
from crypto_factor_research.config import DAY, HOUR


def panel():
    return pd.DataFrame(
        {
            "instrument_id": ["REUSED", "REUSED", "OLD", "NEW", "NEW", "PRE"],
            "feature_cutoff_ms": [10 * DAY, 20 * DAY, 20 * DAY, 10 * DAY, 20 * DAY, 20 * DAY],
            "decision_ms": [
                10 * DAY + HOUR,
                20 * DAY + HOUR,
                20 * DAY + HOUR,
                10 * DAY + HOUR,
                20 * DAY + HOUR,
                20 * DAY + HOUR,
            ],
            "research_candidate": [True, True, True, False, True, True],
        }
    )


def test_dated_scope_preserves_old_crypto_episode_and_absent_historical_names():
    metadata = {
        "REUSED": {"underlyingType": "EQUITY", "onboardDate": 15 * DAY},
        "NEW": {"underlyingType": "COIN", "onboardDate": 10 * DAY},
        "PRE": {"underlyingType": "PREMARKET", "onboardDate": 15 * DAY},
    }
    result = dated_candidates(panel(), metadata)
    assert result.provisional_entry_candidate.tolist() == [True, False, True, False, True, False]
    assert result.current_coin_supported_candidate.tolist() == [
        False,
        False,
        False,
        False,
        True,
        False,
    ]
    assert result.loc[2, "historical_class_unresolved"]
    assert not result.execution_ready.any()


def test_future_gap_risk_does_not_change_entry_or_preemptively_close_position():
    metadata = {"REUSED": {"underlyingType": "COIN", "onboardDate": 0}}
    entry = dated_candidates(panel(), metadata)
    gaps = pd.DataFrame({"instrument_id": ["REUSED"], "nominal_event_ms": [12 * DAY]})
    result = holding_audit(entry, gaps)
    pd.testing.assert_series_equal(
        entry.provisional_entry_candidate, result.provisional_entry_candidate
    )
    assert result.loc[0, "provisional_entry_candidate"]
    assert result.loc[0, "known_funding_breaks_next_7d"] == 1
    assert result.loc[1, "known_funding_breaks_next_7d"] == 0
    assert holding_audit(entry, gaps.iloc[:0]).provisional_entry_candidate.equals(
        result.provisional_entry_candidate
    )


def test_nominal_gap_is_not_a_payment_and_recovered_observation_removes_it():
    old = pd.DataFrame(
        {"event_timestamp_ms": [5, 8 * HOUR + 5], "funding_interval_hours": [4.0, 4.0]}
    )
    found = nominal_breaks("X", old, [])
    assert [row["nominal_event_ms"] for row in found] == [4 * HOUR]
    assert found[0]["meaning"] == "absent_observation_not_proven_payment"
    assert not nominal_breaks("X", old, [{"timestamp_ms": 4 * HOUR + 3}])
    old.loc[1, "funding_interval_hours"] = 8
    assert not nominal_breaks("X", old, [])


def test_reentry_uses_current_past_input_state_without_permanent_blacklist():
    data = panel().iloc[[3, 4]].copy()
    assert dated_candidates(
        data, {"NEW": {"underlyingType": "COIN", "onboardDate": 0}}
    ).provisional_entry_candidate.tolist() == [False, True]


def test_invalid_interval_does_not_generate_synthetic_payments():
    old = pd.DataFrame(
        {"event_timestamp_ms": [0, 8 * HOUR], "funding_interval_hours": [np.nan, np.nan]}
    )
    assert nominal_breaks("X", old, []) == []


def test_sparse_requested_months_are_not_treated_as_a_continuous_source_series():
    from crypto_factor_research.capacity import breaks_in_job

    old = pd.DataFrame(
        {
            "event_timestamp_ms": [0, 4 * HOUR, 100 * DAY, 100 * DAY + 4 * HOUR],
            "funding_interval_hours": [4.0] * 4,
        }
    )
    jobs = [
        {"symbol": "X", "start_ms": 0, "stop_ms": 4 * HOUR},
        {"symbol": "X", "start_ms": 100 * DAY, "stop_ms": 100 * DAY + 4 * HOUR},
    ]
    assert not [row for job in jobs for row in breaks_in_job(job, old, [])]
