"""Small offline checks only;no historical training or simulation."""

import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

from crypto_factor_research.config import DAY, HOUR, sha
from crypto_factor_research.first_window import (
    held_intervals,
    main_stage,
    ranked_schedule,
    training_rows,
)
from crypto_factor_research.window_data import episode_notice, ms, read_market, window_label

ROOT = Path(__file__).resolve().parents[1]


def test_strategy_parameters_are_unchanged():
    old = json.loads((ROOT / "config/dynamic_first_window.json").read_text())
    new = json.loads((ROOT / "config/dynamic_2023.json").read_text())
    for key in [
        "features",
        "model_parameters",
        "rebalance_weeks",
        "minimum_candidates",
        "positions_each_side",
        "random_seeds",
        "slippage_bps",
    ]:
        assert old[key] == new[key]
    assert new["train_stop"] == new["start"] == "2023-01-01"
    assert window_label(new) == "train2021-2022/trade2023"


def test_schedule_uses_2023_mondays():
    t = ms("2023-01-02")
    f = pd.DataFrame(
        {
            "instrument_id": [f"A{i:02}" for i in range(20)],
            "feature_cutoff_ms": t,
            "score": range(20),
        }
    )
    result = ranked_schedule(f, 2023, weeks=2)
    assert len(result) == 26 and list(result)[0] == "2023-01-02"
    assert len(result["2023-01-02"]) == 10
    assert all(day.startswith("2023-") for day in result)


def test_2022_labels_crossing_2023_cutoff_are_purged():
    class Data:
        notices = {}

        def vwap(self, symbol, t):
            return 100 + t / DAY

    cutoff = ms("2023-01-01")
    frame = pd.DataFrame(
        {"instrument_id": ["A", "A"], "feature_cutoff_ms": [cutoff - 10 * DAY, cutoff - 2 * DAY]}
    )
    train, _ = training_rows(frame, Data(), cutoff)
    assert len(train) == 1 and train.label_available_ms.max() < cutoff


def test_verified_new_episode_can_reenter_without_old_exit_truncation():
    t = ms("2023-01-02")
    notice = {
        "blocked_from_ms": t - 20 * DAY,
        "exit_ms": t - 19 * DAY,
        "effective_ms": t - 18 * DAY,
        "valid_to_ms": t - DAY,
    }
    assert episode_notice({"A": notice}, "A", t - 2 * DAY) == notice
    assert episode_notice({"A": notice}, "A", t) is None
    spans = held_intervals({"2023-01-02": {"A": 0.1}}, {"A": notice}, t, t + 5 * DAY)
    assert spans["A"] == [(t + 2 * HOUR, t + 5 * DAY - HOUR)]


@pytest.mark.parametrize("with_overlay", [False, True])
def test_market_reader_includes_2023_but_not_2024(tmp_path, with_overlay):
    daily = tmp_path / "daily"
    hourly = tmp_path / "hourly"
    (daily / "index").mkdir(parents=True)
    (hourly / "index").mkdir(parents=True)
    sources = {}
    for month in ["2022-12", "2023-01", "2024-01"]:
        t = ms(month + "-01")
        for kind, product in [
            ("trade", "klines"),
            ("mark", "markPriceKlines"),
            ("funding", "fundingRate"),
        ]:
            suffix = f"X-fundingRate-{month}.zip" if kind == "funding" else f"1h/X-1h-{month}.zip"
            key = f"data/futures/um/monthly/{product}/X/{suffix}"
            rel = f"observations/{kind}/X/{month}.parquet"
            path = hourly / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            value = (
                {
                    "instrument_id": ["X"],
                    "event_timestamp_ms": [t],
                    "funding_rate": [0.001],
                    "funding_interval_hours": [8.0],
                }
                if kind == "funding"
                else {
                    "instrument_id": ["X"],
                    "bar_open_ms": [t],
                    **{
                        name: [1.0]
                        for name in [
                            "open",
                            "high",
                            "low",
                            "close",
                            "volume",
                            "quote_volume",
                            "taker_buy_volume",
                            "taker_buy_quote_volume",
                        ]
                    },
                }
            )
            pd.DataFrame(value).to_parquet(path, index=False)
            meta = {
                "relative_path": rel,
                "parquet_sha256": sha(path),
                "raw_sha256": "fixture",
                "rows": 1,
            }
            idx = hourly / "index" / (hashlib.sha256(key.encode()).hexdigest() + ".json")
            idx.write_text(json.dumps(meta))
            sources[key] = {
                "parquet_sha256": sha(path),
                "raw_sha256": "fixture",
                "index_sha256": sha(idx),
            }
    (daily / "index/X.json").write_text(json.dumps({"sources": sources}))
    repair = tmp_path / "repair"
    repair.mkdir()
    overlay = repair / "deduplicated_observations.jsonl"
    overlay.write_text("")
    if with_overlay:
        stamp = ms("2023-01-01") + HOUR
        source = repair / "source.json"
        source.write_text("verified fixture")
        overlay.write_text(
            json.dumps(
                {
                    "symbol": "X",
                    "kind": "trade",
                    "timestamp_ms": stamp,
                    "source": {"path": str(source), "sha256": sha(source)},
                    "values": [
                        stamp,
                        2.0,
                        2.0,
                        2.0,
                        2.0,
                        3.0,
                        stamp + HOUR - 1,
                        6.0,
                        1,
                        1.0,
                        2.0,
                        0,
                    ],
                }
            )
            + "\n"
        )
    (repair / "assessment.json").write_text(
        json.dumps({"output_hashes": {overlay.name: sha(overlay)}})
    )
    market, _ = read_market(
        tmp_path,
        {
            "daily_root": "daily",
            "hourly_root": "hourly",
            "repair_run": "repair",
            "train_start": "2021-01-01",
            "stop_exclusive": "2024-01-01",
        },
        {"X"},
    )
    expected = [ms("2022-12-01"), ms("2023-01-01")]
    if with_overlay:
        expected.append(ms("2023-01-01") + HOUR)
        assert market["trade"].iloc[-1].quote_volume == 6.0
    assert market["trade"].bar_open_ms.tolist() == expected
    assert len(market["funding"]) == 2
    assert list(market["trade"].columns) == [
        "instrument_id",
        "bar_open_ms",
        "close",
        "volume",
        "quote_volume",
    ]
    assert list(market["mark"].columns) == ["instrument_id", "bar_open_ms", "close"]
    assert isinstance(market["trade"].instrument_id.dtype, pd.CategoricalDtype)


def test_saved_run_can_be_summarized_without_loading_or_fitting(tmp_path, capsys):
    config = tmp_path / "config.json"
    config.write_text(json.dumps({"train_stop": "2023-01-01", "start": "2023-01-01"}))
    run = tmp_path / "saved"
    run.mkdir()
    (run / "manifest.json").write_text(json.dumps({"identity": {"config_sha256": sha(config)}}))
    (run / "report_summary.json").write_text(
        json.dumps({"success": True, "window": "fixture", "source_bindings": {"hidden": "large"}})
    )
    assert main_stage(tmp_path, config, "summary", run)["success"]
    assert "source_bindings" not in capsys.readouterr().out
    with pytest.raises(ValueError, match="read/report only"):
        main_stage(tmp_path, config, "all", run)
