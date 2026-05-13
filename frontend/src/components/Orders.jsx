import { useEffect, useState } from "react";

export default function Orders() {
  const [orders, setOrders] = useState([]);

  async function loadOrders() {
    const r = await fetch("/orders-svc/orders");
    const data = await r.json();
    setOrders(data.orders || []);
  }

  async function createOrder() {
    await fetch("/orders-svc/orders", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_id: 1,
        product_id: 1,
        quantity: 1,
      }),
    });

    loadOrders();
  }

  useEffect(() => {
    loadOrders();
  }, []);

  return (
    <div>
      <h2>Orders</h2>

      <button onClick={createOrder}>Create Order</button>

      <ul>
        {orders.map((o) => (
          <li key={o.id}>
            Order #{o.id} - {o.status}
          </li>
        ))}
      </ul>
    </div>
  );
}