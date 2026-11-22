"""Explicit full-catalog input CLI, separate from the restricted prototype."""

import argparse
import json
from pathlib import Path

from .config import InputSpec, load_json


def main():
    parser = argparse.ArgumentParser(
        description="Full-catalog chronological input construction (no fitting or PnL)"
    )
    parser.add_argument("command", choices=["universe", "summary", "review"])
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--config", type=Path, default=Path("config/full_universe_inputs.json"))
    parser.add_argument("--dataset", type=Path)
    parser.add_argument("--report-dir", type=Path)
    parser.add_argument("--prototype-manifest", type=Path)
    args = parser.parse_args()
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
