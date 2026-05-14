import { useEffect, useState } from "react";

export default function Orders() {
  const [orders, setOrders] = useState([]);
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  // Order form state
  const [userId, setUserId] = useState(1);
  const [productId, setProductId] = useState("");
  const [quantity, setQuantity] = useState(1);

  useEffect(() => {
    loadOrders();
    loadProducts();
  }, []);

  async function loadProducts() {
    try {
      const r = await fetch("/products-svc/products");
      const data = await r.json();
      setProducts(data.products || []);
      if (data.products?.length > 0) {
        setProductId(data.products[0].id);
      }
    } catch {
      // product service may be down, that's ok
    }
  }

  async function loadOrders() {
    try {
      const r = await fetch("/orders-svc/orders");
      const data = await r.json();
      setOrders(data.orders || []);
    } catch {
      setError("Could not reach order service");
    }
  }

  async function createOrder() {
    setError("");
    setSuccess("");
    if (!productId) {
      setError("Select a product first");
      return;
    }
    setLoading(true);
    try {
      const r = await fetch("/orders-svc/orders", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: parseInt(userId),
          product_id: parseInt(productId),
          quantity: parseInt(quantity),
        }),
      });
      const data = await r.json();
      if (r.ok) {
        setSuccess(`Order #${data.order_id} created! Total: $${data.total_price}`);
        loadOrders();
      } else {
        setError(data.detail || "Failed to create order");
      }
    } catch {
      setError("Could not reach order service");
    } finally {
      setLoading(false);
    }
  }

  function statusColor(status) {
    if (status === "completed") return "var(--green)";
    if (status === "cancelled") return "var(--red)";
    return "var(--yellow)";
  }

  return (
    <div>
      <h2>Orders</h2>

      {/* Create order form */}
      <div className="card" style={{ maxWidth: 420, marginBottom: 24 }}>
        <h3>Create Order</h3>

        <label style={{ display: "block", marginBottom: 4, fontSize: 13, color: "var(--text-muted)" }}>
          User ID
        </label>
        <input
          type="number"
          value={userId}
          min={1}
          onChange={(e) => setUserId(e.target.value)}
        />

        <label style={{ display: "block", marginBottom: 4, fontSize: 13, color: "var(--text-muted)" }}>
          Product
        </label>
        {products.length > 0 ? (
          <select
            value={productId}
            onChange={(e) => setProductId(e.target.value)}
            style={{
              display: "block",
              width: "100%",
              maxWidth: 320,
              padding: "9px 13px",
              marginBottom: 10,
              background: "var(--surface2)",
              border: "1px solid var(--border)",
              borderRadius: 7,
              color: "var(--text)",
              fontSize: 14,
            }}
          >
            {products.map((p) => (
              <option key={p.id} value={p.id}>
                #{p.id} — {p.name} (${p.price})
              </option>
            ))}
          </select>
        ) : (
          <input
            type="number"
            placeholder="Product ID"
            value={productId}
            min={1}
            onChange={(e) => setProductId(e.target.value)}
          />
        )}

        <label style={{ display: "block", marginBottom: 4, fontSize: 13, color: "var(--text-muted)" }}>
          Quantity
        </label>
        <input
          type="number"
          value={quantity}
          min={1}
          onChange={(e) => setQuantity(e.target.value)}
        />

        {error && <p style={{ color: "var(--red)", marginBottom: 8 }}>{error}</p>}
        {success && <p style={{ color: "var(--green)", marginBottom: 8 }}>{success}</p>}

        <button onClick={createOrder} disabled={loading}>
          {loading ? "Creating..." : "Create Order"}
        </button>
        <button onClick={loadOrders} style={{ background: "var(--surface2)", border: "1px solid var(--border)", color: "var(--text)" }}>
          Refresh
        </button>
      </div>

      {/* Orders list */}
      <h3>All Orders ({orders.length})</h3>
      {orders.length === 0 ? (
        <p>No orders yet.</p>
      ) : (
        <ul>
          {orders.map((o) => (
            <li key={o.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span>
                <strong>Order #{o.id}</strong> — User {o.user_id}, Product {o.product_id}, Qty {o.quantity}
                {o.total_price != null && <> — <strong>${parseFloat(o.total_price).toFixed(2)}</strong></>}
              </span>
              <span style={{ color: statusColor(o.status), fontWeight: 600, fontSize: 13 }}>
                {o.status}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
