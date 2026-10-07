"""
candidates.py -- generate candidate lineaments from the feature stack.

Usage:
    python -m src.offline.candidates

Input:
    data/derived/stack_20m.tif   (25 bands, EPSG:32632, 20 m)

Output:
    data/derived/candidates.geojson   (LineString features, EPSG:32632)
    data/derived/candidates_stats.txt (summary)
"""

import sys
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
from sklearn.decomposition import PCA

from src.config import (
    DERIVED, GRID, CRS_PROJECTED,
    CANNY_SIGMA, CANNY_LOW, CANNY_HIGH,
    HOUGH_MIN_LENGTH, HOUGH_MAX_GAP,
    MIN_LENGTH_M,
)


# ---------- constants ----------

# Band indices in the 25-layer stack (0-indexed)
BAND_VV       = 0
BAND_VH       = 1
BAND_S2_START = 4    # B02
BAND_S2_END   = 9    # B12 (inclusive)
BAND_HS_START = 16   # hillshade_000
BAND_HS_END   = 19   # hillshade_135 (inclusive)

RES = GRID["res"]
SHAPE = (
    (GRID["y_max"] - GRID["y_min"]) // RES,   # rows = 1669
    (GRID["x_max"] - GRID["x_min"]) // RES,   # cols = 1672
)

# Affine transform: pixel (col,row) -> world (x,y) in EPSG:32632
TRANSFORM = Affine(
    RES, 0, GRID["x_min"],
    0, -RES, GRID["y_max"],
)


def log(msg):
    print(msg, flush=True)


# ---------- input selection ----------

def robust_normalize(band, p_low=2, p_high=98):
    """Clip to [p_low, p_high] percentile and rescale to [0, 1]."""
    finite = band[np.isfinite(band)]
    if finite.size == 0:
        return np.zeros_like(band, dtype=np.float32)
    lo, hi = np.percentile(finite, [p_low, p_high])
    if hi <= lo:
        return np.zeros_like(band, dtype=np.float32)
    return np.clip((band - lo) / (hi - lo), 0, 1).astype(np.float32)


def compute_pc1_of_s2(s2_bands):
    """Compute first principal component of Sentinel-2 bands."""
    n_bands, H, W = s2_bands.shape
    # Normalize each band
    norm = np.zeros_like(s2_bands, dtype=np.float32)
    for i in range(n_bands):
        norm[i] = robust_normalize(s2_bands[i])

    # Fill NaN with column-wise median before PCA
    norm = np.nan_to_num(norm, nan=0.0, posinf=0.0, neginf=0.0)

    # Reshape to (n_samples, n_bands)
    flat = norm.reshape(n_bands, -1).T   # (H*W, n_bands)

    pca = PCA(n_components=1, random_state=42)
    pc1 = pca.fit_transform(flat).reshape(H, W)

    # Robust-normalize the result
    return robust_normalize(pc1)


# ---------- edge detection ----------

def build_edge_inputs(stack):
    """Return a list of (name, 2D array) for edge detection."""
    log("Selecting edge-detection inputs...")
    inputs = []

    # 4 hillshades
    for i in range(BAND_HS_START, BAND_HS_END + 1):
        name = ["hillshade_000", "hillshade_045",
                "hillshade_090", "hillshade_135"][i - BAND_HS_START]
        inputs.append((name, robust_normalize(stack[i])))

    # Sentinel-1 VV and VH
    inputs.append(("VV_mean", robust_normalize(stack[BAND_VV])))
    inputs.append(("VH_mean", robust_normalize(stack[BAND_VH])))

    # PC1 of Sentinel-2
    s2 = stack[BAND_S2_START:BAND_S2_END + 1]
    inputs.append(("S2_PC1", compute_pc1_of_s2(s2)))

    log(f"  using {len(inputs)} edge inputs")
    for name, _ in inputs:
        log(f"    - {name}")
    return inputs


