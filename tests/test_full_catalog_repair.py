"""Official-source validation, conflicts and verified resume without network."""

import json

import pandas as pd
import pytest

from crypto_factor_research import repair
from crypto_factor_research.config import HOUR, sha


def job(kind="trade"):
    return {
        "symbol": "TESTUSDT",
        "kind": kind,
        "start_ms": 0,
        "stop_ms": 24 * HOUR,
        "job_id": "test",
        "baselines": {},
    }


def bar(t=0):
    return [t, "100", "102", "99", "101", "10", t + HOUR - 1, "1000", 5, "6", "600", "0"]


def test_kline_bounds_and_duplicate_validation():
    assert len(repair.parse_klines([bar()], job())) == 1
    with pytest.raises(ValueError, match="Duplicate"):
        repair.parse_klines([bar(), bar()], job())
    broken = bar()
    broken[10] = "1001"
    with pytest.raises(ValueError, match="bounds"):
        repair.parse_klines([broken], job())
    with pytest.raises(ValueError, match="timestamp"):
        repair.parse_klines([bar(1)], job())


def test_funding_identity_and_missing_response_are_explicit():
    j = job("funding")
    assert repair.parse_funding([], j) == []
    with pytest.raises(ValueError, match="mismatch"):
        repair.parse_funding([{"symbol": "OTHER", "fundingTime": 0, "fundingRate": "0.1"}], j)
    with pytest.raises(ValueError, match="mismatch"):
        repair.parse_funding([{"symbol": "TESTUSDT", "fundingTime": 0, "fundingRate": "NaN"}], j)


def test_existing_observation_conflict_is_reported(tmp_path):
    p = tmp_path / "old.parquet"
    pd.DataFrame(
        {"event_timestamp_ms": [0], "funding_rate": [0.01], "funding_interval_hours": [8.0]}
    ).to_parquet(p, index=False)
    j = job("funding")
    j["baselines"] = {str(p): sha(p)}
    additions, conflicts = repair.compare_observations(j, [{"timestamp_ms": 0, "rate": 0.02}], {})
    assert not additions and conflicts == [0]


def test_missing_funding_interval_is_not_fabricated():
    additions, conflicts = repair.compare_observations(
        job("funding"), [{"timestamp_ms": 0, "rate": 0.01}], {}
    )
    assert not conflicts and additions[0]["funding_interval_hours"] is None
    assert additions[0]["interval_evidence"] == "unverified"


def test_resume_rechecks_raw_body_and_metadata(tmp_path, monkeypatch):
    calls = []

    def fake(url, folder, gate):
        calls.append(url)
        folder.mkdir(parents=True, exist_ok=True)
        p = folder / "test.raw"
        p.write_bytes(b"[]")
        return p.read_bytes(), {"url": url, "path": str(p), "sha256": sha(p)}

    monkeypatch.setattr(repair, "request", fake)
    j = job("funding")
    first = repair.verify_job(j, tmp_path, repair.RateGate(0), {})
    assert first["status"] == "official_response_no_new_observations"
    assert repair.verify_job(j, tmp_path, repair.RateGate(0), {})["cache_hit"]
    assert len(calls) == 1
    (tmp_path / "jobs/test/responses/test.raw").write_bytes(b"changed")
    with pytest.raises(ValueError, match="body changed"):
        repair.verify_job(j, tmp_path, repair.RateGate(0), {})


def test_archive_name_identity_is_checked(tmp_path):
    import io
    import zipfile

    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        z.writestr("OTHER-1h-1970-01-01.csv", "")
    with pytest.raises(ValueError, match="filename"):
        repair.unzip_daily(b.getvalue(), job())


def test_complete_plan_keeps_blank_csv_fields_json_safe(tmp_path):
    from test_full_universe_inputs import fixture_sources

    from crypto_factor_research.reporting import review_inputs
    from crypto_factor_research.universe import build_inputs

    spec = fixture_sources(tmp_path)
    path = tmp_path / "daily/daily/NEW.parquet"
    f = pd.read_parquet(path)
    f.loc[0, "trade_hours"] = 12
    f.loc[0, "imbalance_inputs_valid"] = False
    f.to_parquet(path, index=False)
    ipath = tmp_path / "daily/index/NEW.json"
    meta = json.loads(ipath.read_text())
    meta["daily_sha256"] = sha(path)
    ipath.write_text(json.dumps(meta))
    _, dataset = build_inputs(spec)
    review_inputs(dataset, tmp_path, tmp_path / "review")
    (tmp_path / "experiments").mkdir()
    (tmp_path / "experiments/018_full_catalog_source_repair.md").write_text("Registered")
    output = repair.make_plan(tmp_path, dataset, tmp_path / "review")
    plan = json.loads((output / "plan.json").read_text())
    assert len(plan["cases"]) == 1 and not plan["jobs"]
    plan["cases"].append(
        {
            "case_id": "stopped",
            "instrument_id": "OLD",
            "issue": "regular_execution_review",
            "job_ids": [],
            "initial_disposition": "known_effective_stop",
        }
    )
    repair.write_json(output / "plan.json", plan)
    repair.run_repairs(tmp_path, output)
    from crypto_factor_research.repair_assessment import assess_repairs

    assessed = assess_repairs(tmp_path, output)
    assert assessed["all_cases_accounted"]
    assert assessed["verified_disposition_counts"]["known_effective_stop"] == 1


def test_required_key_closure_does_not_confuse_some_rows_with_complete_coverage():
    from crypto_factor_research.repair_assessment import classify_required_hours

    state, missing = classify_required_hours([0, HOUR, 2 * HOUR], {0}, {HOUR})
    assert state == "required_keys_still_missing" and missing == [2 * HOUR]
    assert classify_required_hours([0], set(), {0})[0] == "required_keys_recovered"
    assert classify_required_hours([0], {0}, set(), True)[0] == "episode_or_policy_evidence_needed"


def test_product_scope_preserves_reused_and_absent_identifiers(tmp_path):
    from crypto_factor_research.source_evidence import scope_report

    dataset = tmp_path / "dataset"
    dataset.mkdir()
    pd.DataFrame(
        {"instrument_id": ["OLD", "REUSED", "COIN"], "candidate_decisions": [1, 2, 3]}
    ).to_csv(dataset / "asset_summary.csv", index=False)
    repair.write_json(
        dataset / "manifest.json",
        {"output_hashes": {"asset_summary.csv": sha(dataset / "asset_summary.csv")}},
    )
    folder = tmp_path / "repair"
    folder.mkdir()
    repair.write_json(folder / "plan.json", {"dataset": str(dataset)})
    evidence = folder / "evidence/exchange_info"
    evidence.mkdir(parents=True)
    raw = evidence / "raw.json"
    repair.write_json(
        raw,
        {
            "symbols": [
                {"symbol": "REUSED", "underlyingType": "EQUITY", "onboardDate": 2000},
                {"symbol": "COIN", "underlyingType": "COIN"},
            ]
        },
    )
    repair.write_json(evidence / "source.json", {"path": str(raw), "sha256": sha(raw)})
    result = scope_report(tmp_path, folder)
    frame = pd.read_csv(folder / "current_product_scope.csv")
    assert set(frame.instrument_id) == {"OLD", "REUSED", "COIN"}
    assert result["current_snapshot_is_not_historical_pit_proof"]
    assert not result["whole_identifier_exclusions_applied"]
