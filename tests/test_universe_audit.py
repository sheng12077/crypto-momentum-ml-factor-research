"""All-identifier accounting is mandatory even when input verification fails."""

import importlib.util
import json
from pathlib import Path
import pandas as pd
import pytest

spec = importlib.util.spec_from_file_location(
    "universe_audit", Path(__file__).resolve().parents[1] / "tools/audit_universe_coverage.py"
)
audit_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit_module)


def inputs(tmp_path):
    root = tmp_path / "daily_source"
    (root / "daily").mkdir(parents=True)
    (root / "index").mkdir()
    (root / "manifest.json").write_text(json.dumps({"identifiers": 2}))
    for symbol, flags in [("OLD", [False, False]), ("NEW", [False, True])]:
        frame = pd.DataFrame(
            {
                "instrument_id": symbol,
                "data_day": ["2022-01-01", "2022-01-02"],
                "trade_hours": [0, 24],
                "mark_hours": [0, 24],
                "trade_volume_sum": [0.0, 10.0],
                "price_funding_data_candidate": flags,
                "base_failure_mask": [1 | 2 | 8, 0],
                "episode_number": [0, 1],
                "known_equity_episode": False,
                "lifecycle_origin_unverified": True,
            }
        )
        path = root / "daily" / (symbol + ".parquet")
        frame.to_parquet(path, index=False)
        (root / "index" / (symbol + ".json")).write_text(
            json.dumps(
                {"instrument_id": symbol, "daily_sha256": audit_module.digest(path), "rows": 2}
            )
        )
    cohort = tmp_path / "cohort.json"
    cohort.write_text(json.dumps({"symbols": ["OLD"]}))
    return root, cohort, tmp_path / "output"


def test_new_identifiers_accounted_without_fixed_cohort_gate(tmp_path):
    root, cohort, out = inputs(tmp_path)
    audit_module.audit(root, cohort, out)
    summary = json.loads((out / "summary.json").read_text())
    frame = pd.read_csv(out / "assets.csv").set_index("instrument_id")
    assert summary["identifiers_accounted"] == 2 and summary["input_files_verified"] == 2
    assert summary["legacy_candidates_outside_old_cohort"] == 1
    assert frame.loc["NEW", "old_backtest_disposition"] == "never_considered_by_fixed_cohort"
    assert frame.loc["NEW", "legacy_price_funding_candidate_ever"]
    assert frame.loc["NEW", "legacy_flag_days_trade_day_incomplete"] == 0
    assert not summary["new_dynamic_universe_built"] and not summary["PnL_computed"]


def test_every_corrupt_identifier_remains_in_ledger(tmp_path):
    root, cohort, out = inputs(tmp_path)
    for path in (root / "index").glob("*.json"):
        index = json.loads(path.read_text())
        index["daily_sha256"] = "bad"
        path.write_text(json.dumps(index))
    with pytest.raises(SystemExit):
        audit_module.audit(root, cohort, out)
    summary = json.loads((out / "summary.json").read_text())
    assert summary["identifiers_accounted"] == 2 and len(summary["errors"]) == 2
    assert summary["input_files_verified"] == 0
    assert len(pd.read_csv(out / "assets.csv")) == 2


def test_missing_input_file_cannot_be_silently_ignored(tmp_path):
    root, cohort, out = inputs(tmp_path)
    (root / "daily/NEW.parquet").unlink()
    with pytest.raises(ValueError, match="inventory does not reconcile"):
        audit_module.audit(root, cohort, out)
