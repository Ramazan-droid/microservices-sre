import { useState } from "react";
import Header from "./components/Header";
import Dashboard from "./components/Dashboard";
import Products from "./components/Products";
import Orders from "./components/Orders";
import Chat from "./components/Chat";
import Auth from "./components/Auth";
import Incident from "./components/Incident";

export default function App() {
  const [page, setPage] = useState("dashboard");

  const renderPage = () => {
    switch (page) {
      case "dashboard": return <Dashboard />;
      case "products": return <Products />;
      case "orders": return <Orders />;
      case "chat": return <Chat />;
      case "auth": return <Auth />;
      case "incident": return <Incident />;
      default: return <Dashboard />;
    }
  };

  return (
    <>
      <Header page={page} setPage={setPage} />
      <div className="container">{renderPage()}</div>
    </>
  );
}