"""
verify_candidates.py -- verify the candidate set meets SDP requirements.

Usage:
    python scripts/verify_candidates.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import geopandas as gpd

from src.config import DERIVED, GRID

gdf = gpd.read_file(DERIVED / "candidates.geojson")

print("=" * 60)
print("CANDIDATE VERIFICATION")
print("=" * 60)

# --- 1. Count ---
n = len(gdf)
print(f"\n1. Total candidates: {n}")
print(f"   SDP target: 2,000 - 8,000")
if 2000 <= n <= 8000:
    print(f"   ✅ PASS — within target range")
else:
    print(f"   ❌ FAIL — outside target range")

# --- 2. Lengths ---
lengths = gdf["length_m"].values
print(f"\n2. Segment lengths (m):")
print(f"   Min:    {lengths.min():.2f}")
print(f"   Max:    {lengths.max():.2f}")
print(f"   Mean:   {lengths.mean():.2f}")
print(f"   Median: {np.median(lengths):.2f}")
print(f"   SDP min length: 400 m")
if lengths.min() >= 400:
    print(f"   ✅ PASS — all segments >= 400 m")
else:
    print(f"   ❌ FAIL — some segments below 400 m")

# --- 3. Spatial extent ---
print(f"\n3. Spatial extent (EPSG:32632):")
bounds = gdf.total_bounds
print(f"   X: {bounds[0]:.0f} to {bounds[2]:.0f}")
print(f"   Y: {bounds[1]:.0f} to {bounds[3]:.0f}")
print(f"   Study area X: {GRID['x_min']} to {GRID['x_max']}")
print(f"   Study area Y: {GRID['y_min']} to {GRID['y_max']}")

inside = (
    (bounds[0] >= GRID["x_min"] - 100) and
    (bounds[2] <= GRID["x_max"] + 100) and
    (bounds[1] >= GRID["y_min"] - 100) and
    (bounds[3] <= GRID["y_max"] + 100)
)
if inside:
    print(f"   ✅ PASS — all candidates within study area")
else:
    print(f"   ⚠️  WARN — some candidates outside study area")

# --- 4. CRS ---
print(f"\n4. CRS:")
print(f"   Candidates: {gdf.crs}")
print(f"   Expected:   EPSG:32632")
if gdf.crs.to_epsg() == 32632:
    print(f"   ✅ PASS")
else:
    print(f"   ❌ FAIL")

# --- 5. Spatial spread (are they clustered or spread out?) ---
print(f"\n5. Spatial spread:")
# Divide the AOI into 6x6 = 36 bins, count candidates per bin
bin_x = np.linspace(GRID["x_min"], GRID["x_max"], 7)
bin_y = np.linspace(GRID["y_min"], GRID["y_max"], 7)
centroids = gdf.geometry.centroid
xs = centroids.x.values
ys = centroids.y.values
hist, _, _ = np.histogram2d(xs, ys, bins=[bin_x, bin_y])
nonzero = (hist > 0).sum()
total_cells = 36
print(f"   Cells occupied: {nonzero} of {total_cells} ({100*nonzero/total_cells:.0f}%)")
if nonzero >= 30:
    print(f"   ✅ PASS — candidates cover the study area")
elif nonzero >= 20:
    print(f"   ⚠️  WARN — moderately clustered")
else:
    print(f"   ❌ FAIL — heavily clustered")

# --- 6. Azimuth distribution ---
print(f"\n6. Azimuth distribution:")
def azimuth(geom):
    coords = list(geom.coords)
    (x0, y0), (x1, y1) = coords[0], coords[-1]
    ang = np.degrees(np.arctan2(y1 - y0, x1 - x0)) % 180.0
    return ang

azimuths = gdf.geometry.apply(azimuth).values
hist_az, edges = np.histogram(azimuths, bins=9, range=(0, 180))
labels = [f"{int(edges[i])}-{int(edges[i+1])}°" for i in range(9)]
for label, count in zip(labels, hist_az):
    bar = "█" * int(count / hist_az.max() * 40)
    print(f"   {label:>10}  {count:>5}  {bar}")

print()
print("=" * 60)
print("VERIFICATION COMPLETE")
print("=" * 60)