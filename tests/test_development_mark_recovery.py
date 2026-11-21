import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import recover_development_marks as recovery  # noqa: E402

STAMP = 1659225600000  # 2022-07-31 UTC


def job():
    return {"symbol": "BTCUSDT", "date": "2022-07-31", "targets": [STAMP], "overlaps": {}}


def payload(stamp=STAMP):
    return [stamp, "100", "102", "99", "101", "0", stamp + recovery.HOUR - 1,
            "0", 0, "0", "0", "0"]


def row():
    return {"instrument_id": "BTCUSDT", "bar_open_ms": STAMP,
            "bar_open_time": datetime.fromtimestamp(STAMP / 1000, UTC),
            "bar_close_ms": STAMP + recovery.HOUR - 1,
            "open": 100., "high": 102., "low": 99., "close": 101.,
            "open_raw": "100", "high_raw": "102", "low_raw": "99", "close_raw": "101",
            "historical_strategy_eligible": False, "publication_time_proven": False}


@pytest.mark.parametrize(("stamp", "marks", "expected"), [
    (0, {}, "whole_month_absent"), (0, {1: {}}, "leading"),
    (2, {1: {}}, "trailing"), (1, {0: {}, 2: {}}, "interior"),
])
def test_gap_classification(stamp, marks, expected):
    assert recovery.classify(stamp, marks) == expected


def test_exact_recovered_and_remaining_partition():
    item = job()
    item["targets"].append(STAMP + recovery.HOUR)
    assert recovery.validate_overlay([row()], [item]) == [("BTCUSDT", STAMP + recovery.HOUR)]
    with pytest.raises(ValueError, match="Duplicate/unplanned"):
        recovery.validate_overlay([row(), row()], [item])


@pytest.mark.parametrize("failure", ["wrong_price", "infinite", "close_time", "open_time", "eligible"])
def test_bad_overlay_never_passes_readback(failure):
    item = row()
    if failure == "wrong_price":
        item["close"] = 103
    elif failure == "infinite":
        item["close"] = float("inf")
    elif failure == "close_time":
        item["bar_close_ms"] += 1
    elif failure == "open_time":
        item["bar_open_time"] = datetime(2021, 1, 1, tzinfo=UTC)
    else:
        item["historical_strategy_eligible"] = True
    with pytest.raises(ValueError):
        recovery.validate_overlay([item], [job()])


def test_overlap_conflict_blocks_entire_day():
    item = job()
    item["overlaps"] = {str(STAMP): {"open": "100", "high": "102", "low": "99", "close": "100"}}
    with pytest.raises(ValueError, match="conflict"):
        recovery.checked_rows({"values": [payload()]}, item)


def test_partial_official_source_does_not_invent_missing_rows():
    item = job()
    item["targets"].append(STAMP + recovery.HOUR)
    result = recovery.checked_rows({"values": [payload()]}, item)
    assert len(result) == 1 and result[0]["timestamp_ms"] == STAMP


def test_oos_targets_and_duplicate_targets_rejected():
    bad = job()
    bad["targets"] = [1735689600000]
    with pytest.raises(ValueError, match="development"):
        recovery.validate_overlay([], [bad])
    with pytest.raises(ValueError, match="Duplicate target"):
        recovery.validate_overlay([], [job(), job()])


def prepare(tmp_path):
    directory, cache, export = (tmp_path / name for name in ("run", "cache", "export"))
    directory.mkdir()
    recovery.write(directory / "plan.json", {"jobs": [job()], "target_hours": 1})
    return directory, cache, export


def test_403_stops_before_export_and_records_outcome(tmp_path, monkeypatch):
    directory, cache, export = prepare(tmp_path)
    monkeypatch.setattr(recovery, "daily_source", lambda *args: {
        "success": False, "new_requests": 1, "error": "HTTP Error 403: Forbidden"})
    with pytest.raises(RuntimeError, match="stopped"):
        recovery.recover(directory, cache, export)
    assert (directory / "source_outcomes.json").exists()
    assert not export.exists()


def test_terminal_404_is_not_blindly_retried_and_missing_keys_remain(tmp_path, monkeypatch):
    directory, cache, export = prepare(tmp_path)
    key = recovery.hashlib.sha256(b"BTCUSDT:2022-07-31").hexdigest()
    recovery.write(cache / "daily" / key / "result.json", {
        "success": False, "new_requests": 1, "error": "HTTP Error 404: Not Found"})
    monkeypatch.setattr(recovery, "daily_source", lambda *args: pytest.fail("Unexpected HTTP retry"))
    recovery.recover(directory, cache, export)
    manifest = json.loads((export / "manifest.json").read_text())
    assert not manifest["recovery_complete"] and manifest["unresolved_hours"] == 1
    assert recovery.pq.read_table(export / "mark_gap_overlay.parquet").num_rows == 0


def test_previously_successful_corrupt_cache_is_fatal(tmp_path, monkeypatch):
    directory, cache, export = prepare(tmp_path)
    key = recovery.hashlib.sha256(b"BTCUSDT:2022-07-31").hexdigest()
    recovery.write(cache / "daily" / key / "result.json", {"success": True})
    monkeypatch.setattr(recovery, "daily_source", lambda *args: {
        "success": False, "new_requests": 0, "error": "cached daily source metadata mismatch"})
    with pytest.raises(ValueError, match="integrity"):
        recovery.recover(directory, cache, export)
    assert not export.exists()
