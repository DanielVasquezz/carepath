import { useEffect, useState } from "react";
import Login from "./Login";
import Dashboard from "./Dashboard";

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem("token");
    setIsAuthenticated(!!token);
    setLoading(false);
  }, []);

  if (loading) return (
    <div style={{ textAlign: "center", padding: 80, fontFamily: "system-ui" }}>
      <p>Loading...</p>
    </div>
  );

  return isAuthenticated
    ? <Dashboard onLogout={() => setIsAuthenticated(false)} />
    : <Login onLogin={() => setIsAuthenticated(true)} />;
}

export default App;