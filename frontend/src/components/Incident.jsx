import { useState } from "react";

export default function Incident() {
  const [result, setResult] = useState("");
  const [recovery, setRecovery] = useState("");

  async function triggerIncident() {
    setResult("Testing Order Service...");

    try {
      const r = await fetch("/orders-svc/orders", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: 1,
          product_id: 1,
          quantity: 1,
        }),
      });

      if (r.ok) {
        setResult("System healthy. No incident detected.");
      } else {
        setResult("INCIDENT: Order service failure detected.");
      }
    } catch (e) {
      setResult("INCIDENT: Service unreachable");
    }
  }

  async function verifyRecovery() {
    try {
      const r = await fetch("/orders-svc/health");
      const data = await r.json();

      if (r.ok && data.status === "ok") {
        setRecovery("Order Service fully recovered ✅");
      } else {
        setRecovery("Still degraded ⚠️");
      }
    } catch {
      setRecovery("Service unreachable ❌");
    }
  }

  return (
    <div>
      <h2>Incident Simulation</h2>

      <button onClick={triggerIncident}>Trigger Incident</button>
      <p>{result}</p>

      <h3>Recovery Check</h3>
      <button onClick={verifyRecovery}>Verify Recovery</button>
      <p>{recovery}</p>

      <div style={{ marginTop: "20px", background: "#1e293b", padding: "10px" }}>
        <h4>Root Cause Example</h4>
        <p>DATABASE_URL misconfigured → wrong hostname</p>
      </div>
    </div>
  );
}