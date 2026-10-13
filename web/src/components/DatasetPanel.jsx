export default function DatasetPanel({ dataset }) {
  if (!dataset) {
    return (
      <div className="card">
        <div className="card-title">Dataset</div>
        <div className="skeleton-line" />
        <div className="skeleton-line short" />
        <div className="skeleton-line short" />
      </div>
    );
  }

  const rows = [
    ["Study area", "Abraka, Delta State"],
    ["CRS",        dataset.crs],
    ["Resolution", `${dataset.resolution_m} m`],
    ["Grid",       `${dataset.grid_size[0]} × ${dataset.grid_size[1]}`],
    ["Layers",     dataset.layers.length],
    ["Sentinel-1", `${dataset.sentinel1_scenes} scenes`],
    ["Sentinel-2", `${dataset.sentinel2_scenes} scenes`],
    ["Period",     `${dataset.date_range.start} → ${dataset.date_range.end}`],
  ];

  return (
    <div className="card">
      <div className="card-title">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <ellipse cx="12" cy="5" rx="9" ry="3" />
          <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3" />
          <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" />
        </svg>
        Dataset
      </div>
      <dl className="kv-list">
        {rows.map(([k, v]) => (
          <div key={k} className="kv-row">
            <dt>{k}</dt>
            <dd>{v}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}