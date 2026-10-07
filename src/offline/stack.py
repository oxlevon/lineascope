"""
stack.py -- build the 25-layer feature stack for LineaScope.

Usage:
    python -m src.offline.stack

Output:
    data/derived/stack_20m.tif   (25 bands, EPSG:32632, 20 m)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import numpy as np
import rasterio
from rasterio.transform import from_bounds
from rasterio.features import rasterize
from rasterio.warp import reproject, Resampling
from scipy import ndimage
import geopandas as gpd

from src.config import (
    RAW, OSM, DERIVED, GRID, CRS_PROJECTED,
    S1_LAYERS, S2_LAYERS, DEM_LAYERS, ANCILLARY_LAYERS, ALL_LAYERS,
    GRID_WIDTH, GRID_HEIGHT,
)

TRANSFORM = from_bounds(
    GRID["x_min"], GRID["y_min"],
    GRID["x_max"], GRID["y_max"],
    GRID_WIDTH, GRID_HEIGHT,
)
RES = GRID["res"]
SHAPE = (GRID_HEIGHT, GRID_WIDTH)   # (rows, cols)


# ---------- helpers ----------

def log(msg):
    print(msg, flush=True)


def read_aligned(path):
    """Read a raster already on the target grid."""
    with rasterio.open(path) as src:
        data = src.read()
    return data


def save_stack(layers, path):
    """Write dict of {name: 2D array} to a multiband GeoTIFF."""
    names = list(layers.keys())
    stack = np.stack([layers[n] for n in names]).astype(np.float32)
    profile = {
        "driver": "GTiff",
        "height": SHAPE[0],
        "width": SHAPE[1],
        "count": len(names),
        "dtype": "float32",
        "crs": CRS_PROJECTED,
        "transform": TRANSFORM,
        "compress": "lzw",
        "tiled": True,
        "blockxsize": 256,
        "blockysize": 256,
    }
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(stack)
        for i, n in enumerate(names, 1):
            dst.set_band_description(i, n)
    log(f"  wrote {len(names)} bands to {path}")


# ---------- DEM derivatives ----------

def compute_dem_layers(dem):
    """Compute slope, aspect, hillshades, curvature, TPI."""
    out = {}
    out["elevation"] = dem

    # slope & aspect from gradient (in metres)
    dy, dx = np.gradient(dem, RES)
    slope_rad = np.arctan(np.sqrt(dx ** 2 + dy ** 2))
    out["slope"] = np.degrees(slope_rad)

    # aspect as sine/cosine (avoids the 0/360 wrap problem)
    aspect_rad = np.arctan2(-dy, dx)
    out["aspect_sin"] = np.sin(aspect_rad)
    out["aspect_cos"] = np.cos(aspect_rad)

    # hillshades at 4 azimuths, altitude 45 deg
    altitude = np.radians(45.0)
    zenith = np.pi / 2 - altitude
    for az in [0, 45, 90, 135]:
        az_rad = np.radians(az)
        hs = (np.cos(zenith) * np.cos(slope_rad) +
              np.sin(zenith) * np.sin(slope_rad) *
              np.cos(az_rad - aspect_rad))
        out[f"hillshade_{az:03d}"] = np.clip(hs, 0, 1)

    # curvature = Laplacian
    out["curvature"] = ndimage.laplace(dem)

    # TPI = elevation - local mean (window 5x5)
    local_mean = ndimage.uniform_filter(dem, size=5)
    out["tpi"] = dem - local_mean

    return out


# ---------- spectral indices ----------

def compute_s2_layers(s2):
    """s2 is (6, H, W): B02, B03, B04, B08, B11, B12."""
    out = {}
    names = ["B02", "B03", "B04", "B08", "B11", "B12"]
    for i, n in enumerate(names):
        out[n] = s2[i]

    # NDVI = (NIR - Red) / (NIR + Red)
    nir = s2[3].astype(np.float32)
    red = s2[2].astype(np.float32)
    denom = nir + red
    denom[denom == 0] = 1e-6
    out["NDVI"] = (nir - red) / denom

    # B11/B12 ratio
    b11 = s2[4].astype(np.float32)
    b12 = s2[5].astype(np.float32)
    denom2 = b12.copy()
    denom2[denom2 == 0] = 1e-6
    out["B11_B12_ratio"] = b11 / denom2

    return out


# ---------- OSM-derived distances ----------

def osm_distance(gdf_path, name):
    """Rasterise OSM features and compute Euclidean distance in metres."""
    log(f"  computing distance to {name}...")
    gdf = gpd.read_file(gdf_path)
    if gdf.empty:
        log(f"    ! {name} is empty, filling with a large constant")
        return np.full(SHAPE, 9999.0, dtype=np.float32)

    shapes = [(geom, 1) for geom in gdf.geometry if geom is not None]
    if not shapes:
        log(f"    ! {name} has no valid geometries, filling with 9999")
        return np.full(SHAPE, 9999.0, dtype=np.float32)

    mask = rasterize(
        shapes,
        out_shape=SHAPE,
        transform=TRANSFORM,
        fill=0,
        all_touched=True,
    )
    dist_pixels = ndimage.distance_transform_edt(mask == 0)
    return (dist_pixels * RES).astype(np.float32)


# ---------- WorldCover built-up fraction ----------

def compute_builtup(wc_path):
    """Resample 10m WorldCover to 20m, return fraction that is built-up (class 50)."""
    log("  computing built-up fraction from WorldCover...")
    with rasterio.open(wc_path) as src:
        wc = src.read(1)
        src_transform = src.transform
        src_crs = src.crs

    # binary mask: is built-up?
    is_built = (wc == 50).astype(np.float32)

    # reproject/average to 20m grid
    out = np.zeros(SHAPE, dtype=np.float32)
    reproject(
        source=is_built,
        destination=out,
        src_transform=src_transform,
        src_crs=src_crs,
        dst_transform=TRANSFORM,
        dst_crs=CRS_PROJECTED,
        resampling=Resampling.average,
    )
    return np.clip(out, 0, 1)


# ---------- main ----------

def build():
    DERIVED.mkdir(parents=True, exist_ok=True)

    layers = {}

    # 1. Sentinel-1 (already 4 bands at 20m)
    log("Loading Sentinel-1...")
    s1_asc = read_aligned(RAW / "S1_ASC_mean_std_20m.tif")
    s1_desc = read_aligned(RAW / "S1_DESC_mean_std_20m.tif")

    # Combine ascending and descending by averaging
    # bands: [VV_mean, VH_mean, VV_std, VH_std] (in each file)
    # We produce: VV_mean (avg), VH_mean (avg), VV_std (avg), VH_std (avg)
    s1_combined = (s1_asc + s1_desc) / 2.0
    for i, name in enumerate(S1_LAYERS):
        layers[name] = s1_combined[i].astype(np.float32)

    # 2. Sentinel-2 (6 bands, add 2 indices)
    log("Loading Sentinel-2...")
    s2 = read_aligned(RAW / "S2_median_6band_20m.tif").astype(np.float32)
    s2_layers = compute_s2_layers(s2)
    layers.update(s2_layers)

    # 3. DEM derivatives
    log("Computing DEM derivatives...")
    dem = read_aligned(RAW / "CopDEM_GLO30_20m.tif")[0].astype(np.float32)
    layers.update(compute_dem_layers(dem))

    # 4. OSM distances
    log("Computing OSM distances...")
    layers["dist_road"]     = osm_distance(OSM / "osm_roads.gpkg", "roads")
    layers["dist_waterway"] = osm_distance(OSM / "osm_waterways.gpkg", "waterways")

    # 5. WorldCover built-up fraction
    layers["builtup_fraction"] = compute_builtup(RAW / "WorldCover_2021_10m.tif")

    # 6. Verify all expected layers exist
    missing = [n for n in ALL_LAYERS if n not in layers]
    if missing:
        log(f"  ! missing layers: {missing}")
    extra = [n for n in layers if n not in ALL_LAYERS]
    if extra:
        log(f"  ! unexpected extra layers: {extra}")

    log(f"\nTotal layers prepared: {len(layers)}")
    for n in layers:
        log(f"  - {n}")

    # 7. Save
    out_path = DERIVED / "stack_20m.tif"
    log(f"\nWriting stack to {out_path}")
    save_stack(layers, out_path)

    log("\nDone.")


if __name__ == "__main__":
    build()