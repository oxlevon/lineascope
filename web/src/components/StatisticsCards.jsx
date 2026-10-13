const KPIS = [
  { key: "count",                 label: "Lineaments",        unit: "",       format: (v) => v.toLocaleString() },
  { key: "total_length_km",       label: "Total length",      unit: "km",     format: (v) => v.toFixed(1) },
  { key: "mean_length_m",         label: "Mean length",       unit: "m",      format: (v) => v.toFixed(0) },
  { key: "density_km_per_km2",    label: "Density",           unit: "km/km²", format: (v) => v.toFixed(3) },
  { key: "dominant_azimuth_deg",  label: "Primary azimuth",   unit: "°",      format: (v) => v.toFixed(0) },
  { key: "secondary_azimuth_deg", label: "Secondary azimuth", unit: "°",      format: (v) => v != null ? v.toFixed(0) : "—" },
];

export default function StatisticsCards({ stats }) {
  return (
    <div className="kpi-grid">
      {KPIS.map((k) => (
        <div key={k.key} className="kpi">
          <div className="kpi-label">{k.label}</div>
          <div className="kpi-value">
            {k.format(stats[k.key])}
            {stats[k.key] != null && <span className="kpi-unit">{k.unit}</span>}
          </div>
        </div>
      ))}
    </div>
  );
}