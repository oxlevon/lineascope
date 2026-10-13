import {
  ResponsiveContainer, RadarChart, PolarGrid, PolarAngleAxis,
  PolarRadiusAxis, Radar,
} from "recharts";

export default function RoseChart({ stats }) {
  const data = stats.azimuth_histogram.map((v, i) => ({
    azimuth: `${Math.round(stats.azimuth_histogram_bins[i])}°`,
    count: v,
  }));
  const max = Math.max(...stats.azimuth_histogram);

  return (
    <div className="card chart-card">
      <div className="card-title">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="12" cy="12" r="9" />
          <path d="M12 3v9l6 3" strokeLinecap="round" />
        </svg>
        Azimuth Distribution (rose)
      </div>
      <div className="chart-container">
        <ResponsiveContainer>
          <RadarChart data={data} outerRadius="80%">
            <PolarGrid stroke="#e2e8f0" />
            <PolarAngleAxis dataKey="azimuth" tick={{ fontSize: 10, fill: "#64748b" }} />
            <PolarRadiusAxis angle={90} domain={[0, max]} tick={{ fontSize: 9, fill: "#94a3b8" }} />
            <Radar name="Lineaments" dataKey="count"
                   stroke="#dc2626" fill="#f97316" fillOpacity={0.55} strokeWidth={1.6} />
          </RadarChart>
        </ResponsiveContainer>
      </div>
      <div className="chart-footer">
        Primary <b>{stats.dominant_azimuth_deg.toFixed(0)}°</b>
        {" · "}Secondary <b>{stats.secondary_azimuth_deg?.toFixed(0) ?? "—"}°</b>
        {" · "}<span className="muted">{stats.count} lineaments</span>
      </div>
    </div>
  );
}