"""Verify existing annual model, training, prediction and SHAP caches; never refit."""

import json
import lightgbm as lgb
import numpy as np
import pandas as pd
from ..settings import FEATURES, HOUR, DAY, STOP, MODEL_ROOTS, TRAINING_PREPARED, ms
from ..integrity import sha, checked_manifest

PARAMS = dict(
    n_estimators=100,
    learning_rate=0.03,
    num_leaves=7,
    max_depth=3,
    min_child_samples=100,
    reg_lambda=10.0,
    subsample=1.0,
    colsample_bytree=1.0,
    random_state=42,
    deterministic=True,
    force_col_wise=True,
    n_jobs=1,
    verbosity=-1,
)


def matured_training(features, trades, cutoff):
    frame = features[
        (features.feature_cutoff_ms < cutoff) & (features.label_available_ms < cutoff)
    ].copy()
    frame = frame.sort_values(["decision_date", "instrument_id"]).reset_index(drop=True)
    past = trades[trades.bar_open_ms < cutoff]
    lookup = {(r.instrument_id, int(r.bar_open_ms)): r for r in past.itertuples()}
    for row in frame.itertuples():
        if pd.notna(row.label):
            continue
        entry = int(row.feature_cutoff_ms) + HOUR
        exit_time = entry + 7 * DAY
        if exit_time + 2 * HOUR != row.label_available_ms or exit_time + 2 * HOUR >= cutoff:
            raise ValueError("Invalid label timing")
        a, b = lookup.get((row.instrument_id, entry)), lookup.get((row.instrument_id, exit_time))
        if a is not None and b is not None and a.volume > 0 and b.volume > 0:
            frame.loc[row.Index, "label"] = (b.quote_volume / b.volume) / (
                a.quote_volume / a.volume
            ) - 1
    frame = frame[frame.label.notna()].reset_index(drop=True)
    if not np.isfinite(frame[FEATURES + ["label"]].to_numpy(float)).all():
        raise ValueError("Invalid matured training values")
    return frame


def cached_predictions(features, trades):
    predictions, audits = [], []
    keys = ["decision_date", "instrument_id"]
    for year, folder in MODEL_ROOTS.items():
        meta = json.loads((folder / "model_summary.json").read_text())
        if "output_hashes" in meta:
            checked_manifest(folder, "model_summary.json")
        digest = meta.get("model_sha256", meta.get("frozen_model_sha256"))
        if digest and digest != sha(folder / "lightgbm.txt"):
            raise ValueError(f"Changed annual model: {year}")
        if meta["parameters"] != PARAMS or meta["features"] != FEATURES:
            raise ValueError(f"Changed model specification: {year}")
        cutoff = ms(f"{year}-01-01")
        train = (
            pd.read_parquet(folder / "training_samples.parquet")
            .sort_values(keys)
            .reset_index(drop=True)
        )
        if year <= 2024:
            source = TRAINING_PREPARED[year]
            original_meta = json.loads((source / "manifest.json").read_text())
            if (
                sha(source / "features.parquet")
                != original_meta["output_hashes"]["features.parquet"]
            ):
                raise ValueError("Original training feature source changed")
            original = pd.read_parquet(source / "features.parquet")
            expected_train = (
                original[
                    (original.feature_cutoff_ms < cutoff)
                    & (original.label_available_ms < cutoff)
                    & original.label.notna()
                ]
                .sort_values(keys)
                .reset_index(drop=True)
            )
        else:
            expected_train = matured_training(features, trades[trades.bar_open_ms < cutoff], cutoff)
        pd.testing.assert_frame_equal(
            train, expected_train[train.columns], check_exact=True, check_dtype=False
        )
        if (
            not (train.label_available_ms < cutoff).all()
            or not (train.feature_cutoff_ms < cutoff).all()
        ):
            raise ValueError("Training label crosses forecast cutoff")
        name = "predictions.parquet" if year >= 2025 else "validation_predictions.parquet"
        sample = pd.read_parquet(folder / name).sort_values(keys).reset_index(drop=True)
        expected = (
            features[
                (features.feature_cutoff_ms >= cutoff)
                & (features.feature_cutoff_ms < min(ms(f"{year + 1}-01-01"), STOP))
            ]
            .sort_values(keys)
            .reset_index(drop=True)
        )
        cols = keys + FEATURES + ["feature_cutoff_ms", "decision_ms", "label_available_ms"]
        pd.testing.assert_frame_equal(
            sample[cols], expected[cols], check_exact=True, check_dtype=False
        )
        if sample.duplicated(keys).any() or sample.empty:
            raise ValueError("Missing/duplicate annual forecast rows")
        booster = lgb.Booster(model_file=str(folder / "lightgbm.txt"))
        if not np.allclose(booster.predict(sample[FEATURES]), sample.score, atol=1e-12, rtol=0):
            raise ValueError("Cached model prediction mismatch")
        attribution = (
            pd.read_csv(folder / "shap_values.csv").sort_values(keys).reset_index(drop=True)
        )
        pd.testing.assert_frame_equal(attribution[keys], sample[keys], check_dtype=False)
        shap_columns = ["shap_" + f for f in FEATURES]
        error = np.max(
            np.abs(
                attribution[shap_columns].sum(axis=1) + attribution.expected_value - sample.score
            )
        )
        if not np.isfinite(error) or error > 1e-6:
            raise ValueError("Cached SHAP additivity mismatch")
        # Labels in old development caches are irrelevant to forecasting: never carry them into plans.
        predictions.append(sample[cols + ["score"]])
        audits.append(
            {
                "year": year,
                "training_rows": len(train),
                "forecast_rows": len(sample),
                "cutoff_ms": cutoff,
                "latest_label_available_ms": int(train.label_available_ms.max()),
                "model_sha256": sha(folder / "lightgbm.txt"),
                "shap_additivity_max_error": float(error),
            }
        )
    return pd.concat(predictions, ignore_index=True), audits