def run_canny(inputs):
    """Apply Canny to each input; return list of boolean edge maps."""
    log("Applying Canny edge detection...")
    edges = []
    for name, arr in inputs:
        e = canny(arr, sigma=CANNY_SIGMA,
                  low_threshold=CANNY_LOW, high_threshold=CANNY_HIGH)
        log(f"  {name}: {e.sum():>8d} edge pixels")
        edges.append(e)
    return edges


def vote_count(edges, min_votes=2):
    """Return binary mask where at least min_votes edge maps agree."""
    log(f"Vote-counting (threshold = {min_votes})...")
    votes = np.zeros_like(edges[0], dtype=np.uint8)
    for e in edges:
        votes += e.astype(np.uint8)
    mask = votes >= min_votes
    log(f"  {mask.sum()} pixels passed the vote threshold")
    return mask


# ---------- line extraction ----------

def extract_segments(mask):
    """Skeletonize the mask and extract line segments with Hough."""
    log("Skeletonizing...")
    skel = skeletonize(mask)
    log(f"  {skel.sum()} skeleton pixels")

    log("Running probabilistic Hough transform...")
    segments_px = probabilistic_hough_line(
        skel,
        threshold=10,
        line_length=HOUGH_MIN_LENGTH,
        line_gap=HOUGH_MAX_GAP,
    )
    log(f"  {len(segments_px)} raw segments detected")
    return segments_px


def pixel_to_world(segments_px):
    """Convert pixel segments to world coordinates (EPSG:32632)."""
    log("Converting pixel coordinates to EPSG:32632...")
    lines = []
    for (x0, y0), (x1, y1) in segments_px:
        wx0, wy0 = TRANSFORM * (x0, y0)
        wx1, wy1 = TRANSFORM * (x1, y1)
        lines.append(LineString([(wx0, wy0), (wx1, wy1)]))
    return lines


def filter_by_length(lines, min_m):
    log(f"Filtering by length >= {min_m} m...")
    kept = [ln for ln in lines if ln.length >= min_m]
    log(f"  {len(kept)} of {len(lines)} segments retained")
    return kept


# ---------- main ----------

def main():
    stack_path = DERIVED / "stack_20m.tif"
    out_path = DERIVED / "candidates.geojson"
    stats_path = DERIVED / "candidates_stats.txt"

    log(f"Reading stack: {stack_path}")
    with rasterio.open(stack_path) as src:
        stack = src.read().astype(np.float32)

    log(f"  stack shape: {stack.shape}")

    # 1. Prepare inputs
    inputs = build_edge_inputs(stack)

    # 2. Canny
    edges = run_canny(inputs)

    # 3. Vote count
    mask = vote_count(edges, min_votes=2)

    # 4. Extract segments
    segments_px = extract_segments(mask)

    # 5. Georeference
    lines = pixel_to_world(segments_px)

    # 6. Filter by length
    lines = filter_by_length(lines, MIN_LENGTH_M)

    # 7. Save GeoJSON
    gdf = gpd.GeoDataFrame(
        {
            "id": range(len(lines)),
            "length_m": [round(ln.length, 2) for ln in lines],
        },
        geometry=lines,
        crs=CRS_PROJECTED,
    )
    gdf.to_file(out_path, driver="GeoJSON")
    log(f"\nSaved {len(gdf)} candidates to {out_path}")

    # 8. Stats
    lengths = gdf["length_m"].values
    with open(stats_path, "w") as f:
        f.write(f"Total candidates: {len(gdf)}\n")
        f.write(f"Min length (m): {lengths.min():.2f}\n")
        f.write(f"Max length (m): {lengths.max():.2f}\n")
        f.write(f"Mean length (m): {lengths.mean():.2f}\n")
        f.write(f"Median length (m): {np.median(lengths):.2f}\n")
    log(f"Stats saved to {stats_path}")

    log("\nDone.")


if __name__ == "__main__":
    main()