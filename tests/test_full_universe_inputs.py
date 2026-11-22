"""Full-catalog input semantics, funding availability and source-bound end-to-end build."""

import hashlib
import json

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import pytest

from crypto_factor_research.config import DAY, HOUR, InputSpec, sha
from crypto_factor_research.features import funding_windows
from crypto_factor_research.universe import (
    REASONS,
    build_inputs,
    issue_intervals,
    states_for_symbol,
)


def frame(symbol="NEW", count=150):
    dates = pd.date_range("2021-01-01", periods=count, tz="UTC")
    return pd.DataFrame(
        {
            "instrument_id": symbol,
            "data_day": dates.strftime("%Y-%m-%d"),
            "reference_time_ms": dates.as_unit("ms").asi8 + DAY,
            "episode_number": 0,
            "close_episode_number": 0,
            "trade_hours": 24,
            "mark_hours": 24,
            "trade_close": 100.0 + np.arange(count),
            "mark_close": 100.0,
            "trade_volume_sum": 10.0,
            "trade_quote_volume_sum": 100.0,
            "taker_buy_quote_volume_sum": 60.0,
            "trade_close_valid_for_history": True,
            "imbalance_inputs_valid": True,
            "partial_lifecycle_day": False,
            "known_lifecycle_order_block": False,
            "scoped_execution_block": False,
            "known_equity_episode": False,
            "lifecycle_origin_unverified": True,
        }
    )


def funds(f):
    start = int(f.reference_time_ms.iloc[0]) - DAY
    stamps = np.arange(start, int(f.reference_time_ms.iloc[-1]), 8 * HOUR, dtype=np.int64)
    return pd.DataFrame(
        {
            "instrument_id": f.instrument_id.iloc[0],
            "event_timestamp_ms": stamps,
            "funding_rate": 0.0001,
            "funding_interval_hours": 8.0,
        }
    )


def test_new_asset_matures_without_size_or_fixed_cohort_and_marks_are_separate():
    f = frame()
    f["vendor_asset_id"] = None
    f["mark_hours"] = 0
    f["mark_close"] = np.nan
    states = states_for_symbol(f, funds(f))
    assert not states.research_candidate.iloc[:120].any()
    assert states.research_candidate.iloc[120:].all()
    assert states.missing_snapshot_mark.iloc[120:].all()
    assert not states.execution_ready.any()
    assert states.momentum120.iloc[120] == pytest.approx(2.2 - 1)


def test_hourly_funding_window_uses_availability_clock_and_excludes_cutoff_event():
    t = int(pd.Timestamp("2025-01-10", tz="UTC").timestamp() * 1000)
    stamps = np.arange(t - 7 * DAY - HOUR, t, HOUR, dtype=np.int64)
    funding = pd.DataFrame(
        {"event_timestamp_ms": stamps, "funding_rate": 0.0001, "funding_interval_hours": 1.0}
    )
    funding.loc[funding.index[-1], "funding_rate"] = 999.0
    values, flags = funding_windows(funding, np.array([t]))
    assert flags[0] == 0 and values[0] == pytest.approx(0.0168)
    broken = funding.drop(index=20).reset_index(drop=True)
    _, flags = funding_windows(broken, np.array([t]))
    assert flags[0] & 1 and flags[0] & 2


def test_gap_and_episode_reset_do_not_splice_prices():
    f = frame(count=300)
    f.loc[140, "trade_close_valid_for_history"] = False
    f.loc[200:, ["episode_number", "close_episode_number"]] = 1
    states = states_for_symbol(f, funds(f))
    assert states.history_length.iloc[141] == 1
    assert states.history_length.iloc[200] == 1
    assert np.isnan(states.momentum120.iloc[201])
    assert not states.research_candidate.iloc[141:].any()
    assert states.reason_mask.iloc[201] & REASONS["history_reset_warmup"]


def test_future_changes_do_not_change_past_candidates_or_features():
    f = frame(count=170)
    funding = funds(f)
    prior = states_for_symbol(f, funding)
    cutoff = int(f.reference_time_ms.iloc[140])
    f.loc[141:, "trade_close"] *= 100
    f.loc[141:, "taker_buy_quote_volume_sum"] = 1.0
    funding.loc[funding.event_timestamp_ms >= cutoff, "funding_rate"] = 20.0
    later = states_for_symbol(f, funding)
    pd.testing.assert_frame_equal(prior.iloc[:141], later.iloc[:141], check_exact=True)


