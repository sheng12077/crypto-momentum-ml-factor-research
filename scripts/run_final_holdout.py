"""User-run logged orchestration of the preregistered final holdout."""
import argparse
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/interim/final_holdout/v20261122_002"
STAGES = {"prepare": "prepare_final_holdout.py", "spot": "build_final_holdout_spot.py",
          "simulate": "run_final_holdout_cases.py", "report": "report_final_holdout.py"}


def summary():
    path = BASE / "results/summary.json"
    if not path.exists():
        return {"success": False, "completed": False,
            "completed_case_markers": len(list((BASE / "results").glob("*/*/slippage_*/_complete.json"))),
            "final_holdout_performance_computed": False}
    obj = json.loads(path.read_text())
    complete = BASE / "results/report_complete.json"
    verified = False
    if complete.exists():
        from audit_development_continuity import sha
        meta = json.loads(complete.read_text())
        verified = meta["success"] and all(sha(ROOT / n) == h for n, h in meta["output_hashes"].items())
        verified = verified and sha(BASE / "results/verification.json") == meta["verification_sha256"]
    return {"success": obj["success"], "registered_runs_completed": obj["registered_runs_completed"],
        "verified_replays": obj["verified_replays"], "model_fits": obj["model_fits"],
        "report_verified": verified, "evidence_gates": obj["evidence_gates"],
        "primary_results": [{k: r[k] for k in ("window", "model", "total_return", "Sharpe_rf0", "MDD")}
                            for r in obj["primary_results"]],
        "final_holdout_performance_computed": True, "prior_2024_validation_failed": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=["all", *STAGES, "summary"], default="all")
    args = parser.parse_args()
    if args.stage == "summary":
        print(json.dumps(summary()))
        return
    from acquire_usdm_universe import exclusive_run
    with exclusive_run(BASE / ".run.lock"):
        log = ROOT / "reports/acquisition" / f"final_holdout_{args.stage}_{datetime.now(UTC):%Y%m%dT%H%M%SZ}.log"
        log.parent.mkdir(parents=True, exist_ok=True)
        print(f"Log: {log}", flush=True)
        with log.open("w", encoding="utf-8") as handle:
            for stage in (list(STAGES) if args.stage == "all" else [args.stage]):
                process = subprocess.Popen([sys.executable, "-u", str(ROOT / "scripts" / STAGES[stage])],
                    cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, encoding="utf-8", errors="replace")
                try:
                    for line in process.stdout:
                        handle.write(line)
                        handle.flush()
                        print(line, end="", flush=True)
                    code = process.wait()
                except KeyboardInterrupt:
                    process.terminate()
                    process.wait()
                    raise
                if code:
                    (BASE / "last_failure.json").write_text(json.dumps({"stage": stage,
                        "exit_code": code, "log": str(log)}, indent=2)+"\n")
                    raise SystemExit(code)


if __name__ == "__main__":
    main()
