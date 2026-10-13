"""
services.py -- business logic for the LineaScope API.

Loads the trained model and pre-computed candidate features once at
startup, then scores candidates on request. Logs every detection run
to a local SQLite database (src/api/db.py).
"""

import json
import time
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import geopandas as gpd
import joblib

from src.config import (
    DERIVED, REFERENCE, MODELS, CRS_WGS84,
    BBOX_WGS84, GRID, CRS_PROJECTED,
    GRID_WIDTH, GRID_HEIGHT, ALL_LAYERS,
)
from src.api import db


# ---------- singleton state ----------

class State:
    model: object = None
    feature_cols: list = None
    model_version: str = None
    candidates: gpd.GeoDataFrame = None
    features: pd.DataFrame = None
    reference: gpd.GeoDataFrame = None
    metrics: dict = None
    loaded: bool = False


state = State()


# ---------- loaders ----------

def load_all():
    """Called once at startup."""
    if state.loaded:
        return

    print("[services] Loading model...")
    bundle = joblib.load(MODELS / "rf_final.joblib")
    state.model = bundle["model"]
    state.feature_cols = bundle["feature_cols"]
    state.model_version = bundle.get("experiment", "unknown")

    print("[services] Loading candidates...")
    cands = gpd.read_file(DERIVED / "candidates.geojson")
    cands = cands.rename(columns={"id": "candidate_id"})
    feats = pd.read_parquet(DERIVED / "candidate_features.parquet")

    merged = cands.merge(
        feats, on="candidate_id", how="inner", suffixes=("_c", "_f")
    )
    if "length_m_f" in merged.columns:
        merged["length_m"] = merged["length_m_f"]
    if "azimuth_f" in merged.columns:
        merged["azimuth"] = merged["azimuth_f"]

    X = merged[state.feature_cols].values.astype(np.float32)
    merged["probability"] = state.model.predict_proba(X)[:, 1]

    state.candidates = merged
    print(f"[services]   {len(merged)} candidates scored")

    print("[services] Loading reference lineaments...")
    state.reference = gpd.read_file(REFERENCE / "reference_lineaments.geojson")
    print(f"[services]   {len(state.reference)} reference lines")

    print("[services] Loading metrics...")
    with open(DERIVED / "metrics.json") as f:
        state.metrics = json.load(f)

    # Initialise the SQLite run log
    db.init_db()
    print(f"[services] Run log ready at {db.DB_PATH}")

    state.loaded = True
    print("[services] Ready.")


# ---------- helpers ----------

def _stats_from_detections(det: gpd.GeoDataFrame) -> dict:
    if len(det) == 0:
        return {
            "count": 0,
            "total_length_km": 0.0,
            "mean_length_m": 0.0,
            "median_length_m": 0.0,
            "min_length_m": 0.0,
            "max_length_m": 0.0,
            "density_km_per_km2": 0.0,
            "dominant_azimuth_deg": 0.0,
            "secondary_azimuth_deg": None,
            "azimuth_histogram": [0] * 18,
            "azimuth_histogram_bins": [5 + 10 * i for i in range(18)],
        }

    lengths = det["length_m"].values
    az = det["azimuth"].values

    hist, edges = np.histogram(az, bins=18, range=(0, 180))
    centers = [(edges[i] + edges[i + 1]) / 2.0 for i in range(len(hist))]

    order = np.argsort(hist)[::-1]
    peak1 = int(order[0])
    peak2 = None
    for i in order[1:]:
        if abs(centers[i] - centers[peak1]) >= 30:
            peak2 = int(i)
            break

    return {
        "count": int(len(det)),
        "total_length_km": float(lengths.sum() / 1000),
        "mean_length_m": float(lengths.mean()),
        "median_length_m": float(np.median(lengths)),
        "min_length_m": float(lengths.min()),
        "max_length_m": float(lengths.max()),
        "density_km_per_km2": float(lengths.sum() / 1000 / 1100.0),
        "dominant_azimuth_deg": float(centers[peak1]),
        "secondary_azimuth_deg": float(centers[peak2]) if peak2 is not None else None,
        "azimuth_histogram": [int(x) for x in hist],
        "azimuth_histogram_bins": [float(c) for c in centers],
    }


# ---------- public API ----------

def filter_candidates(threshold: float, min_length_m: int) -> gpd.GeoDataFrame:
    df = state.candidates
    mask = (df["probability"] >= threshold) & (df["length_m"] >= min_length_m)
    return df[mask].copy()


def detect(threshold: float, min_length_m: int) -> dict:
    t0 = time.time()
    det = filter_candidates(threshold, min_length_m)

    det_wgs = det.to_crs(CRS_WGS84)

    features = []
    for _, row in det_wgs.iterrows():
        features.append({
            "type": "Feature",
            "geometry": row.geometry.__geo_interface__,
            "properties": {
                "candidate_id": int(row["candidate_id"]),
                "probability": float(row["probability"]),
                "length_m": float(row["length_m"]),
                "azimuth": float(row["azimuth"]),
            },
        })

    stats = _stats_from_detections(det)
    runtime = time.time() - t0

    # Log the run
    try:
        run_id = db.insert_run(
            threshold=threshold,
            min_length_m=min_length_m,
            n_lineaments=stats["count"],
            total_length_km=stats["total_length_km"],
            runtime_s=runtime,
        )
        print(
            f"[services] Logged run {run_id}: "
            f"{stats['count']} lineaments in {runtime:.2f}s"
        )
    except Exception as e:
        print(f"[services] WARN — failed to log run: {e}")

    return {
        "params": {"threshold": float(threshold), "min_length_m": int(min_length_m)},
        "geojson": {"type": "FeatureCollection", "features": features},
        "statistics": stats,
        "runtime_s": round(runtime, 4),
    }


def get_dataset_info() -> dict:
    return {
        "study_area_name": "Abraka and Middle Ethiope River corridor, Delta State, Nigeria",
        "bbox_wgs84": BBOX_WGS84,
        "crs": CRS_PROJECTED,
        "resolution_m": GRID["res"],
        "grid_size": [GRID_WIDTH, GRID_HEIGHT],
        "layers": [
            {"name": name, "description": name} for name in ALL_LAYERS
        ],
        "date_range": {"start": "2025-11-01", "end": "2026-04-01"},
        "sentinel1_scenes": 25,
        "sentinel2_scenes": 3,
    }


def get_reference_geojson() -> dict:
    ref = state.reference.to_crs(CRS_WGS84)
    features = []
    for _, row in ref.iterrows():
        features.append({
            "type": "Feature",
            "geometry": row.geometry.__geo_interface__,
            "properties": {
                "id": int(row["id"]) if "id" in row else None,
                "confidence": row.get("confidence", None),
                "azimuth": float(row["azimuth"]) if "azimuth" in row else None,
            },
        })
    return {
        "count": len(ref),
        "total_length_km": float(ref.length.sum() / 1000),
        "geojson": {"type": "FeatureCollection", "features": features},
    }


def get_metrics() -> dict:
    m = state.metrics
    candidates = ["E1_DEM_only", "E2_S2_only", "E3_S1_only", "E4_all_features"]
    f1s = {k: m[k]["cv"]["pooled"]["f1"] for k in candidates if k in m}
    best = max(f1s, key=f1s.get) if f1s else "unknown"
    return {**m, "best_experiment": best}