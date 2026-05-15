import { useEffect, useState } from "react";

const STARS = [1, 2, 3, 4, 5];

function StarRating({ value, onChange }) {
  return (
    <div style={{ display: "flex", gap: 4, marginBottom: 10 }}>
      {STARS.map((s) => (
        <span
          key={s}
          onClick={() => onChange && onChange(s)}
          style={{
            fontSize: 24,
            cursor: onChange ? "pointer" : "default",
            color: s <= value ? "#f59e0b" : "var(--border)",
            transition: "color 0.1s",
          }}
        >
          ★
        </span>
      ))}
    </div>
  );
}

export default function Reviews() {
  const [reviews, setReviews] = useState([]);
  const [products, setProducts] = useState([]);
  const [filterProduct, setFilterProduct] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  // Form state
  const [productId, setProductId] = useState("");
  const [userId, setUserId] = useState(1);
  const [rating, setRating] = useState(5);
  const [comment, setComment] = useState("");

  useEffect(() => {
    loadProducts();
    loadReviews();
  }, []);

  async function loadProducts() {
    try {
      const r = await fetch("/products-svc/products");
      const data = await r.json();
      const list = data.products || [];
      setProducts(list);
      if (list.length > 0) setProductId(list[0].id);
    } catch {
      // product service may be down
    }
  }

  async function loadReviews(pid) {
    try {
      const url = pid ? `/reviews-svc/reviews?product_id=${pid}` : "/reviews-svc/reviews";
      const r = await fetch(url);
      const data = await r.json();
      setReviews(data.reviews || []);
    } catch {
      setError("Could not reach review service");
    }
  }

  function handleFilterChange(e) {
    const val = e.target.value;
    setFilterProduct(val);
    loadReviews(val || undefined);
  }

  async function submitReview() {
    setError("");
    setSuccess("");
    if (!productId) { setError("Select a product"); return; }
    setLoading(true);
    try {
      const r = await fetch("/reviews-svc/reviews", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          product_id: parseInt(productId),
          user_id: parseInt(userId),
          rating,
          comment,
        }),
      });
      const data = await r.json();
      if (r.ok) {
        setSuccess(`Review #${data.review_id} submitted!`);
        setComment("");
        setRating(5);
        loadReviews(filterProduct || undefined);
      } else {
        setError(data.detail || "Failed to submit review");
      }
    } catch {
      setError("Could not reach review service");
    } finally {
      setLoading(false);
    }
  }

  async function deleteReview(id) {
    try {
      await fetch(`/reviews-svc/reviews/${id}`, { method: "DELETE" });
      loadReviews(filterProduct || undefined);
    } catch {
      setError("Could not delete review");
    }
  }

  function productName(id) {
    const p = products.find((p) => p.id === id);
    return p ? p.name : `Product #${id}`;
  }

  function avgRating() {
    if (!reviews.length) return null;
    return (reviews.reduce((s, r) => s + r.rating, 0) / reviews.length).toFixed(1);
  }

  return (
    <div>
      <h2>Reviews</h2>

      <div style={{ display: "flex", gap: 24, flexWrap: "wrap", alignItems: "flex-start" }}>

        {/* Submit form */}
        <div className="card" style={{ minWidth: 280, maxWidth: 360 }}>
          <h3>Write a Review</h3>

          <label style={{ fontSize: 13, color: "var(--text-muted)" }}>Product</label>
          {products.length > 0 ? (
            <select
              value={productId}
              onChange={(e) => setProductId(e.target.value)}
              style={{
                display: "block", width: "100%", padding: "9px 13px",
                marginBottom: 10, background: "var(--surface2)",
                border: "1px solid var(--border)", borderRadius: 7,
                color: "var(--text)", fontSize: 14,
              }}
            >
              {products.map((p) => (
                <option key={p.id} value={p.id}>#{p.id} — {p.name}</option>
              ))}
            </select>
          ) : (
            <input
              type="number" min={1} placeholder="Product ID"
              value={productId} onChange={(e) => setProductId(e.target.value)}
            />
          )}

          <label style={{ fontSize: 13, color: "var(--text-muted)" }}>User ID</label>
          <input
            type="number" min={1} value={userId}
            onChange={(e) => setUserId(e.target.value)}
          />

          <label style={{ fontSize: 13, color: "var(--text-muted)" }}>Rating</label>
          <StarRating value={rating} onChange={setRating} />

          <label style={{ fontSize: 13, color: "var(--text-muted)" }}>Comment</label>
          <textarea
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            placeholder="Write your review..."
            rows={3}
            style={{
              display: "block", width: "100%", maxWidth: "100%",
              padding: "9px 13px", marginBottom: 10,
              background: "var(--surface2)", border: "1px solid var(--border)",
              borderRadius: 7, color: "var(--text)", fontSize: 14,
              resize: "vertical", fontFamily: "inherit",
            }}
          />

          {error && <p style={{ color: "var(--red)", marginBottom: 8 }}>{error}</p>}
          {success && <p style={{ color: "var(--green)", marginBottom: 8 }}>{success}</p>}
          <button onClick={submitReview} disabled={loading}>
            {loading ? "Submitting..." : "Submit Review"}
          </button>
        </div>

        {/* Reviews list */}
        <div style={{ flex: 1, minWidth: 280 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 16, flexWrap: "wrap" }}>
            <h3 style={{ margin: 0 }}>
              All Reviews ({reviews.length})
              {avgRating() && (
                <span style={{ color: "#f59e0b", marginLeft: 10, fontSize: 16 }}>
                  ★ {avgRating()} avg
                </span>
              )}
            </h3>
            <select
              value={filterProduct}
              onChange={handleFilterChange}
              style={{
                padding: "6px 12px", background: "var(--surface2)",
                border: "1px solid var(--border)", borderRadius: 7,
                color: "var(--text)", fontSize: 13,
              }}
            >
              <option value="">All products</option>
              {products.map((p) => (
                <option key={p.id} value={p.id}>#{p.id} — {p.name}</option>
              ))}
            </select>
          </div>

          {reviews.length === 0 ? (
            <p>No reviews yet.</p>
          ) : (
            <ul style={{ listStyle: "none", padding: 0 }}>
              {reviews.map((r) => (
                <li key={r.id} className="card" style={{ marginBottom: 10, textAlign: "left" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                    <div>
                      <strong style={{ fontSize: 14 }}>{productName(r.product_id)}</strong>
                      <span style={{ color: "var(--text-muted)", fontSize: 13, marginLeft: 8 }}>
                        by User #{r.user_id}
                      </span>
                      <StarRating value={r.rating} />
                      {r.comment && <p style={{ marginTop: 4 }}>{r.comment}</p>}
                      <p style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 6 }}>
                        {new Date(r.created_at).toLocaleString()}
                      </p>
                    </div>
                    <button
                      onClick={() => deleteReview(r.id)}
                      style={{
                        background: "transparent", border: "1px solid var(--border)",
                        color: "var(--red)", padding: "4px 10px", fontSize: 12,
                        marginBottom: 0,
                      }}
                    >
                      Delete
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>

      </div>
    </div>
  );
}
