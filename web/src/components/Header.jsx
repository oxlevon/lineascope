export default function Header({ health }) {
  return (
    <header className="header">
      <div className="header-left">
        <img
          src="/delsu-logo.jpg"
          alt="Delta State University"
          className="header-logo-img"
          onError={(e) => {
            // Fallback if logo missing
            e.target.style.display = "none";
          }}
        />
        <div className="header-institution">
          <div className="header-university">Delta State University, Abraka</div>
          <div className="header-faculty">Faculty of Computing</div>
        </div>
        <div className="header-divider" />
        <div className="header-brand">
          <h1>LineaScope</h1>
          <span>AI-Based Geological Lineament Detection System</span>
        </div>
      </div>

      <div className="header-status">
        {health ? (
          <>
            <span className="status-pill status-ok">
              <span className="status-dot" /> Online
            </span>
            <span className="status-info">Model <b>{health.model_version}</b></span>
            <span className="status-info">{health.n_candidates.toLocaleString()} candidates</span>
          </>
        ) : (
          <span className="status-pill status-wait">
            <span className="status-dot" /> Connecting…
          </span>
        )}
      </div>
    </header>
  );
}