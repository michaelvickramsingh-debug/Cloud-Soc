const NAV = [
  { label: "Overview", page: "home", icon: "🏠" },
  { label: "Why Cloud is Targeted", page: "why-cloud", icon: "☁️" },
  { label: "─── 5 BEST PRACTICES ───", disabled: true },
  { label: "BP1 · Threat Intelligence", page: "best-practice", id: 1, icon: "🧠" },
  { label: "BP2 · Control Plane Context", page: "best-practice", id: 2, icon: "🔗" },
  { label: "BP3 · Runtime Protection", page: "best-practice", id: 3, icon: "🛡️" },
  { label: "BP4 · Cloud Expertise", page: "best-practice", id: 4, icon: "👥" },
  { label: "BP5 · Automate Response", page: "best-practice", id: 5, icon: "⚙️" },
  { label: "─────────────────────", disabled: true },
  { label: "Live Alerts", page: "alerts", icon: "🚨" },
  { label: "Cloud Logs", page: "logs", icon: "📜" },
];

export default function Sidebar({ page, bpId, navigate }) {
  return (
    <aside style={{
      width: 260,
      background: "#0d1220",
      borderRight: "1px solid #1e2d45",
      padding: "24px 0",
      flexShrink: 0,
      position: "sticky",
      top: 0,
      height: "100vh",
      overflowY: "auto",
    }}>
      {/* Logo */}
      <div style={{ padding: "0 20px 24px", borderBottom: "1px solid #1e2d45" }}>
        <div style={{ fontSize: 11, color: "#4a90e2", letterSpacing: 3, marginBottom: 4 }}>CROWDSTRIKE</div>
        <div style={{ fontSize: 15, fontWeight: 700, color: "#e2e8f0", lineHeight: 1.3 }}>Cloud Detection<br />& Response</div>
        <div style={{ fontSize: 10, color: "#64748b", marginTop: 4 }}>Survival Guide for the SOC</div>
      </div>

      {/* Nav */}
      <nav style={{ padding: "16px 0" }}>
        {NAV.map((item, i) => {
          if (item.disabled) return (
            <div key={i} style={{ padding: "8px 20px", fontSize: 9, color: "#334155", letterSpacing: 1 }}>{item.label}</div>
          );
          const isActive = page === item.page && (item.id === undefined || item.id === bpId);
          return (
            <button key={i} onClick={() => navigate(item.page, item.id)} style={{
              display: "flex", alignItems: "center", gap: 10,
              width: "100%", padding: "10px 20px",
              background: isActive ? "#1a2744" : "transparent",
              borderLeft: isActive ? "3px solid #4a90e2" : "3px solid transparent",
              border: "none", color: isActive ? "#e2e8f0" : "#94a3b8",
              fontSize: 13, cursor: "pointer", textAlign: "left",
              transition: "all 0.15s",
            }}>
              <span>{item.icon}</span>
              <span>{item.label}</span>
            </button>
          );
        })}
      </nav>

      {/* Footer */}
      <div style={{ padding: "16px 20px", borderTop: "1px solid #1e2d45", marginTop: "auto", position: "absolute", bottom: 0, left: 0, right: 0 }}>
        <div style={{ fontSize: 10, color: "#334155" }}>Based on CrowdStrike Whitepaper</div>
        <div style={{ fontSize: 10, color: "#334155" }}>© 2025 CloudGuard Project</div>
      </div>
    </aside>
  );
}
