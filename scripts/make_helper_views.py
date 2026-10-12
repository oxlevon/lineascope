"""
make_helper_views.py -- generate helper rasters for QGIS digitising.

Outputs:
    data/derived/helper_combined_hillshade.tif
    data/derived/helper_edge_overlay.tif
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import rasterio
from rasterio.transform import Affine
from skimage.feature import canny

from src.config import DERIVED, GRID

RES = GRID["res"]
SHAPE = (
    (GRID["y_max"] - GRID["y_min"]) // RES,
    (GRID["x_max"] - GRID["x_min"]) // RES,
)
TRANSFORM = Affine(
    RES, 0, GRID["x_min"],
    0, -RES, GRID["y_max"],
)

stack_path = DERIVED / "stack_20m.tif"
print(f"Reading {stack_path}")
with rasterio.open(stack_path) as src:
    stack = src.read().astype(np.float32)
    profile = src.profile.copy()

# --- Combined hillshade: average of the 4 hillshades ---
print("Computing combined hillshade...")
hs_bands = stack[16:20]   # hillshade_000, 045, 090, 135
combined = np.mean(hs_bands, axis=0)

# Normalize to 0-255 for display
lo, hi = np.percentile(combined[np.isfinite(combined)], [2, 98])
combined_disp = np.clip((combined - lo) / (hi - lo), 0, 1) * 255

combined_path = DERIVED / "helper_combined_hillshade.tif"
profile_out = profile.copy()
profile_out.update(count=1, dtype="uint8", compress="lzw")
with rasterio.open(combined_path, "w", **profile_out) as dst:
    dst.write(combined_disp.astype(np.uint8), 1)
print(f"  wrote {combined_path}")

# --- Edge overlay: canny edges on the combined hillshade ---
print("Computing edge overlay...")
edges = canny(
    combined_disp / 255.0,
    sigma=2.0,
    low_threshold=0.08,
    high_threshold=0.20,
)

# Overlay: hillshade with dark edges
overlay = combined_disp.copy()
overlay[edges] = 0   # black edges

overlay_path = DERIVED / "helper_edge_overlay.tif"
with rasterio.open(overlay_path, "w", **profile_out) as dst:
    dst.write(overlay.astype(np.uint8), 1)
print(f"  wrote {overlay_path}")

print("\nDone. Load these into QGIS as raster layers.")