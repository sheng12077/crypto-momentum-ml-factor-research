#!/usr/bin/env bash
# WSL/Linux, Python >=3.12; no third-party packages required.
set -euo pipefail
task_repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$task_repo_root"
task_data_root="$(cd ../.. && pwd)/data"
task_census_dir="data/interim/usdm_universe/census_full_20261117"
task_download_dir="data/interim/usdm_universe/download_full_20261117"
task_audit_dir="data/interim/usdm_universe/audit_20261117"
task_mark_plan="data/interim/usdm_universe/mark_recovery_plan_20261117.json"
task_mark_primary="data/interim/usdm_universe/mark_recovery_full_20261117"
task_mark_daily="data/interim/usdm_universe/mark_recovery_daily_20261117"
mkdir -p reports/acquisition

case "${1:-}" in
  census)
    python3 scripts/acquire_usdm_universe.py census \
      --seed-summary data/interim/universe_feasibility/20261117_metadata_pilot/summary.json \
      --output-dir "$task_census_dir" \
      --workers "${USDM_WORKERS:-4}" \
      2>&1 | tee -a reports/acquisition/census_20261117.log
    ;;
  download)
    : "${USDM_MAX_GIB:?Set USDM_MAX_GIB to an explicit compressed ZIP budget}"
    python3 scripts/acquire_usdm_universe.py download \
      --plan "$task_census_dir/download_plan.json" \
      --data-root "$task_data_root" \
      --output-dir "$task_download_dir" \
      --max-gib "$USDM_MAX_GIB" \
      --workers "${USDM_WORKERS:-4}" \
      2>&1 | tee -a reports/acquisition/download_20261117.log
    ;;
  audit)
    python3 scripts/audit_usdm_acquisition.py \
      --census-dir "$task_census_dir" \
      --download-dir "$task_download_dir" \
      --data-root "$task_data_root" \
      --output-dir "$task_audit_dir" \
      --workers "${USDM_WORKERS:-4}" \
      2>&1 | tee -a reports/acquisition/audit_20261117.log
    ;;
  mark-recover)
    python3 scripts/recover_mark_gaps.py run \
      --plan "$task_mark_plan" --output-dir "$task_mark_primary" \
      --workers "${MARK_RECOVERY_WORKERS:-2}" \
      2>&1 | tee -a reports/acquisition/mark_recovery_20261117.log
    ;;
  mark-daily)
    python3 scripts/recover_mark_daily.py \
      --plan "$task_mark_plan" --primary-dir "$task_mark_primary" \
      --output-dir "$task_mark_daily" \
      2>&1 | tee -a reports/acquisition/mark_recovery_daily_resume_20261117.log
    ;;
  summary)
    python3 - "$task_census_dir/summary.json" "$task_download_dir/summary.json" "$task_audit_dir/summary.json" "$task_mark_primary/summary.json" "$task_mark_daily/summary.json" <<'PY'
import json
import pathlib
import sys
for value in sys.argv[1:]:
    path = pathlib.Path(value)
    print(path)
    if path.exists():
        report = json.loads(path.read_text())
        if len(report.get("errors", [])) > 5:
            report["error_count"] = len(report["errors"])
            report["errors"] = report["errors"][:5]
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("not completed yet")
PY
    ;;
  *)
    echo 'Usage: bash scripts/run_usdm_acquisition.sh {census|download|audit|mark-recover|mark-daily|summary}' >&2
    exit 2
    ;;
esac
