import { useState } from "react";
import Lightbox from "./Lightbox";

const KPI_KEYS = [
  { key: "count",                 label: "Lineaments",      unit: "",       fmt: (v) => v.toLocaleString() },
  { key: "total_length_km",       label: "Total length",    unit: "km",     fmt: (v) => v.toFixed(1) },
  { key: "mean_length_m",         label: "Mean length",     unit: "m",      fmt: (v) => v.toFixed(0) },
  { key: "density_km_per_km2",    label: "Density",         unit: "km/km²", fmt: (v) => v.toFixed(3) },
  { key: "dominant_azimuth_deg",  label: "Primary az.",     unit: "°",      fmt: (v) => v.toFixed(0) },
  { key: "secondary_azimuth_deg", label: "Secondary az.",   unit: "°",      fmt: (v) => v != null ? v.toFixed(0) : "—" },
];

const FIGURES = [
  { file: "fig_rose_comparison.png",          title: "Orientation (rose)" },
  { file: "fig_feature_importance.png",       title: "Feature importance" },
  { file: "fig_ablation_comparison.png",      title: "Ablation (E0–E4)" },
  { file: "fig_probability_distribution.png", title: "Probability distribution" },
  { file: "fig_detected_map.png",             title: "Detected map" },
];

export default function AnalysisPanel({ stats }) {
  const [preview, setPreview] = useState(null);

  return (
    <>
      <aside className="analysis-panel">
        <div className="analysis-section">
          <div className="analysis-heading">
            <span className="analysis-heading-dot" />
            Analysis Results
          </div>
          <div className="kpi-grid-2">
            {KPI_KEYS.map((k) => (
              <div key={k.key} className="kpi-mini">
                <div className="kpi-mini-label">{k.label}</div>
                <div className="kpi-mini-value">
                  {k.fmt(stats[k.key])}
                  {stats[k.key] != null && k.unit && (
                    <span className="kpi-mini-unit">{k.unit}</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        {FIGURES.map((f) => (
          <div key={f.file} className="analysis-section">
            <div className="analysis-heading small">
              <span className="analysis-heading-dot" />
              {f.title}
              <a
                href={`/results/${f.file}`}
                download={f.file}
                title="Download PNG"
                className="figure-dl"
                onClick={(e) => e.stopPropagation()}
              >
                ⬇
              </a>
            </div>
            <button
              type="button"
              className="figure-link"
              onClick={() =>
                setPreview({
                  src: `/results/${f.file}`,
                  alt: f.title,
                })
              }
              title="Click to enlarge"
            >
              <img
                src={`/results/${f.file}`}
                alt={f.title}
                className="analysis-figure"
                onError={(e) => {
                  e.target.style.display = "none";
                  e.target.parentElement.classList.add("figure-missing");
                }}
              />
            </button>
          </div>
        ))}
      </aside>

      {preview && (
        <Lightbox
          src={preview.src}
          alt={preview.alt}
          onClose={() => setPreview(null)}
        />
      )}
    </>
  );
}