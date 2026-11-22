"""Missing API observations must never be reinterpreted as zero funding."""

import json

import pandas as pd
import pytest

from crypto_factor_research.config import HOUR, sha
from crypto_factor_research.funding_evidence import audit_breaks, compare_records


def rows(interior=False):
    result = [
        {"symbol": "A", "fundingTime": 0, "fundingRate": "0.0001"},
        {"symbol": "A", "fundingTime": 8 * HOUR, "fundingRate": "0.0002"},
    ]
    if interior:
        result.insert(1, {"symbol": "A", "fundingTime": 4 * HOUR, "fundingRate": "-0.0003"})
    return result


def test_no_interior_record_is_only_an_observed_gap():
    result = compare_records("A", (0, 0.0001), (8 * HOUR, 0.0002), rows())
    assert result["status"] == "api_has_same_observed_gap"
    assert result["interior_event_times_ms"] == []


def test_additional_api_record_is_identified_without_auto_integration():
    result = compare_records("A", (0, 0.0001), (8 * HOUR, 0.0002), rows(True))
    assert result["status"] == "api_has_additional_events"
    assert result["interior_event_times_ms"] == [4 * HOUR]


def test_anchor_disagreement_and_empty_api_are_not_certified():
    assert compare_records("A", (0, 0.001), (8 * HOUR, 0.0002), rows())["status"] == (
        "api_anchors_disagree"
    )
    assert compare_records("A", (0, 0.0001), (8 * HOUR, 0.0002), [])["status"] == (
        "api_anchors_disagree"
    )


@pytest.mark.parametrize(
    "bad",
    [
        {"symbol": "B", "fundingTime": 4 * HOUR, "fundingRate": ".01"},
        {"symbol": "A", "fundingTime": 20 * HOUR, "fundingRate": ".01"},
        {"symbol": "A", "fundingTime": 4 * HOUR, "fundingRate": "nan"},
        {"symbol": "A", "fundingTime": 0, "fundingRate": ".0001"},
    ],
)
def test_bad_api_records_fail_validation(bad):
    with pytest.raises(ValueError):
        compare_records("A", (0, 0.0001), (8 * HOUR, 0.0002), rows() + [bad])


def test_audit_deduplicates_cases_and_preserves_strategy_inputs(tmp_path):
    run = tmp_path / "run"
    run.mkdir()
    funding = run / "funding.parquet"
    pd.DataFrame(
        {
            "instrument_id": ["A", "A"],
            "event_timestamp_ms": [0, 8 * HOUR],
            "funding_rate": [0.0001, 0.0002],
        }
    ).to_parquet(funding, index=False)
    digest = sha(funding)
    (run / "manifest.json").write_text(json.dumps({"output_hashes": {funding.name: digest}}))
    problem = {"symbol": "A", "timestamp_ms": 0, "reason": "unresolved_observed_schedule_break"}
    (run / "preflight_problems.json").write_text(json.dumps([problem, problem]))

    class Client:
        calls = 0

        def get(self, url):
            self.calls += 1
            return json.dumps(rows()).encode(), {"fixture": True}

    client = Client()
    summary = audit_breaks(tmp_path, run, client=client)
    assert summary["success"] and client.calls == 1
    assert summary["unique_saved_breaks"] == 1 and summary["full_scope"]
    assert summary["strategy_records_modified"] == 0
    assert not summary["financial_execution_ready"]
    assert summary["status_counts"] == {"api_has_same_observed_gap": 1}
    assert sha(funding) == digest


def test_modified_funding_input_blocks_evidence_audit(tmp_path):
    run = tmp_path / "run"
    run.mkdir()
    (run / "preflight_problems.json").write_text("[]")
    (run / "funding.parquet").write_text("changed")
    (run / "manifest.json").write_text(
        json.dumps(
            {
                "output_hashes": {"funding.parquet": "wrong"},
            }
        )
    )
    with pytest.raises(ValueError, match="Prepared funding source changed"):
        audit_breaks(tmp_path, run)