def fixture_sources(tmp_path):
    daily = tmp_path / "daily"
    hourly = tmp_path / "hourly"
    (daily / "daily").mkdir(parents=True)
    (daily / "index").mkdir()
    (hourly / "index").mkdir(parents=True)
    (daily / "manifest.json").write_text(json.dumps({"identifiers": 2}))
    (hourly / "manifest.json").write_text(json.dumps({"success": True}))
    for symbol in ["OLD", "NEW"]:
        f = frame(symbol)
        dpath = daily / "daily" / (symbol + ".parquet")
        f.to_parquet(dpath, index=False)
        funding = funds(f)
        sources = {}
        months = pd.to_datetime(funding.event_timestamp_ms, unit="ms", utc=True).dt.strftime(
            "%Y-%m"
        )
        for month, group in funding.groupby(months):
            key = f"data/futures/um/monthly/fundingRate/{symbol}/{symbol}-fundingRate-{month}.zip"
            rel = f"observations/funding/{symbol}/{month}.parquet"
            path = hourly / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            group.to_parquet(path, index=False)
            meta = {
                "relative_path": rel,
                "rows": len(group),
                "raw_sha256": "synthetic",
                "parquet_sha256": sha(path),
            }
            ipath = hourly / "index" / (hashlib.sha256(key.encode()).hexdigest() + ".json")
            ipath.write_text(json.dumps(meta))
            sources[key] = {
                "index_sha256": sha(ipath),
                "raw_sha256": "synthetic",
                "parquet_sha256": sha(path),
            }
        index = {
            "instrument_id": symbol,
            "daily_sha256": sha(dpath),
            "rows": len(f),
            "sources": sources,
        }
        (daily / "index" / (symbol + ".json")).write_text(json.dumps(index))
    (tmp_path / "policy.json").write_text(json.dumps({"interval_exclusions": []}))
    (tmp_path / "registration.md").write_text("Synthetic registration")
    values = {
        "daily_root": "daily",
        "hourly_root": "hourly",
        "source_start": "2021-01-01",
        "source_stop": "2021-05-31",
        "decision_start": "2021-01-01",
        "decision_stop": "2021-05-31",
        "funding_lag_hours": 1,
        "funding_window_days": 7,
        "history_days": 120,
        "output_root": "features",
        "scope_policy": "policy.json",
        "registration": "registration.md",
    }
    return InputSpec(tmp_path, values)


def test_end_to_end_accounts_for_every_id_and_reuses_exact_output(tmp_path):
    spec = fixture_sources(tmp_path)
    meta, output = build_inputs(spec)
    assert meta["success"] and meta["identifiers_accounted"] == 2
    assert meta["daily_rows"] == 300 and meta["weekly_rows"] == 2 * meta["decision_dates"]
    assert meta["identifiers_ever_provisional_candidate"] == 2
    assert not meta["execution_ready"] and not meta["PnL_computed"]
    weekly = pq.read_table(output / "weekly_candidates.parquet").to_pandas()
    assert set(weekly.instrument_id) == {"OLD", "NEW"}
    reused, again = build_inputs(spec)
    assert again == output and reused["output_hashes"] == meta["output_hashes"]
    fund = next((tmp_path / "hourly/observations/funding").glob("*/*.parquet"))
    fund.write_bytes(b"bad")
    with pytest.raises(ValueError, match="cache_integrity_errors"):
        build_inputs(spec)


def test_corrupt_symbol_is_retained_and_partial_build_is_not_final_cache(tmp_path):
    spec = fixture_sources(tmp_path)
    path = tmp_path / "daily/daily/NEW.parquet"
    original = path.read_bytes()
    path.write_bytes(b"bad")
    meta, output = build_inputs(spec)
    assert (
        not meta["success"]
        and meta["identifiers_accounted"] == 2
        and len(meta["source_errors"]) == 1
    )
    assert output.parent.name == "incomplete"
    assert len(pq.read_table(output / "daily_states.parquet")) == 300
    path.write_bytes(original)
    repaired, final = build_inputs(spec)
    assert repaired["success"] and final.parent.name == "features"


def test_ordinary_initial_warmup_is_not_a_repair_job():
    f = frame()
    states = states_for_symbol(f, funds(f))
    assert issue_intervals(states, None, {"interval_exclusions": []}) == []


def test_malformed_funding_is_blocked_instead_of_imputed():
    f = frame()
    funding = funds(f)
    funding.loc[funding.index[-2], "funding_rate"] = np.nan
    states = states_for_symbol(f, funding)
    assert not states.research_candidate.iloc[-1]
    assert states.reason_mask.iloc[-1] & REASONS["invalid_or_gapped_funding_window"]
    assert np.isnan(states.funding7.iloc[-1])


def test_review_separates_listing_flow_warmup_from_missing_trading_day(tmp_path):
    from crypto_factor_research.reporting import review_inputs

    spec = fixture_sources(tmp_path)
    daily_root = tmp_path / "daily"
    for symbol, missing_day in [("NEW", 0), ("OLD", 130)]:
        path = daily_root / "daily" / (symbol + ".parquet")
        f = pd.read_parquet(path)
        f.loc[missing_day, "trade_hours"] = 12
        f.loc[missing_day, "imbalance_inputs_valid"] = False
        f.to_parquet(path, index=False)
        ipath = daily_root / "index" / (symbol + ".json")
        index = json.loads(ipath.read_text())
        index["daily_sha256"] = sha(path)
        ipath.write_text(json.dumps(index))
    _, output = build_inputs(spec)
    review_inputs(output, tmp_path, tmp_path / "review")
    queue = pd.read_csv(tmp_path / "review/reviewed_queue.csv")
    assert set(queue.loc[queue.instrument_id.eq("NEW"), "review_disposition"]) == {
        "initial_listing_flow_warmup"
    }
    assert set(queue.loc[queue.instrument_id.eq("OLD"), "review_disposition"]) == {
        "inspect_exact_trade_input_days"
    }
