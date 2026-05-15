export default function Header({ page, setPage }) {
  const items = ["dashboard", "products", "orders","reviews", "chat", "auth", "incident"];

  return (
    <div className="header">
      <div className="logo">🚀 MicroShop</div>

      <div className="nav">
        {items.map((item) => (
          <button
            key={item}
            className={page === item ? "active" : ""}
            onClick={() => setPage(item)}
          >
            {item.toUpperCase()}
          </button>
        ))}
      </div>
    </div>
  );
}