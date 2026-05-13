import { useEffect, useState } from "react";

export default function Dashboard() {
  const [services, setServices] = useState([]);
  const [stats, setStats] = useState(null);

  useEffect(() => {
    loadDashboard();
  }, []);

  async function loadDashboard() {
    const list = [
      { name: "Auth", url: "/auth/health", port: "8001" },
      { name: "Product", url: "/products-svc/health", port: "8002" },
      { name: "Order", url: "/orders-svc/health", port: "8003" },
      { name: "User", url: "/users-svc/health", port: "8004" },
      { name: "Chat", url: "/chat-svc/health", port: "8005" },
    ];

    const results = await Promise.all(
      list.map(async (s) => {
        try {
          const r = await fetch(s.url);
          const data = await r.json();
          return { ...s, ok: r.ok && data.status === "ok" };
        } catch {
          return { ...s, ok: false };
        }
      })
    );

    setServices(results);

    try {
      const [p, o] = await Promise.all([
        fetch("/products-svc/products"),
        fetch("/orders-svc/orders"),
      ]);

      const pd = await p.json();
      const od = await o.json();

      setStats({
        products: pd.products?.length || 0,
        orders: od.orders?.length || 0,
      });
    } catch {
      setStats(null);
    }
  }

  return (
    <div>
      <h2>System Dashboard</h2>

      <div className="grid">
        {services.map((s) => (
          <div className="card" key={s.name}>
            <h3>{s.name}</h3>
            <p>Port: {s.port}</p>
            <p style={{ color: s.ok ? "green" : "red" }}>
              {s.ok ? "Healthy" : "Down"}
            </p>
          </div>
        ))}
      </div>

      <div className="card" style={{ marginTop: 20 }}>
        <h3>Quick Stats</h3>
        {stats ? (
          <>
            <p>Products: {stats.products}</p>
            <p>Orders: {stats.orders}</p>
          </>
        ) : (
          <p>Loading...</p>
        )}
      </div>
    </div>
  );
}