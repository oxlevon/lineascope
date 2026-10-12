"""
features.py -- compute geometric, spectral, radar, topographic, and
cultural features for each candidate lineament.

Usage:
    python -m src.offline.features

Input:
    data/derived/candidates.geojson
    data/derived/stack_20m.tif

Output:
    data/derived/candidate_features.parquet
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import numpy as np
import pandas as pd
import rasterio
import geopandas as gpd
from skimage.measure import profile_line

from src.config import DERIVED, GRID, ALL_LAYERS


RES = GRID["res"]
SHAPE = (
    (GRID["y_max"] - GRID["y_min"]) // RES,
    (GRID["x_max"] - GRID["x_min"]) // RES,
)


def log(msg):
    print(msg, flush=True)


def world_to_pixel(transform, x, y):
    col, row = ~transform * (x, y)
    return row, col


def sample_profile(band, p0, p1, width=1):
    try:
        return profile_line(band, p0, p1, linewidth=width,
                            order=1, mode="constant", cval=np.nan)
    except Exception:
        return np.array([np.nan])


def safe_stats(values):
    v = values[~np.isnan(values)]
    if v.size == 0:
        return np.nan, np.nan
    return float(np.mean(v)), float(np.std(v))


def sample_offset_line(band, p0, p1, offset_pixels):
    r0, c0 = p0
    r1, c1 = p1
    dr, dc = r1 - r0, c1 - c0
    L = np.hypot(dr, dc)
    if L < 1e-6:
        return np.array([np.nan])
    nr, nc = -dc / L, dr / L
    off_r = nr * offset_pixels
    off_c = nc * offset_pixels
    return sample_profile(band, (r0 + off_r, c0 + off_c),
                          (r1 + off_r, c1 + off_c))


def main():
    stack_path = DERIVED / "stack_20m.tif"
    cand_path = DERIVED / "candidates.geojson"
    out_path = DERIVED / "candidate_features.parquet"

    log(f"Loading stack: {stack_path}")
    with rasterio.open(stack_path) as src:
        stack = src.read().astype(np.float32)
        transform = src.transform
    log(f"  stack shape: {stack.shape}")

    log(f"Loading candidates: {cand_path}")
    cands = gpd.read_file(cand_path)
    log(f"  {len(cands)} candidates")

    band_index = {name: i for i, name in enumerate(ALL_LAYERS)}

    sample_layers = (
        ["VV_mean", "VH_mean", "VV_std", "VH_std",
         "B02", "B03", "B04", "B08", "B11", "B12",
         "NDVI", "B11_B12_ratio",
         "elevation", "slope", "aspect_sin", "aspect_cos",
         "hillshade_000", "hillshade_045",
         "hillshade_090", "hillshade_135",
         "curvature", "tpi",
         "dist_road", "dist_waterway", "builtup_fraction"]
    )

    contrast_layers = ["VV_mean", "VH_mean", "NDVI", "hillshade_090"]

    records = []
    n = len(cands)
    t0 = time.time()

    for i, row in cands.iterrows():
        line = row.geometry
        coords = list(line.coords)
        if len(coords) < 2:
            continue

        x0, y0 = coords[0]
        x1, y1 = coords[-1]

        length_m = float(line.length)
        dx = x1 - x0
        dy = y1 - y0
        azimuth = float(np.degrees(np.arctan2(dy, dx)) % 180.0)

        rec = {
            "candidate_id": int(row["id"]),
            "length_m": length_m,
            "azimuth": azimuth,
            "x_mid": (x0 + x1) / 2,
            "y_mid": (y0 + y1) / 2,
        }

        p0 = world_to_pixel(transform, x0, y0)
        p1 = world_to_pixel(transform, x1, y1)

        for name in sample_layers:
            band = stack[band_index[name]]
            prof = sample_profile(band, p0, p1)
            mean_v, std_v = safe_stats(prof)
            rec[f"{name}_mean"] = mean_v
            rec[f"{name}_std"] = std_v

        for name in contrast_layers:
            band = stack[band_index[name]]
            line_prof = sample_profile(band, p0, p1)
            left_prof = sample_offset_line(band, p0, p1, +3)
            right_prof = sample_offset_line(band, p0, p1, -3)
            line_mean, _ = safe_stats(line_prof)
            left_mean, _ = safe_stats(left_prof)
            right_mean, _ = safe_stats(right_prof)
            flank_mean = np.nanmean([left_mean, right_mean])
            rec[f"{name}_contrast"] = line_mean - flank_mean

        records.append(rec)

        if (i + 1) % 500 == 0:
            elapsed = time.time() - t0
            rate = (i + 1) / elapsed
            eta = (n - i - 1) / rate
            log(f"  {i+1}/{n} ({rate:.0f}/s, ETA {eta:.0f}s)")

    df = pd.DataFrame(records)
    df.to_parquet(out_path, index=False)
    log(f"\nSaved {len(df)} rows x {len(df.columns)} features to {out_path}")
    log(f"Total time: {time.time() - t0:.0f} s")
    log("\nDone.")


if __name__ == "__main__":
    main()