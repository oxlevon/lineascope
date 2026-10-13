const CONFIGS = [
  { key: "E0_baseline",        label: "E0 — Baseline" },
  { key: "E1_DEM_only",        label: "E1 — DEM only" },
  { key: "E2_S2_only",         label: "E2 — Sentinel-2" },
  { key: "E3_S1_only",         label: "E3 — Sentinel-1" },
  { key: "E4_all_features",    label: "E4 — All features" },
];

export default function MetricsPanel({ metrics }) {
  if (!metrics) {
    return (
      <div className="card">
        <div className="card-title">Model Metrics</div>
        <div className="skeleton-line" />
        <div className="skeleton-line" />
      </div>
    );
  }

  const best = metrics.best_experiment;

  return (
    <div className="card">
      <div className="card-title">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M3 3v18h18" strokeLinecap="round" />
          <path d="M7 15l4-4 4 4 4-6" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
        Model Metrics (5-fold spatial CV)
      </div>
      <table className="metrics-table">
        <thead>
          <tr>
            <th>Config</th>
            <th className="num">P</th>
            <th className="num">R</th>
            <th className="num">F1</th>
          </tr>
        </thead>
        <tbody>
          {CONFIGS.map((c) => {
            const m = metrics[c.key];
            const pooled = c.key === "E0_baseline" ? m : m?.pooled;
            const isBest = best === c.key;
            return (
              <tr key={c.key} className={isBest ? "row-best" : ""}>
                <td>{c.label}{isBest && <span className="best-tag">BEST</span>}</td>
                <td className="num">{pooled?.precision?.toFixed(2) ?? "—"}</td>
                <td className="num">{pooled?.recall?.toFixed(2) ?? "—"}</td>
                <td className="num"><b>{pooled?.f1?.toFixed(2) ?? "—"}</b></td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}