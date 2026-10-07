"""
candidates.py -- generate candidate lineaments from the feature stack.

Usage:
    python -m src.offline.candidates           # use config defaults
    python -m src.offline.candidates --sweep   # try 4 parameter sets

Input:
    data/derived/stack_20m.tif

Output:
    data/derived/candidates.geojson
    data/derived/candidates_stats.txt
    (sweep mode also writes candidates_vote{N}_canny{M}.geojson)
"""

import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import numpy as np
import rasterio
from rasterio.transform import Affine
from skimage.feature import canny
from skimage.morphology import skeletonize
from skimage.transform import probabilistic_hough_line
import geopandas as gpd
from shapely.geometry import LineString
from shapely.ops import linemerge
from sklearn.decomposition import PCA
from scipy.spatial import cKDTree

from src.config import DERIVED, GRID, CRS_PROJECTED


# ---------- constants ----------

BAND_VV       = 0
BAND_VH       = 1
BAND_S2_START = 4
BAND_S2_END   = 9
BAND_HS_START = 16
BAND_HS_END   = 19

RES = GRID["res"]
SHAPE = (
    (GRID["y_max"] - GRID["y_min"]) // RES,
    (GRID["x_max"] - GRID["x_min"]) // RES,
)
TRANSFORM = Affine(RES, 0, GRID["x_min"], 0, -RES, GRID["y_max"])

# ---------- defaults (tuned for this study area) ----------

DEFAULTS = {
    "canny_sigma":      1.5,
    "canny_low":        0.08,
    "canny_high":       0.20,
    "vote_min":         3,
    "hough_min_length": 15,
    "hough_max_gap":    4,
    "merge_angle_deg":  10.0,
    "merge_gap_m":      80.0,
    "min_length_m":     500.0,
}


def log(msg):
    print(msg, flush=True)


# ---------- helpers ----------

def robust_normalize(band, p_low=2, p_high=98):
    finite = band[np.isfinite(band)]
    if finite.size == 0:
        return np.zeros_like(band, dtype=np.float32)
    lo, hi = np.percentile(finite, [p_low, p_high])
    if hi <= lo:
        return np.zeros_like(band, dtype=np.float32)
    return np.clip((band - lo) / (hi - lo), 0, 1).astype(np.float32)


def compute_pc1_of_s2(s2_bands):
    n_bands, H, W = s2_bands.shape
    norm = np.zeros_like(s2_bands, dtype=np.float32)
    for i in range(n_bands):
        norm[i] = robust_normalize(s2_bands[i])
    norm = np.nan_to_num(norm, nan=0.0, posinf=0.0, neginf=0.0)
    flat = norm.reshape(n_bands, -1).T
    pca = PCA(n_components=1, random_state=42)
    pc1 = pca.fit_transform(flat).reshape(H, W)
    return robust_normalize(pc1)


def build_edge_inputs(stack):
    inputs = []
    names = ["hillshade_000", "hillshade_045",
             "hillshade_090", "hillshade_135"]
    for i in range(BAND_HS_START, BAND_HS_END + 1):
        inputs.append((names[i - BAND_HS_START], robust_normalize(stack[i])))
    inputs.append(("VV_mean", robust_normalize(stack[BAND_VV])))
    inputs.append(("VH_mean", robust_normalize(stack[BAND_VH])))
    s2 = stack[BAND_S2_START:BAND_S2_END + 1]
    inputs.append(("S2_PC1", compute_pc1_of_s2(s2)))
    return inputs


def run_canny(inputs, sigma, low, high):
    edges = []
    for name, arr in inputs:
        e = canny(arr, sigma=sigma, low_threshold=low, high_threshold=high)
        log(f"  {name}: {e.sum():>8d} edge pixels")
        edges.append(e)
    return edges


def vote_count(edges, min_votes):
    votes = np.zeros_like(edges[0], dtype=np.uint8)
    for e in edges:
        votes += e.astype(np.uint8)
    mask = votes >= min_votes
    log(f"  vote>={min_votes}: {mask.sum()} pixels passed")
    return mask


def extract_segments(mask, min_length_px, max_gap_px):
    skel = skeletonize(mask)
    log(f"  {skel.sum()} skeleton pixels")
    segments_px = probabilistic_hough_line(
        skel,
        threshold=10,
        line_length=min_length_px,
        line_gap=max_gap_px,
    )
    log(f"  {len(segments_px)} raw Hough segments")
    return segments_px


def pixel_to_world(segments_px):
    lines = []
    for (x0, y0), (x1, y1) in segments_px:
        wx0, wy0 = TRANSFORM * (x0, y0)
        wx1, wy1 = TRANSFORM * (x1, y1)
        lines.append(LineString([(wx0, wy0), (wx1, wy1)]))
    return lines


