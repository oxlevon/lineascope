"""
visualize.py -- generate Chapter Four figures from the pipeline results.

Usage:
    python -m src.offline.visualize

Output:
    results/fig_detected_map.png
    results/fig_rose_detected.png
    results/fig_rose_reference.png
    results/fig_feature_importance.png
    results/fig_ablation_comparison.png
    results/fig_confusion_matrix.png
    results/fig_probability_distribution.png
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import cm

from src.config import DERIVED, REFERENCE, MODELS, RESULTS


def log(msg):
    print(msg, flush=True)


def rose_diagram(ax, azimuths, bins=18, title="Rose"):
    """Plot a rose diagram (polar histogram)."""
    az_rad = np.radians(azimuths)
    # Mirror to full 360
    az_rad_full = np.concatenate([az_rad, az_rad + np.pi])
    hist, edges = np.histogram(az_rad_full, bins=bins * 2, range=(0, 2 * np.pi))
    width = 2 * np.pi / (bins * 2)
    center = (edges[:-1] + edges[1:]) / 2
    ax.bar(center, hist, width=width, bottom=0, color="steelblue", alpha=0.8,
           edgecolor="white", linewidth=0.5)
    ax.set_theta_zero_location("N")
    ax.set_theta_direction(-1)
    ax.set_title(title, fontsize=11)


def fig_detected_map():
    log("Figure: detected lineament map...")
    fig, ax = plt.subplots(figsize=(10, 10), dpi=120)

    # Hillshade as background
    with __import__("rasterio").open(DERIVED / "stack_20m.tif") as src:
        hs = src.read(17).astype(np.float32)
        extent = [src.bounds.left, src.bounds.right,
                  src.bounds.bottom, src.bounds.top]
    lo, hi = np.percentile(hs, [2, 98])
    hs_disp = np.clip((hs - lo) / (hi - lo), 0, 1)
    ax.imshow(hs_disp, cmap="gray", extent=extent, origin="upper")

    # Candidates (light)
    cands = gpd.read_file(DERIVED / "candidates.geojson")
    cands.plot(ax=ax, color="yellow", linewidth=0.15, alpha=0.25)

    # Detected (bold)
    det = gpd.read_file(DERIVED / "detected_lineaments.geojson").to_crs(32632)
    det.plot(ax=ax, color="red", linewidth=0.9)

    ax.set_title(f"Detected lineaments: {len(det)} segments, "
                 f"{det.length.sum()/1000:.1f} km total", fontsize=12)
    ax.set_xticks([]); ax.set_yticks([])
    plt.tight_layout()
    out = RESULTS / "fig_detected_map.png"
    plt.savefig(out, dpi=120, bbox_inches="tight")
    plt.close()
    log(f"  saved {out}")


def fig_rose():
    log("Figure: rose diagrams (detected vs reference)...")

    det = gpd.read_file(DERIVED / "detected_lineaments.geojson")
    ref = gpd.read_file(REFERENCE / "reference_lineaments.geojson")

    fig, axes = plt.subplots(1, 2, figsize=(12, 6),
                              subplot_kw={"projection": "polar"}, dpi=120)
    rose_diagram(axes[0], det["azimuth"].values,
                 title=f"Detected ({len(det)})")
    rose_diagram(axes[1], ref["azimuth"].values,
                 title=f"Reference ({len(ref)})")

    plt.tight_layout()
    out = RESULTS / "fig_rose_comparison.png"
    plt.savefig(out, dpi=120, bbox_inches="tight")
    plt.close()
    log(f"  saved {out}")


def fig_feature_importance():
    log("Figure: feature importance...")
    fi = pd.read_csv(DERIVED / "feature_importance.csv")
    fi = fi.head(20)  # top 20

    fig, ax = plt.subplots(figsize=(9, 7), dpi=120)
    y = np.arange(len(fi))[::-1]
    ax.barh(y, fi["importance"].values, color="steelblue")
    ax.set_yticks(y)
    ax.set_yticklabels(fi["feature"].values, fontsize=9)
    ax.set_xlabel("Importance (Gini)")
    ax.set_title("Top 20 features (E4: all features)", fontsize=12)
    plt.tight_layout()
    out = RESULTS / "fig_feature_importance.png"
    plt.savefig(out, dpi=120, bbox_inches="tight")
    plt.close()
    log(f"  saved {out}")


def fig_ablation():
    log("Figure: ablation comparison...")
    with open(DERIVED / "metrics.json") as f:
        metrics = json.load(f)

    experiments = ["E0_baseline", "E1_DEM_only", "E2_S2_only",
                   "E3_S1_only", "E4_all_features"]
    labels = ["E0\n(baseline)", "E1\nDEM only", "E2\nS2 only",
              "E3\nS1 only", "E4\nAll features"]

    f1s = []
    for e in experiments:
        if e == "E0_baseline":
            f1s.append(metrics[e]["f1"])
        else:
            f1s.append(metrics[e]["cv"]["pooled"]["f1"])

    fig, ax = plt.subplots(figsize=(9, 5), dpi=120)
    bars = ax.bar(labels, f1s, color=["gray", "steelblue", "orange",
                                       "green", "purple"])
    for bar, v in zip(bars, f1s):
        ax.text(bar.get_x() + bar.get_width() / 2, v + 0.01,
                f"{v:.3f}", ha="center", fontsize=10)
    ax.set_ylabel("F1-score")
    ax.set_title("Ablation: Random Forest performance across feature sets",
                 fontsize=12)
    ax.set_ylim(0, max(f1s) * 1.2)
    ax.axhline(f1s[0], ls="--", color="gray", alpha=0.5,
               label="E0 baseline")
    ax.legend()
    plt.tight_layout()
    out = RESULTS / "fig_ablation_comparison.png"
    plt.savefig(out, dpi=120, bbox_inches="tight")
    plt.close()
    log(f"  saved {out}")


def fig_probability_distribution():
    log("Figure: probability distribution...")
    det = gpd.read_file(DERIVED / "detected_lineaments.geojson")

    fig, ax = plt.subplots(figsize=(9, 5), dpi=120)
    ax.hist(det["probability"], bins=30, color="steelblue",
            edgecolor="white", alpha=0.85)
    ax.axvline(0.5, color="red", ls="--", label="Threshold = 0.50")
    ax.set_xlabel("Predicted probability")
    ax.set_ylabel("Count")
    ax.set_title(f"Probability distribution of {len(det)} detected lineaments")
    ax.legend()
    plt.tight_layout()
    out = RESULTS / "fig_probability_distribution.png"
    plt.savefig(out, dpi=120, bbox_inches="tight")
    plt.close()
    log(f"  saved {out}")


def main():
    RESULTS.mkdir(parents=True, exist_ok=True)

    fig_detected_map()
    fig_rose()
    fig_feature_importance()
    fig_ablation()
    fig_probability_distribution()

    log("\nAll figures saved to results/")
    log("\nDone.")


if __name__ == "__main__":
    main()