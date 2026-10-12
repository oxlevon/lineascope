"""
diagnose_labels.py -- check if reference lines and candidates are
actually in the same place.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from src.config import DERIVED, REFERENCE

cands = gpd.read_file(DERIVED / "candidates.geojson")
refs  = gpd.read_file(REFERENCE / "reference_lineaments.geojson")

print("=" * 65)
print("CANDIDATES")
print("=" * 65)
print(f"  Count:        {len(cands)}")
print(f"  CRS:          {cands.crs}")
print(f"  Total length: {cands.length.sum()/1000:.1f} km")
b = cands.total_bounds
print(f"  Bounds:  X {b[0]:.0f} – {b[2]:.0f}")
print(f"           Y {b[1]:.0f} – {b[3]:.0f}")
cx, cy = cands.unary_union.centroid.x, cands.unary_union.centroid.y
print(f"  Centroid: ({cx:.0f}, {cy:.0f})")

print()
print("=" * 65)
print("REFERENCE LINEAMENTS")
print("=" * 65)
print(f"  Count:        {len(refs)}")
print(f"  CRS:          {refs.crs}")
print(f"  Total length: {refs.length.sum()/1000:.1f} km")
b = refs.total_bounds
print(f"  Bounds:  X {b[0]:.0f} – {b[2]:.0f}")
print(f"           Y {b[1]:.0f} – {b[3]:.0f}")
cx, cy = refs.unary_union.centroid.x, refs.unary_union.centroid.y
print(f"  Centroid: ({cx:.0f}, {cy:.0f})")

print()
print("=" * 65)
print("OVERLAP CHECK")
print("=" * 65)
# How many reference lines have ANY candidate within 100 m?
ref_buffers = refs.geometry.buffer(100)
hits = 0
for buf in ref_buffers:
    n = cands[cands.intersects(buf)]
    if len(n) > 0:
        hits += 1
print(f"  Reference lines with >=1 candidate within 100 m: {hits}/{len(refs)}")

# Reverse: how many candidates are within 100 m of ANY reference?
cand_buffers = cands.geometry
total_hits = 0
for cb in cand_pts.geometry if False else cands.geometry:
    if refs.distance(cb).min() <= 100:
        total_hits += 1
print(f"  Candidates within 100 m of ANY reference: {total_hits}/{len(cands)}")

# --- Save a visual comparison ---
fig, axes = plt.subplots(1, 2, figsize=(16, 8), dpi=100)

for ax, gdf, title, color in [
    (axes[0], cands, f"Candidates ({len(cands)})", "yellow"),
    (axes[1], refs, f"Reference lines ({len(refs)})", "cyan"),
]:
    gdf.plot(ax=ax, color=color, linewidth=0.6)
    ax.set_title(title, fontsize=12)
    ax.set_xlim(167620, 201060)
    ax.set_ylim(625200, 658580)
    ax.set_aspect("equal")

plt.tight_layout()
out = DERIVED / "diagnose_spatial_layout.png"
plt.savefig(out, dpi=100, bbox_inches="tight")
print(f"\nSaved visual diagnostic to {out}")