def merge_collinear(lines, angle_deg, gap_m):
    """
    Greedy merge: if two segments are within gap_m and their azimuths
    differ by less than angle_deg, merge them.
    Uses a spatial index on segment endpoints.
    """
    log(f"  merging (angle<={angle_deg} deg, gap<={gap_m} m)...")
    if not lines:
        return []

    # Represent each line by its endpoints and azimuth
    def azimuth(ln):
        (x0, y0), (x1, y1) = ln.coords[0], ln.coords[-1]
        ang = np.degrees(np.arctan2(y1 - y0, x1 - x0)) % 180.0
        return ang

    lines = list(lines)
    used = [False] * len(lines)
    azimuths = [azimuth(ln) for ln in lines]

    # Build tree on all endpoints
    endpoints = []
    for ln in lines:
        endpoints.append(ln.coords[0])
        endpoints.append(ln.coords[-1])
    tree = cKDTree(np.array(endpoints))

    merged = []
    for i in range(len(lines)):
        if used[i]:
            continue
        current = lines[i]
        used[i] = True

        # Iteratively extend the current line by finding nearby collinear segments
        changed = True
        while changed:
            changed = False
            # Query endpoints of current line
            c0 = np.array(current.coords[0])
            c1 = np.array(current.coords[-1])
            idxs = tree.query_ball_point([c0, c1], r=gap_m)
            candidates = set()
            for sub in idxs:
                for k in sub:
                    candidates.add(k // 2)   # which line
            for j in candidates:
                if used[j]:
                    continue
                # angle check
                d_ang = abs(azimuths[i] - azimuths[j])
                d_ang = min(d_ang, 180 - d_ang)
                if d_ang <= angle_deg:
                    # merge via linemerge on the two lines
                    try:
                        m = linemerge([current, lines[j]])
                        if m.geom_type == "LineString":
                            current = m
                            used[j] = True
                            changed = True
                    except Exception:
                        pass

        merged.append(current)

    log(f"  {len(lines)} -> {len(merged)} after merge")
    return merged


def filter_by_length(lines, min_m):
    kept = [ln for ln in lines if ln.length >= min_m]
    log(f"  {len(kept)} of {len(lines)} retained after length filter")
    return kept


# ---------- pipeline ----------

def run_pipeline(stack, params, save_path=None, stats_path=None, tag=""):
    inputs = build_edge_inputs(stack)
    log(f"[{tag}] {len(inputs)} edge inputs")

    log(f"[{tag}] Canny (sigma={params['canny_sigma']}, "
        f"low={params['canny_low']}, high={params['canny_high']})")
    edges = run_canny(inputs, params["canny_sigma"],
                      params["canny_low"], params["canny_high"])

    mask = vote_count(edges, params["vote_min"])

    segs = extract_segments(mask, params["hough_min_length"],
                            params["hough_max_gap"])

    lines = pixel_to_world(segs)
    lines = merge_collinear(lines,
                            params["merge_angle_deg"],
                            params["merge_gap_m"])
    lines = filter_by_length(lines, params["min_length_m"])

    log(f"[{tag}] FINAL: {len(lines)} candidates")

    if save_path is not None:
        gdf = gpd.GeoDataFrame(
            {
                "id": range(len(lines)),
                "length_m": [round(ln.length, 2) for ln in lines],
            },
            geometry=lines,
            crs=CRS_PROJECTED,
        )
        gdf.to_file(save_path, driver="GeoJSON")
        log(f"[{tag}] saved {len(gdf)} candidates -> {save_path}")

    if stats_path is not None:
        lengths = np.array([ln.length for ln in lines])
        with open(stats_path, "w") as f:
            f.write(f"tag: {tag}\n")
            f.write(f"total_candidates: {len(lines)}\n")
            if len(lengths):
                f.write(f"min_length_m: {lengths.min():.2f}\n")
                f.write(f"max_length_m: {lengths.max():.2f}\n")
                f.write(f"mean_length_m: {lengths.mean():.2f}\n")
                f.write(f"median_length_m: {np.median(lengths):.2f}\n")

    return lines


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sweep", action="store_true",
                        help="try 4 parameter sets")
    args = parser.parse_args()

    stack_path = DERIVED / "stack_20m.tif"
    log(f"Reading stack: {stack_path}")
    with rasterio.open(stack_path) as src:
        stack = src.read().astype(np.float32)
    log(f"  shape: {stack.shape}")

    if args.sweep:
        sweep = [
            {"canny_low": 0.08, "canny_high": 0.20, "vote_min": 3,
             "hough_min_length": 15, "hough_max_gap": 4,
             "merge_angle_deg": 10, "merge_gap_m": 80,
             "min_length_m": 500, "canny_sigma": 1.5,
             "tag": "vote3_canny08"},
            {"canny_low": 0.10, "canny_high": 0.25, "vote_min": 4,
             "hough_min_length": 15, "hough_max_gap": 4,
             "merge_angle_deg": 10, "merge_gap_m": 80,
             "min_length_m": 500, "canny_sigma": 1.5,
             "tag": "vote4_canny10"},
            {"canny_low": 0.12, "canny_high": 0.30, "vote_min": 4,
             "hough_min_length": 15, "hough_max_gap": 4,
             "merge_angle_deg": 10, "merge_gap_m": 80,
             "min_length_m": 500, "canny_sigma": 1.5,
             "tag": "vote4_canny12"},
            {"canny_low": 0.10, "canny_high": 0.25, "vote_min": 5,
             "hough_min_length": 15, "hough_max_gap": 4,
             "merge_angle_deg": 10, "merge_gap_m": 80,
             "min_length_m": 500, "canny_sigma": 1.5,
             "tag": "vote5_canny10"},
        ]
        print("\n=== Sweep mode: 4 parameter sets ===\n")
        for p in sweep:
            tag = p.pop("tag")
            out = DERIVED / f"candidates_{tag}.geojson"
            stats = DERIVED / f"candidates_{tag}_stats.txt"
            run_pipeline(stack, p, save_path=out, stats_path=stats, tag=tag)
            print()

        print("Sweep complete. Compare the *_stats.txt files.")
    else:
        params = dict(DEFAULTS)
        run_pipeline(
            stack, params,
            save_path=DERIVED / "candidates.geojson",
            stats_path=DERIVED / "candidates_stats.txt",
            tag="default",
        )
        log("\nDone.")


if __name__ == "__main__":
    main()