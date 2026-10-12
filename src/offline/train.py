"""
train.py -- train and evaluate the Random Forest classifier with
spatial block cross-validation and ablation experiments.

Usage:
    python -m src.offline.train

Input:
    data/derived/training_samples.parquet

Output:
    models/rf_final.joblib
    models/rf_E1_DEM_only.joblib ... models/rf_E4_all_features.joblib
    data/derived/metrics.json
    data/derived/feature_importance.csv
    data/derived/cv_folds.csv
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import numpy as np
import pandas as pd
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    precision_score, recall_score, f1_score,
    roc_auc_score, average_precision_score,
    confusion_matrix, matthews_corrcoef,
)
from sklearn.model_selection import GroupKFold
from sklearn.cluster import KMeans

from src.config import DERIVED, MODELS, RF_PARAMS, SPATIAL_FOLDS


# --- Columns that are NEVER features (metadata / leakage) ---
NON_FEATURE_COLS = {
    "sample_id",      # identifier
    "kind",           # duplicate of label
    "label",          # target
    "geometry",       # spatial
    "x_mid",          # coordinate (causes leakage)
    "y_mid",          # coordinate (causes leakage)
    "spatial_block",  # the CV grouping variable (causes leakage)
}

N_SPATIAL_BLOCKS = 5


def log(msg):
    print(msg, flush=True)


def get_feature_columns(df):
    """Return all columns that are legitimate features."""
    cols = [c for c in df.columns if c not in NON_FEATURE_COLS]
    cols = [c for c in cols if pd.api.types.is_numeric_dtype(df[c])]
    return cols


def feature_group(name):
    """Return a predicate that matches feature columns in the given group."""
    patterns = {
        "DEM":  ["elevation", "slope", "aspect", "hillshade", "curvature", "tpi"],
        "S2":   ["B02", "B03", "B04", "B08", "B11", "B12", "NDVI", "B11_B12"],
        "S1":   ["VV", "VH"],
        "CULT": ["dist_road", "dist_waterway", "builtup"],
    }
    pats = patterns[name]
    return lambda c: any(p in c for p in pats)


def make_spatial_blocks(df, n_blocks=5, seed=42):
    from sklearn.cluster import KMeans
    coords = df[["x_mid", "y_mid"]].values
    km = KMeans(n_clusters=n_blocks, random_state=seed, n_init=10)
    df["spatial_block"] = km.fit_predict(coords)
    return df


def cross_validate(df, feature_cols, model_params, cv):
    X = df[feature_cols].values.astype(np.float32)
    y = (df["label"] == "positive").astype(int).values
    groups = df["spatial_block"].values

    all_y_true, all_y_pred, all_y_prob = [], [], []
    fold_metrics = []

    for fold, (tr, te) in enumerate(cv.split(X, y, groups), 1):
        model = RandomForestClassifier(**model_params)
        model.fit(X[tr], y[tr])

        y_prob = model.predict_proba(X[te])[:, 1]
        y_pred = (y_prob >= 0.5).astype(int)

        tn, fp, fn, tp = confusion_matrix(y[te], y_pred, labels=[0, 1]).ravel()
        p = precision_score(y[te], y_pred, zero_division=0)
        r = recall_score(y[te], y_pred, zero_division=0)
        f = f1_score(y[te], y_pred, zero_division=0)
        try:
            auc = roc_auc_score(y[te], y_prob)
        except ValueError:
            auc = float("nan")
        try:
            pr_auc = average_precision_score(y[te], y_prob)
        except ValueError:
            pr_auc = float("nan")

        fold_metrics.append({
            "fold": fold, "n_test": len(te),
            "tp": int(tp), "fp": int(fp), "tn": int(tn), "fn": int(fn),
            "precision": float(p), "recall": float(r),
            "f1": float(f), "roc_auc": float(auc), "pr_auc": float(pr_auc),
        })

        all_y_true.extend(y[te])
        all_y_pred.extend(y_pred)
        all_y_prob.extend(y_prob)

    y_true = np.array(all_y_true)
    y_pred = np.array(all_y_pred)
    y_prob = np.array(all_y_prob)

    pooled = {
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall":    float(recall_score(y_true, y_pred, zero_division=0)),
        "f1":        float(f1_score(y_true, y_pred, zero_division=0)),
        "mcc":       float(matthews_corrcoef(y_true, y_pred)),
        "roc_auc":   float(roc_auc_score(y_true, y_prob)),
        "pr_auc":    float(average_precision_score(y_true, y_prob)),
    }
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    pooled["confusion_matrix"] = {
        "tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)
    }

    return {"folds": fold_metrics, "pooled": pooled}


def main():
    MODELS.mkdir(parents=True, exist_ok=True)

    log("Loading training samples...")
    df = pd.read_parquet(DERIVED / "training_samples.parquet")
    log(f"  {len(df)} rows, {df.shape[1]} columns")
    log(f"  positives: {(df['label']=='positive').sum()}")
    log(f"  negatives: {(df['label']=='negative').sum()}")

    log("\nAssigning spatial blocks (k-means on x,y)...")
    df = make_spatial_blocks(df, n_blocks=N_SPATIAL_BLOCKS, seed=42)
    block_counts = df["spatial_block"].value_counts().sort_index()
    for b, c in block_counts.items():
        log(f"  block {b}: {c} samples")

    all_features = get_feature_columns(df)
    log(f"\nFeature columns (excl. {len(NON_FEATURE_COLS)} non-feature): {len(all_features)}")

    cv = GroupKFold(n_splits=SPATIAL_FOLDS)

    experiments = {
        "E1_DEM_only":     ["DEM"],
        "E2_S2_only":      ["S2"],
        "E3_S1_only":      ["S1"],
        "E4_all_features": None,
    }

    results = {}

    for exp_name, groups in experiments.items():
        log(f"\n=== {exp_name} ===")
        if groups is None:
            feature_cols = all_features
        else:
            keepers = [feature_group(g) for g in groups]
            feature_cols = [c for c in all_features if any(k(c) for k in keepers)]

        log(f"  using {len(feature_cols)} features")

        cv_result = cross_validate(df, feature_cols, RF_PARAMS, cv)
        pooled = cv_result["pooled"]

        log(f"  precision = {pooled['precision']:.4f}")
        log(f"  recall    = {pooled['recall']:.4f}")
        log(f"  f1        = {pooled['f1']:.4f}")
        log(f"  roc_auc   = {pooled['roc_auc']:.4f}")
        log(f"  pr_auc    = {pooled['pr_auc']:.4f}")
        log(f"  mcc       = {pooled['mcc']:.4f}")

        # Fit on all data and save
        X = df[feature_cols].values.astype(np.float32)
        y = (df["label"] == "positive").astype(int).values
        final_model = RandomForestClassifier(**RF_PARAMS)
        final_model.fit(X, y)
        joblib.dump(
            {"model": final_model, "feature_cols": feature_cols},
            MODELS / f"rf_{exp_name}.joblib",
            compress=3,
        )

        results[exp_name] = {
            "n_features": len(feature_cols),
            "feature_cols": feature_cols,
            "cv": cv_result,
        }

    # E0 baseline
    n_total = len(df)
    n_pos = (df["label"] == "positive").sum()
    e0 = {
        "precision": float(n_pos / n_total),
        "recall": 1.0,
        "f1": float(2 * (n_pos / n_total) / ((n_pos / n_total) + 1.0)),
        "note": "accept-all baseline",
    }
    results["E0_baseline"] = e0
    log(f"\n=== E0_baseline ===")
    log(f"  precision = {e0['precision']:.4f}")
    log(f"  recall    = {e0['recall']:.4f}")
    log(f"  f1        = {e0['f1']:.4f}")

        # Final model = best performing on spatial CV (E1 in this run)
    best_exp = max(
        ["E1_DEM_only", "E2_S2_only", "E3_S1_only", "E4_all_features"],
        key=lambda e: results[e]["cv"]["pooled"]["f1"]
    )
    log(f"\nBest performing config: {best_exp}")
    log(f"  F1 = {results[best_exp]['cv']['pooled']['f1']:.4f}")

    joblib.dump(
        {"model": joblib.load(MODELS / f"rf_{best_exp}.joblib")["model"],
         "feature_cols": results[best_exp]["feature_cols"],
         "experiment": best_exp},
        MODELS / "rf_final.joblib",
        compress=3,
    )
    log(f"  → final model saved")

    # Feature importance
    log("\nFeature importance (E4):")
    e4 = joblib.load(MODELS / "rf_E4_all_features.joblib")
    feat_imp = pd.DataFrame({
        "feature": e4["feature_cols"],
        "importance": e4["model"].feature_importances_,
    }).sort_values("importance", ascending=False)
    feat_imp.to_csv(DERIVED / "feature_importance.csv", index=False)
    for _, row in feat_imp.head(15).iterrows():
        log(f"  {row['feature']:35s}  {row['importance']:.4f}")

    with open(DERIVED / "metrics.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    log(f"\nSaved metrics to {DERIVED / 'metrics.json'}")

    df[["sample_id", "kind", "label", "x_mid", "y_mid", "spatial_block"]].to_csv(
        DERIVED / "cv_folds.csv", index=False
    )

    log("\nDone.")


if __name__ == "__main__":
    main()