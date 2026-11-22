"""Explicit full-catalog input CLI, separate from the restricted prototype."""

import argparse
import json
from pathlib import Path

from .config import InputSpec, load_json


def main():
    parser = argparse.ArgumentParser(
        description="Full-catalog chronological input construction (no fitting or PnL)"
    )
    parser.add_argument(
        "command",
        choices=[
            "universe",
            "summary",
            "review",
            "repair-plan",
            "repair-run",
            "repair-assess",
            "repair-evidence",
            "repair-scope",
            "capacity-audit",
            "first-window",
            "window",
            "funding-breaks",
        ],
    )
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--config", type=Path, default=Path("config/full_universe_inputs.json"))
    parser.add_argument("--dataset", type=Path)
    parser.add_argument("--report-dir", type=Path)
    parser.add_argument("--prototype-manifest", type=Path)
    parser.add_argument("--repair-dir", type=Path)
    parser.add_argument("--retry-failed", action="store_true")
    parser.add_argument(
        "--stage",
        choices=["all", "prepare", "fit", "preflight", "simulate", "report", "summary"],
        default="all",
    )
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    if args.command == "funding-breaks":
        if args.run_dir is None:
            parser.error("funding-breaks requires --run-dir")
        from .funding_evidence import audit_breaks

        result = audit_breaks(args.project_root, args.run_dir, args.limit)
        if not result["success"]:
            raise SystemExit(1)
        return
    if args.command in {"first-window", "window"}:
        if args.command == "window" and args.config == Path("config/full_universe_inputs.json"):
            parser.error("window requires --config")
        import contextlib
        import sys
        from datetime import UTC, datetime

        from .first_window import main_stage

        class Tee:
            def __init__(self, original, log):
                self.original, self.log = original, log

            def write(self, value):
                self.original.write(value)
                self.log.write(value)

            def flush(self):
                self.original.flush()
                self.log.flush()

        logs = args.project_root / "reports/acquisition"
        logs.mkdir(parents=True, exist_ok=True)
        log_path = logs / ("dynamic_window_" + datetime.now(UTC).strftime("%Y%m%dT%H%M%S") + ".log")
        print("Log: " + str(log_path), flush=True)
        config = args.project_root / (
            "config/dynamic_first_window.json"
            if args.config == Path("config/full_universe_inputs.json")
            else args.config
        )
        with (
            log_path.open("w") as log,
            contextlib.redirect_stdout(Tee(sys.stdout, log)),
            contextlib.redirect_stderr(Tee(sys.stderr, log)),
        ):
            result = main_stage(args.project_root, config, args.stage, args.run_dir)
        if result.get("success") is False:
            raise SystemExit(1)
        return
    if args.command == "capacity-audit":
        if args.repair_dir is None:
            parser.error("capacity-audit requires --repair-dir")
        from .capacity import capacity_audit

        capacity_audit(args.project_root, args.repair_dir)
        return
    if args.command in {"repair-evidence", "repair-scope"}:
        if args.repair_dir is None:
            parser.error(args.command + " requires --repair-dir")
        from .source_evidence import collect_evidence, scope_report

        if args.command == "repair-evidence":
            collect_evidence(args.repair_dir)
        else:
            scope_report(args.project_root, args.repair_dir)
        return
    if args.command == "repair-assess":
        if args.repair_dir is None:
            parser.error("repair-assess requires --repair-dir")
        from .repair_assessment import assess_repairs

        assess_repairs(args.project_root, args.repair_dir)
        return
    if args.command == "repair-plan":
        if args.dataset is None:
            parser.error("repair-plan requires --dataset")
        from .repair import make_plan

        review = (
            args.report_dir
            or args.project_root / "reports/tables/full_universe_inputs" / args.dataset.name
        )
        make_plan(args.project_root, args.dataset, review)
        return
    if args.command == "repair-run":
        if args.repair_dir is None:
            parser.error("repair-run requires --repair-dir")
        from .repair import run_repairs

        run_repairs(args.project_root, args.repair_dir, retry_failed=args.retry_failed)
        return
    if args.command == "review":
        if args.dataset is None:
            parser.error("review requires --dataset")
        from .reporting import review_inputs

        output = (
            args.report_dir
            or args.project_root / "reports/tables/full_universe_inputs" / args.dataset.name
        )
        review_inputs(args.dataset, args.project_root, output, args.prototype_manifest)
        return
    if args.command == "summary":
        if args.dataset is None:
            parser.error("summary requires --dataset")
        meta = load_json(args.dataset / "manifest.json")
        print(
            json.dumps(
                {
                    k: v
                    for k, v in meta.items()
                    if k not in {"source_bindings", "output_hashes", "build_identity"}
                }
            )
        )
        return
    from .universe import build_inputs

    spec = InputSpec.read(args.project_root / args.config, args.project_root)
    meta, _ = build_inputs(spec)
    if not meta["success"]:
        raise SystemExit(1)
