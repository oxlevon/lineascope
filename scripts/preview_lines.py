"""
preview_lines.py -- generate a synthetic preview of what 100 reference
lineaments would look like on the study-area map.

Usage:
    python scripts/preview_lines.py

Output:
    data/derived/preview_100_lines.png
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch
import rasterio

from src.config import DERIVED, GRID

# Load the real hillshade as background
stack_path = DERIVED / "stack_20m.tif"
with rasterio.open(stack_path) as src:
    hs = src.read(17).astype(np.float32)   # hillshade_000

# Robust stretch for display
lo, hi = np.percentile(hs[np.isfinite(hs)], [2, 98])
hs_disp = np.clip((hs - lo) / (hi - lo), 0, 1)

# Figure setup
fig, ax = plt.subplots(figsize=(10, 10), dpi=100)
ax.imshow(hs_disp, cmap="gray", extent=[0, 1672, 1669, 0])

# Realistic lineament azimuth distribution (peaks at ~50 deg and ~130 deg)
rng = np.random.default_rng(42)
n_lines = 100

# Azimuths: bimodal
az_a = rng.normal(50, 15, size=50) % 180    # NE-SW family
az_b = rng.normal(130, 15, size=50) % 180   # NW-SE family
azimuths = np.concatenate([az_a, az_b])

# Lengths: 500m to 5000m, in pixels (1 pixel = 20m)
lengths_m = rng.gamma(shape=2.0, scale=700.0, size=n_lines) + 500
lengths_m = np.clip(lengths_m, 500, 5000)
lengths_px = lengths_m / 20.0

# Positions: place them near "features" -- cluster them by choosing
# a set of 20 anchor points and drawing ~5 lines near each
anchors_x = rng.uniform(100, 1572, size=20)
anchors_y = rng.uniform(100, 1569, size=20)

# The real AOI boundary (in pixels): whole image
ax.add_patch(plt.Rectangle((0, 0), 1672, 1669, fill=False,
                            edgecolor="red", linewidth=1.5, alpha=0.6))

# Draw 100 lines
for i in range(n_lines):
    # pick an anchor
    ax0 = anchors_x[i % 20]
    ay0 = anchors_y[i % 20]

    # add a small jitter so lines aren't all stacked
    cx = ax0 + rng.normal(0, 150)
    cy = ay0 + rng.normal(0, 150)

    # direction
    theta = np.radians(azimuths[i])
    L = lengths_px[i]
    dx = L * np.cos(theta)
    dy = -L * np.sin(theta)   # image y-axis is inverted

    x0, x1 = cx - dx/2, cx + dx/2
    y0, y1 = cy - dy/2, cy + dy/2

    # clip to bounds
    if not (0 <= x0 <= 1672 and 0 <= x1 <= 1672):
        continue
    if not (0 <= y0 <= 1669 and 0 <= y1 <= 1669):
        continue

    ax.plot([x0, x1], [y0, y1], color="cyan", linewidth=1.4, alpha=0.9)

ax.set_xlim(0, 1672)
ax.set_ylim(1669, 0)
ax.set_xticks([])
ax.set_yticks([])
ax.set_title("Preview: what 100 reference lineaments look like\n"
             "(cyan = example reference lines, red = AOI boundary)",
             fontsize=11)

plt.tight_layout()
out_path = DERIVED / "preview_100_lines.png"
plt.savefig(out_path, dpi=100, bbox_inches="tight")
print(f"Saved preview to {out_path}")