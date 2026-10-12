"""
sample_training.py -- generate training samples directly from the
reference set and AOI, independent of the candidate set.

Positives: 500 m sub-segments of the reference lines.
Negatives: random 500 m segments >200 m from any reference and >100 m
           from any OSM road, at random azimuths.

Usage:
    python -m src.offline.sample_training

Output:
    data/derived/training_samples.parquet
    data/derived/training_samples.geojson
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import LineString, Point
from shapely.ops import substring
from skimage.measure import profile_line
import rasterio

from src.config import (
    DERIVED, REFERENCE, OSM, GRID, ALL_LAYERS,
)


# --- Sampling parameters ---
SEGMENT_M       = 500     # length of each training segment
N_NEGATIVES     = 800     # target number of negative samples
NEG_MIN_DIST_REF = 200    # metres: min distance to any reference line
NEG_MIN_DIST_RD  = 100    # metres: min distance to any OSM road
RANDOM_SEED     = 42


def log(msg):
    print(msg, flush=True)


def azimuth(geom):
    coords = list(geom.coords)
    (x0, y0), (x1, y1) = coords[0], coords[-1]
    return float(np.degrees(np.arctan2(y1 - y0, x1 - x0)) % 180.0)


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
    off_r, off_c = nr * offset_pixels, nc * offset_pixels
    return sample_profile(band, (r0 + off_r, c0 + off_c),
                          (r1 + off_r, c1 + off_c))


def features_for_segment(line, stack, transform, band_index,
                          sample_layers, contrast_layers, tag, sample_id):
    """Compute the same 59 features for a synthetic segment."""
    coords = list(line.coords)
    x0, y0 = coords[0]
    x1, y1 = coords[-1]

    length_m = float(line.length)
    azimuth_v = azimuth(line)

    rec = {
        "sample_id": sample_id,
        "kind": tag,
        "length_m": length_m,
        "azimuth": azimuth_v,
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

    return rec


def main():
    rng = np.random.default_rng(RANDOM_SEED)

    log("Loading stack...")
    with rasterio.open(DERIVED / "stack_20m.tif") as src:
        stack = src.read().astype(np.float32)
        transform = src.transform

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

    log("Loading reference lineaments...")
    refs = gpd.read_file(REFERENCE / "reference_lineaments.geojson")

    # --- Positives: 500 m sub-segments of each reference line ---
    log(f"\nSampling positives ({SEGMENT_M} m segments)...")
    positives = []
    for ref_geom in refs.geometry:
        total = ref_geom.length
        if total < SEGMENT_M:
            continue
        n = int(total // SEGMENT_M)
        for i in range(n):
            start = i * SEGMENT_M
            end = start + SEGMENT_M
            seg = substring(ref_geom, start, end)
            if seg.geom_type == "LineString" and seg.length > 0:
                positives.append(seg)
    log(f"  {len(positives)} positive segments")

    # --- Negatives: random segments in AOI ---
    log(f"\nSampling negatives (target {N_NEGATIVES})...")
    log("  Loading OSM roads...")
    try:
        roads = gpd.read_file(OSM / "osm_roads.gpkg")
    except Exception:
        roads = gpd.GeoDataFrame()

    log("  Building spatial indices...")
    ref_sindex = refs.sindex
    road_sindex = roads.sindex if len(roads) else None

    x_min = GRID["x_min"]
    y_min = GRID["y_min"]
    x_max = GRID["x_max"]
    y_max = GRID["y_max"]

    negatives = []
    attempts = 0
    max_attempts = N_NEGATIVES * 20

    while len(negatives) < N_NEGATIVES and attempts < max_attempts:
        attempts += 1

        # Random midpoint and random azimuth
        cx = rng.uniform(x_min + 500, x_max - 500)
        cy = rng.uniform(y_min + 500, y_max - 500)
        az = rng.uniform(0, 180)
        theta = np.radians(az)
        dx = np.cos(theta) * SEGMENT_M / 2
        dy = np.sin(theta) * SEGMENT_M / 2
        seg = LineString([(cx - dx, cy - dy), (cx + dx, cy + dy)])

        # Reject if too close to any reference
        cand_idx = list(ref_sindex.query(seg.buffer(NEG_MIN_DIST_REF)))
        if cand_idx and refs.geometry.iloc[cand_idx].distance(seg).min() < NEG_MIN_DIST_REF:
            continue

        # Reject if too close to any road
        if road_sindex is not None:
            cand_idx = list(road_sindex.query(seg.buffer(NEG_MIN_DIST_RD)))
            if cand_idx and roads.geometry.iloc[cand_idx].distance(seg).min() < NEG_MIN_DIST_RD:
                continue

        negatives.append(seg)

    log(f"  {len(negatives)} negative segments ({attempts} attempts)")

    # --- Compute features ---
    log("\nComputing features for positives...")
    pos_records = []
    for i, seg in enumerate(positives):
        rec = features_for_segment(seg, stack, transform, band_index,
                                   sample_layers, contrast_layers,
                                   "positive", i)
        pos_records.append(rec)
        if (i + 1) % 50 == 0:
            log(f"  {i+1}/{len(positives)}")

    log("\nComputing features for negatives...")
    neg_records = []
    for i, seg in enumerate(negatives):
        rec = features_for_segment(seg, stack, transform, band_index,
                                   sample_layers, contrast_layers,
                                   "negative", i)
        neg_records.append(rec)
        if (i + 1) % 100 == 0:
            log(f"  {i+1}/{len(negatives)}")

    # --- Combine and save ---
    df = pd.DataFrame(pos_records + neg_records)
    df["label"] = df["kind"]

    out_parquet = DERIVED / "training_samples.parquet"
    df.to_parquet(out_parquet, index=False)
    log(f"\nSaved {len(df)} training samples to {out_parquet}")
    log(f"  positives: {(df['kind']=='positive').sum()}")
    log(f"  negatives: {(df['kind']=='negative').sum()}")

    # Also save geometry as GeoJSON for inspection
    gdf = gpd.GeoDataFrame(
        df,
        geometry=positives + negatives,
        crs="EPSG:32632",
    )
    gdf.to_file(DERIVED / "training_samples.geojson", driver="GeoJSON")
    log(f"Saved geometries to {DERIVED / 'training_samples.geojson'}")

    log("\nDone.")


if __name__ == "__main__":
    main()