import { downloadUrl } from "../api";

const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

async function downloadMetricsJson() {
  const res = await fetch(`${API_URL}/api/metrics`);
  if (!res.ok) return;
  const data = await res.json();
  const blob = new Blob([JSON.stringify(data, null, 2)], {
    type: "application/json",
  });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `lineascope_metrics_${Date.now()}.json`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

export default function DownloadPanel({ threshold, minLength, enabled }) {
  const disabled = !enabled;

  return (
    <div className="card">
      <div className="card-title">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" strokeLinecap="round" />
          <path d="M7 10l5 5 5-5M12 15V3" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
        Export Results
      </div>

      {/* ================= Data ================= */}
      <div className="dl-section-label">Data</div>

      <a
        className={`btn-download ${disabled ? "disabled" : ""}`}
        href={disabled ? undefined : downloadUrl(threshold, minLength, "geojson")}
        download="lineascope_detections.geojson"
        onClick={(e) => disabled && e.preventDefault()}
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
             strokeWidth="2" style={{ width: 14, height: 14 }}>
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" strokeLinejoin="round" />
          <path d="M14 2v6h6" strokeLinejoin="round" />
        </svg>
        <span>Detections</span>
        <span className="btn-download-sub">GeoJSON</span>
      </a>

      <a
        className={`btn-download ${disabled ? "disabled" : ""}`}
        href={disabled ? undefined : downloadUrl(threshold, minLength, "csv")}
        download="lineascope_detections.csv"
        onClick={(e) => disabled && e.preventDefault()}
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
             strokeWidth="2" style={{ width: 14, height: 14 }}>
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" strokeLinejoin="round" />
          <path d="M14 2v6h6" strokeLinejoin="round" />
        </svg>
        <span>Attributes</span>
        <span className="btn-download-sub">CSV</span>
      </a>

      <button
        className={`btn-download ${disabled ? "disabled" : ""}`}
        onClick={() => !disabled && downloadMetricsJson()}
        disabled={disabled}
        type="button"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
             strokeWidth="2" style={{ width: 14, height: 14 }}>
          <path d="M3 3v18h18" strokeLinecap="round" />
          <path d="M7 15l4-4 4 4 4-6" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
        <span>Model metrics</span>
        <span className="btn-download-sub">JSON</span>
      </button>

      {/* ================= Figures ================= */}
      <div className="dl-section-label" style={{ marginTop: 10 }}>
        Figures
      </div>

      <a
        className="btn-download"
        href="/results/fig_detected_map.png"
        download="fig_detected_map.png"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
             strokeWidth="2" style={{ width: 14, height: 14 }}>
          <rect x="3" y="3" width="18" height="18" rx="2" strokeLinejoin="round" />
          <circle cx="8.5" cy="8.5" r="1.5" />
          <path d="M21 15l-5-5L5 21" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
        <span>Detected map</span>
        <span className="btn-download-sub">PNG</span>
      </a>

      <a
        className="btn-download"
        href="/results/fig_rose_comparison.png"
        download="fig_rose_comparison.png"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
             strokeWidth="2" style={{ width: 14, height: 14 }}>
          <circle cx="12" cy="12" r="9" />
          <path d="M12 3v9l6 3" strokeLinecap="round" />
        </svg>
        <span>Rose diagrams</span>
        <span className="btn-download-sub">PNG</span>
      </a>

      <a
        className="btn-download"
        href="/results/fig_feature_importance.png"
        download="fig_feature_importance.png"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
             strokeWidth="2" style={{ width: 14, height: 14 }}>
          <path d="M3 3v18h18" strokeLinecap="round" />
          <rect x="6" y="9" width="3" height="9" />
          <rect x="12" y="6" width="3" height="12" />
          <rect x="18" y="12" width="3" height="6" />
        </svg>
        <span>Feature importance</span>
        <span className="btn-download-sub">PNG</span>
      </a>

      <a
        className="btn-download"
        href="/results/fig_ablation_comparison.png"
        download="fig_ablation_comparison.png"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
             strokeWidth="2" style={{ width: 14, height: 14 }}>
          <rect x="3" y="3" width="18" height="18" rx="2" strokeLinejoin="round" />
          <path d="M8 17V8M12 17V5M16 17v-6" strokeLinecap="round" />
        </svg>
        <span>Ablation</span>
        <span className="btn-download-sub">PNG</span>
      </a>

      <a
        className="btn-download"
        href="/results/fig_probability_distribution.png"
        download="fig_probability_distribution.png"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
             strokeWidth="2" style={{ width: 14, height: 14 }}>
          <path d="M3 20h18M5 20v-8M9 20v-14M13 20v-6M17 20v-10M21 20v-4"
                strokeLinecap="round" />
        </svg>
        <span>Probability dist.</span>
        <span className="btn-download-sub">PNG</span>
      </a>

      {disabled && (
        <p className="hint">Run detection first to enable data exports.</p>
      )}
    </div>
  );
}