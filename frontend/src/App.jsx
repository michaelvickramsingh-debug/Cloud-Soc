import { useState } from "react";
import Sidebar from "./components/layout/Sidebar";
import Home from "./pages/Home";
import WhyCloud from "./pages/WhyCloud";
import BestPractice from "./pages/BestPractice";
import Alerts from "./pages/Alerts";
import Logs from "./pages/Logs";

export default function App() {
  const [page, setPage] = useState("home");
  const [bpId, setBpId] = useState(1);

  const navigate = (p, id = 1) => {
    setPage(p);
    if (id) setBpId(id);
  };

  const renderPage = () => {
    switch (page) {
      case "home": return <Home navigate={navigate} />;
      case "why-cloud": return <WhyCloud />;
      case "best-practice": return <BestPractice id={bpId} />;
      case "alerts": return <Alerts />;
      case "logs": return <Logs />;
      default: return <Home navigate={navigate} />;
    }
  };

  return (
    <div style={{ display: "flex", minHeight: "100vh", background: "#0a0e1a", color: "#e2e8f0", fontFamily: "'Inter', sans-serif" }}>
      <Sidebar page={page} bpId={bpId} navigate={navigate} />
      <main style={{ flex: 1, overflowY: "auto", padding: "32px" }}>
        {renderPage()}
      </main>
    </div>
  );
}
