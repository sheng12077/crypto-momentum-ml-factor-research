"""Preserve failed v002 and reuse proven data/model caches; never reuse its financial attempts."""
import json
import shutil

from audit_development_continuity import sha
from final_holdout_common import BASE, checked_manifest, write
from run_first_development import PARAMS

PARENT_CONTRACT = "a58f4792bfc835bd935fb0a70fd89b05b83d13d0e1106902891034d3895ee674"


def migrate_engine_fix(base=BASE):
    prior = base.parent / "v20261122_002"
    if not (prior / "prepared/manifest.json").exists():
        return False
    if (base / "engine_fix_migration.json").exists():
        return False
    if (base / "prepared/manifest.json").exists():
        target_meta = json.loads((base / "prepared/manifest.json").read_text())
        if target_meta.get("parent_version") != "v20261122_002":
            return False
    if sha(prior / "code_contract.json") != PARENT_CONTRACT:
        raise ValueError("Unrecognized parent run; do not silently adopt data/models")
    if (prior / "results/summary.json").exists() or list((prior / "results").glob("*/*/slippage_*/_complete.json")):
        raise ValueError("Parent has completed financial cases; explicit migration review required")
    parent = json.loads((prior / "code_contract.json").read_text())
    current = json.loads((base / "code_contract.json").read_text())
    for field in ("registration_sha256", "old_prepared_sha256", "lifecycle_events_sha256", "analysis_sha256", "runtime"):
        if parent[field] != current[field]:
            raise ValueError(f"Parent/current frozen input or runtime mismatch: {field}")
    allowed = {"scripts/final_holdout_common.py", "scripts/final_holdout_engine.py",
               "scripts/prepare_final_holdout.py", "scripts/run_final_holdout.py", "scripts/report_final_holdout.py",
               "scripts/run_final_holdout_cases.py"}
    changed = {n for n, h in parent["code_hashes"].items() if current["code_hashes"].get(n) != h}
    if changed-allowed:
        raise ValueError(f"Unexpected frozen-code change: {sorted(changed-allowed)}")
    copied = []
    for rel, marker in (("prepared", "manifest.json"), ("spot_benchmarks", "summary.json")):
        source = prior / rel
        meta = checked_manifest(source, marker)
        if meta["code_contract_sha256"] != PARENT_CONTRACT:
            raise ValueError("Parent preparation was not bound to expected contract")
        target = base / rel
        if target.exists():
            # Only an incomplete copy from this controlled migration can exist here.
            for name, digest in meta["output_hashes"].items():
                if (target / name).exists() and sha(target / name) != digest:
                    raise ValueError("Partial migration output mismatch")
        shutil.copytree(source, target, dirs_exist_ok=True)
        old_meta_sha = sha(source / marker)
        meta["parent_manifest_sha256"] = old_meta_sha
        meta["parent_version"] = "v20261122_002"
        meta["code_contract_sha256"] = sha(base / "code_contract.json")
        write(target / marker, meta)
        copied.append(rel)
    for year in (2025, 2026):
        source = prior / f"results/models/{year}"
        meta = checked_manifest(source, "model_summary.json")
        if meta["parameters"] != PARAMS or meta["latest_label_available_ms"] >= meta["training_cutoff_ms"]:
            raise ValueError("Parent model is not the frozen purged model")
        shutil.copytree(source, base / f"results/models/{year}", dirs_exist_ok=True)
    for rel in ("repair/raw",):
        if (prior / rel).exists() and not (base / rel).exists():
            shutil.copytree(prior / rel, base / rel)
    write(base / "engine_fix_migration.json", {"success": True,
        "parent_code_contract_sha256": PARENT_CONTRACT, "parent_version": str(prior),
        "copied_data": copied, "reused_model_years": [2025, 2026],
        "new_model_fits": 0, "financial_cases_reused": 0,
        "reason": "Separate completed funding mark from simultaneous execution quote; preserve frozen strategy."})
    return True
