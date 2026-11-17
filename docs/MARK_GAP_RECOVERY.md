# Mark Gap Recovery Result

Date: 2026-11-17. Primary protocol `b8991bb`; separately registered daily fallback
`e1439b8`. No strategy returns, fitting, trading, interpolation or data deletion.

## Outcome

Recovered 33,168 of 33,240 exact audited mark symbol-hours (99.78%), with zero
source conflicts. All four common gaps are fully covered: 33,096 symbol-hours,
zero unresolved keys. The unchanged full-recovery gate does NOT pass: 72 hours
across seven identifiers remain absent/incomplete in the tested official sources.
Do not describe the entire mark history as complete or historically tradable.

| Stage | Validated rows | Remaining hours | Outcome |
|---|---:|---:|---|
| Frozen source/seed plan | 534 staged candidates | 32,706 | Revalidated before use |
| Primary mark API recovery | 32,808 | 432 in 19 ranges | Full gate failed |
| Official daily ZIP fallback | 33,168 | 72 in 7 ranges | Full gate still failed |

The primary run made 1,155 globally paced API calls; 12 completely seeded ranges
required none. A separate two-range pilot recovered 48 keys and then re-used both
payloads with zero requests and a byte-identical JSONL overlay.

Daily fallback retrieved 53 official ZIPs plus CHECKSUM files (106 HTTP requests,
40,972 compressed ZIP bytes), all checksum-verified. It added 360 unique rows.
A complete daily-cache re-run made zero requests and reproduced the identical
overlay SHA-256. This is source recovery, not observed strategy performance.

## Remaining keys: keep missing, never synthesize

| Identifier | Month | Unresolved mark hours | Also absent from trade bars |
|---|---|---:|---:|
| AERGOUSDT | 2025-04 | 11 | 11 |
| CTKUSDT | 2025-04 | 11 | 10 |
| CVCUSDT | 2025-05 | 9 | 8 |
| CVXUSDT | 2025-07 | 9 | 9 |
| LITUSDT | 2025-12 | 16 | 16 |
| PUMPUSDT | 2025-07 | 7 | 7 |
| SLPUSDT | 2025-07 | 9 | 9 |

70 of the 72 unresolved mark hours also lack trade bars. This supports prioritizing
contract lifecycle/session/source-history investigation, but does NOT prove the
cause or authorize an inferred delisting date. Empty/partial responses are not
network failures; blind retries, zero fills and forward fills cannot create a
verified historical mark.

Recovered rows include 24 mark observations after the known WAVES settlement and
3,192 after each identifier's last observed positive-volume trade. These ex-post
audit flags are preserved, never used to revive eligibility or retroactively select
a historical portfolio. All overlay rows have historical_strategy_eligible=false.

## New versioned partial overlay

Shared data root:

```text
data/canonical/binance_um_mark_recovery/v20261117_001_partial/
  mark_gap_overlay.parquet
  manifest.json
  quality_mask.json
```

Only this NEW version was written. Existing raw, sibling backfills and canonical
datasets were not overwritten or silently merged. The Parquet has Float64 prices
plus exact decimal-string columns, UTC millisecond timestamps, source URL/hash/
retrieval/payload references and lifecycle-review flags. No volume was invented.
The manifest explicitly records recovery_complete=false and unresolved_hours=72.

Independent full-row validation confirms:

- 33,168 unique Parquet keys equal the verified source JSONL keys;
- recovered keys and the 72-key missing mask exactly partition the frozen targets;
- every raw decimal string/numeric price, hourly timestamp, source hash/URL and
  audit flag survives the Parquet round trip unchanged;
- all 33,096 common-gap targets are present; no out-of-target rows;
- quality_mask.json preserves the missing-key list and validation linked to the
  export-manifest hash. Structural validation passes while recovery remains partial.

Parquet SHA-256:
`01c261dbcb8adf7e1b1123983132ee8c166c81082aedc654315054538ac93926`.
Verified JSONL SHA-256:
`1f1b6a6f8a945bd5f577717a59fbab3df2a557ac720635e93b61637e30cf6cfc`.

## Tools, evidence and environment

- Plan: `data/interim/usdm_universe/mark_recovery_plan_20261117.json`.
- Primary: `data/interim/usdm_universe/mark_recovery_full_20261117/`.
- Daily fallback: `data/interim/usdm_universe/mark_recovery_daily_20261117/`.
- Final validation: daily directory `final_validation.json`.
- Logs: `reports/acquisition/mark_recovery_20261117.log`,
  `mark_recovery_daily_20261117.log`, `mark_recovery_daily_resume_20261117.log`.
- Reusable tools: `recover_mark_gaps.py` (plan/run/export),
  `recover_mark_daily.py`, `validate_mark_overlay.py` under scripts/.
- 44 tests pass, including source corruption, partial replies, overlap conflicts,
  exact keys, partial-export labeling, non-overwrite and platform locking.
- Ruff 0.17.5 checks/format validation use the same version as the original runtime.

Primary execution used WSL. Subsequent WSL service launches timed out with
WSAETIMEDOUT; no service was restarted. Daily recovery, readback validation and
export used the existing Windows Python 3.11/PyArrow installation through the same
shared filesystem. A matching Ruff executable was installed only in ignored
data/interim/tooling/ruff_windows, without changing system packages. Windows UNC
byte locks were unsupported, so same-runtime Windows writers use a named mutex;
Linux retains flock. Do NOT run both platform variants against one output at once.

## Reproduction (WSL, when available)

```bash
bash scripts/run_usdm_acquisition.sh mark-recover
bash scripts/run_usdm_acquisition.sh mark-daily
bash scripts/run_usdm_acquisition.sh summary
```

The first two commands intentionally exit nonzero while 72 hours remain. They
verify successful cached evidence and retry failed requests; do not repeatedly run
them expecting absent observations to become data. No automatic retry loop exists.

To export a NEW explicitly partial version (never use the existing output path):

```bash
../funding_carry/.venv/bin/python scripts/recover_mark_gaps.py export \
  --recovery-dir data/interim/usdm_universe/mark_recovery_daily_20261117 \
  --output-dir ../../data/canonical/binance_um_mark_recovery/<NEW_VERSION> \
  --allow-partial

../funding_carry/.venv/bin/python scripts/validate_mark_overlay.py \
  --plan data/interim/usdm_universe/mark_recovery_plan_20261117.json \
  --recovery-dir data/interim/usdm_universe/mark_recovery_daily_20261117 \
  --version-dir ../../data/canonical/binance_um_mark_recovery/<NEW_VERSION> \
  --audit-dir data/interim/usdm_universe/audit_20261117
```

## Next boundary

Normalize archive rows plus this explicit overlay into versioned research tables,
preserving the 72-key quality mask. Investigate lifecycle facts for those seven
identifiers, the 54 funding-after-activity cases and the funding-month-gap identities.
Trade-gap repair and causal trading eligibility remain separate work. No strategy
performance inspection follows automatically from source recovery.
