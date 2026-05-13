import { useEffect, useState } from "react";

export default function Products() {
  const [products, setProducts] = useState([]);

  useEffect(() => {
    loadProducts();
  }, []);

  async function loadProducts() {
    const r = await fetch("/products-svc/products");
    const data = await r.json();
    setProducts(data.products || []);
  }

  return (
    <div>
      <h2>Products</h2>

      <button onClick={loadProducts}>Refresh</button>

      <div className="grid">
        {products.map((p) => (
          <div className="card" key={p.id}>
            <h3>{p.name}</h3>
            <p>${p.price}</p>
            <p>Stock: {p.stock}</p>
          </div>
        ))}
      </div>
    </div>
  );
}