"""
labels.py -- label each candidate as positive/negative/ambiguous by
comparing it to the reference lineaments.

Uses fraction-of-overlap matching: a candidate is positive if more than
MIN_OVERLAP_FRACTION of its length lies within BUFFER_M of a reference
line whose azimuth differs by less than ANGLE_TOL_DEG.

Usage:
    python -m src.offline.labels

Input:
    data/derived/candidate_features.parquet
    data/reference/reference_lineaments.geojson

Output:
    data/derived/candidate_features_labelled.parquet
    data/derived/label_stats.txt
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.ops import unary_union

from src.config import DERIVED, REFERENCE, NEGATIVE_DISTANCE_M


# --- Matching parameters (tuned; document in Chapter Four) ---
BUFFER_M             = 100.0   # was 60
ANGLE_TOL_DEG        = 20.0    # was 15
MIN_OVERLAP_FRACTION = 0.50    # positive needs >=50% of candidate inside buffer


def log(msg):
    print(msg, flush=True)


def azimuth(geom):
    coords = list(geom.coords)
    (x0, y0), (x1, y1) = coords[0], coords[-1]
    return float(np.degrees(np.arctan2(y1 - y0, x1 - x0)) % 180.0)


def angle_diff(a, b):
    d = abs(a - b) % 180.0
    return min(d, 180.0 - d)


def main():
    log("Loading candidates + features...")
    cand_pts = gpd.read_file(DERIVED / "candidates.geojson")
    feats = pd.read_parquet(DERIVED / "candidate_features.parquet")
    cand_pts = cand_pts.rename(columns={"id": "candidate_id"})
    cands = cand_pts.merge(feats, on="candidate_id", how="inner")
    log(f"  matched {len(cands)} candidates")

    log("Loading reference lineaments...")
    refs = gpd.read_file(REFERENCE / "reference_lineaments.geojson")
    log(f"  {len(refs)} reference lines")

    log(f"Matching parameters:")
    log(f"  buffer           = {BUFFER_M} m")
    log(f"  angle tolerance  = {ANGLE_TOL_DEG} deg")
    log(f"  overlap fraction = {MIN_OVERLAP_FRACTION}")

    # Precompute reference azimuths and buffered geometries
    ref_azimuths = np.array([azimuth(g) for g in refs.geometry])
    ref_buffers  = refs.geometry.buffer(BUFFER_M)

    # Spatial index: which candidates intersect which reference buffers
    log("\nBuilding spatial index...")
    buf_sindex = ref_buffers.sindex

    labels = []
    dists = []
    az_diffs = []
    fracs = []

    n = len(cands)
    for i, (cand_geom, cand_az) in enumerate(
            zip(cands.geometry, cands["azimuth"].values)):

        # Find candidate reference buffers that intersect this candidate
        candidate_idx = list(buf_sindex.query(cand_geom))

        # Filter by angle tolerance
        good_buffers = []
        for j in candidate_idx:
            if angle_diff(cand_az, ref_azimuths[j]) <= ANGLE_TOL_DEG:
                good_buffers.append(ref_buffers.iloc[j])

        if good_buffers:
            merged = unary_union(good_buffers)
            overlap_geom = cand_geom.intersection(merged)
            overlap_len = overlap_geom.length
            fraction = overlap_len / cand_geom.length if cand_geom.length > 0 else 0.0
        else:
            fraction = 0.0

        fracs.append(fraction)

        # Nearest reference distance (for reporting)
        min_d = cand_geom.distance(refs.geometry).min()
        dists.append(min_d)

        # Nearest angle difference
        diffs = [angle_diff(cand_az, a) for a in ref_azimuths]
        az_diffs.append(min(diffs))

        # Label decision
        if fraction >= MIN_OVERLAP_FRACTION:
            labels.append("positive")
        elif min_d >= NEGATIVE_DISTANCE_M:
            labels.append("negative")
        else:
            labels.append("ambiguous")

        if (i + 1) % 1000 == 0:
            log(f"  {i+1}/{n}")

    cands["label"] = labels
    cands["overlap_fraction"] = fracs
    cands["nearest_ref_dist_m"] = dists
    cands["nearest_ref_angle_diff"] = az_diffs

    # Stats
    log("\nLabel distribution:")
    counts = cands["label"].value_counts()
    for lab in ["positive", "negative", "ambiguous"]:
        c = int(counts.get(lab, 0))
        pct = 100.0 * c / len(cands)
        log(f"  {lab:10s}  {c:6d}  ({pct:5.1f} %)")

    out_path = DERIVED / "candidate_features_labelled.parquet"
    cands.to_parquet(out_path, index=False)
    log(f"\nSaved {len(cands)} labelled rows to {out_path}")

    with open(DERIVED / "label_stats.txt", "w") as f:
        f.write(f"total_candidates: {len(cands)}\n")
        for lab in ["positive", "negative", "ambiguous"]:
            f.write(f"{lab}: {int(counts.get(lab, 0))}\n")
        f.write(f"buffer_m: {BUFFER_M}\n")
        f.write(f"angle_tol_deg: {ANGLE_TOL_DEG}\n")
        f.write(f"overlap_fraction: {MIN_OVERLAP_FRACTION}\n")

    n_pos = int(counts.get("positive", 0))
    n_neg = int(counts.get("negative", 0))
    log(f"\nSDP target: >=300 positive, >=600 negative")
    log(f"  positive: {n_pos}  {'OK' if n_pos >= 300 else 'LOW'}")
    log(f"  negative: {n_neg}  {'OK' if n_neg >= 600 else 'LOW'}")

    log("\nDone.")


if __name__ == "__main__":
    main()