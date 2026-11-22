"""Benchmark valuation needs execution and daily marks, not unused intraday bars."""

import hashlib
import json
import zipfile

import pytest

from crypto_factor_research.config import DAY, HOUR
from crypto_factor_research.window_data import ms
from crypto_factor_research.window_report import spot_benchmark


def source(tmp_path, missing=None):
    start = ms("2023-01-01")
    folder = tmp_path / "spot" / "BTCUSDT" / "2023-01"
    folder.mkdir(parents=True)
    keys = {start + HOUR, start + DAY - HOUR, start + 2 * DAY - 2 * HOUR}
    rows = [f"{t},100,100,100,100,1,0,100\n" for t in sorted(keys) if t != missing]
    archive = folder / "archive.zip"
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr("BTCUSDT-1h-2023-01.csv", "".join(rows))
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    (folder / "source.json").write_text(json.dumps({"sha256": digest}))
    (folder / "checksum.txt").write_text(digest + " archive.zip\n")
    config = {"start": "2023-01-01", "stop_exclusive": "2023-01-04", "spot_root": "spot"}
    return config, start


def test_unused_intraday_gaps_do_not_block_benchmark(tmp_path):
    config, start = source(tmp_path)
    frame, _ = spot_benchmark(tmp_path, config, "BTCUSDT", start, start + 2 * DAY)
    assert len(frame) == 3
    assert frame.nav.iloc[0] == 100000
    assert frame.nav.iloc[1] == pytest.approx(100000 / (1.0005 * 1.001))
    assert frame.nav.iloc[2] == pytest.approx(100000 * 0.9995 * 0.999 / (1.0005 * 1.001))


@pytest.mark.parametrize("offset", [HOUR, DAY - HOUR, 2 * DAY - 2 * HOUR])
def test_required_execution_or_daily_mark_still_blocks(tmp_path, offset):
    config, start = source(tmp_path, ms("2023-01-01") + offset)
    with pytest.raises(ValueError, match="Spot required prices missing: BTCUSDT, count=1"):
        spot_benchmark(tmp_path, config, "BTCUSDT", start, start + 2 * DAY)
