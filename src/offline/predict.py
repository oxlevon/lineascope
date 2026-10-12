"""
predict.py -- apply the trained Random Forest to all 7,202 candidates
and produce the final detected lineament set.

Usage:
    python -m src.offline.predict

Input:
    models/rf_final.joblib
    data/derived/candidates.geojson
    data/derived/candidate_features.parquet

Output:
    data/derived/detected_lineaments.geojson
    data/derived/detected_lineaments.csv
    data/derived/prediction_stats.txt
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import numpy as np
import pandas as pd
import joblib
import geopandas as gpd

from src.config import DERIVED, MODELS, CRS_WGS84


THRESHOLD = 0.5    # default probability threshold


def log(msg):
    print(msg, flush=True)


def main():
    # --- Load model ---
    model_path = MODELS / "rf_final.joblib"
    log(f"Loading model: {model_path}")
    bundle = joblib.load(model_path)
    model = bundle["model"]
    feature_cols = bundle["feature_cols"]
    experiment = bundle.get("experiment", "unknown")
    log(f"  experiment: {experiment}")
    log(f"  features:   {len(feature_cols)}")

    # --- Load candidates + features ---
    log("\nLoading candidates + features...")
    cands = gpd.read_file(DERIVED / "candidates.geojson")
    cands = cands.rename(columns={"id": "candidate_id"})
    feats = pd.read_parquet(DERIVED / "candidate_features.parquet")
    df = cands.merge(feats, on="candidate_id", how="inner", suffixes=("_c", "_f"))
    # Prefer the feature table's length_m (from _f) if suffix collision happened
    if "length_m_f" in df.columns:
        df["length_m"] = df["length_m_f"]
    if "azimuth_f" in df.columns:
        df["azimuth"] = df["azimuth_f"]
    log(f"  {len(df)} candidates")

    # --- Predict ---
    log("\nScoring candidates...")
    X = df[feature_cols].values.astype(np.float32)
    proba = model.predict_proba(X)[:, 1]
    df["probability"] = proba

    # --- Apply threshold ---
    log(f"\nApplying threshold = {THRESHOLD}")
    detected = df[df["probability"] >= THRESHOLD].copy()
    log(f"  {len(detected)} candidates pass threshold")
    log(f"  ({100 * len(detected) / len(df):.1f} % of all candidates)")

    # --- Compute statistics ---
    lengths = detected["length_m"].values
    az = detected["azimuth"].values

    # Azimuth histogram (18 bins of 10 degrees, 0-180 range)
    hist, edges = np.histogram(az, bins=18, range=(0, 180))
    centers = [(edges[i] + edges[i + 1]) / 2.0 for i in range(len(hist))]

    # Find top 2 peaks separated by at least 30 degrees
    order = np.argsort(hist)[::-1]
    peak1_idx = int(order[0])
    peak2_idx = None
    for i in order[1:]:
        if abs(centers[i] - centers[peak1_idx]) >= 30:
            peak2_idx = int(i)
            break

    dominant_az = float(centers[peak1_idx])
    secondary_az = float(centers[peak2_idx]) if peak2_idx is not None else None

    stats = {
        "total_candidates": int(len(df)),
        "detected_count": int(len(detected)),
        "threshold": THRESHOLD,
        "total_length_km": float(lengths.sum() / 1000),
        "mean_length_m": float(lengths.mean()) if len(lengths) else 0.0,
        "median_length_m": float(np.median(lengths)) if len(lengths) else 0.0,
        "min_length_m": float(lengths.min()) if len(lengths) else 0.0,
        "max_length_m": float(lengths.max()) if len(lengths) else 0.0,
        "dominant_azimuth_deg": dominant_az,
        "secondary_azimuth_deg": secondary_az,
        "azimuth_histogram": hist.tolist(),
        "azimuth_histogram_bins": [float(c) for c in centers],
        "aoi_area_km2": 1100.0,
        "density_km_per_km2": float(lengths.sum() / 1000 / 1100.0),
    }

    log("\n=== Statistics ===")
    for k, v in stats.items():
        if k == "azimuth_histogram":
            continue
        if isinstance(v, float):
            log(f"  {k:25s} {v:.4f}")
        elif v is None:
            log(f"  {k:25s} none")
        else:
            log(f"  {k:25s} {v}")

    log("\n=== Azimuth histogram (10 deg bins) ===")
    for i, c in enumerate(hist):
        label = f"{int(edges[i]):3d}-{int(edges[i+1]):3d}"
        bar = "#" * int(c / max(hist.max(), 1) * 40)
        marker = ""
        if i == peak1_idx:
            marker = "  <- peak 1"
        if peak2_idx is not None and i == peak2_idx:
            marker = "  <- peak 2"
        log(f"  {label}  {c:4d}  {bar}{marker}")

    # --- Save GeoJSON (WGS84 for the web) ---
    out_geojson = DERIVED / "detected_lineaments.geojson"
    out_wgs = detected[["candidate_id", "length_m", "azimuth",
                        "probability", "geometry"]].copy()
    out_wgs = out_wgs.to_crs(CRS_WGS84)
    out_wgs.to_file(out_geojson, driver="GeoJSON")
    log(f"\nSaved GeoJSON: {out_geojson}")

    # --- Save CSV (no geometry) ---
    out_csv = DERIVED / "detected_lineaments.csv"
    detected.drop(columns="geometry").to_csv(out_csv, index=False)
    log(f"Saved CSV:     {out_csv}")

    # --- Save stats JSON ---
    out_stats = DERIVED / "prediction_stats.txt"
    with open(out_stats, "w") as f:
        json.dump(stats, f, indent=2)
    log(f"Saved stats:   {out_stats}")

    log("\nDone.")


if __name__ == "__main__":
    main()