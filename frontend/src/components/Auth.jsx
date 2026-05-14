import { useState } from "react";

export default function Auth() {
  const [token, setToken] = useState(null);
  const [loginUser, setLoginUser] = useState("admin");
  const [loginPass, setLoginPass] = useState("password123");
  const [loginError, setLoginError] = useState("");

  const [regUser, setRegUser] = useState("");
  const [regEmail, setRegEmail] = useState("");
  const [regPass, setRegPass] = useState("");
  const [regMsg, setRegMsg] = useState("");
  const [regError, setRegError] = useState("");

  async function login() {
    setLoginError("");
    try {
      const r = await fetch("/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: loginUser, password: loginPass }),
      });
      const data = await r.json();
      if (r.ok) {
        setToken(data.access_token);
      } else {
        setLoginError(data.detail || "Login failed");
      }
    } catch (e) {
      setLoginError("Could not reach auth service");
    }
  }

  async function logout() {
    setToken(null);
  }

  async function register() {
    setRegMsg("");
    setRegError("");
    if (!regUser || !regEmail || !regPass) {
      setRegError("All fields are required");
      return;
    }
    try {
      const r = await fetch("/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: regUser, email: regEmail, password: regPass }),
      });
      const data = await r.json();
      if (r.ok) {
        setRegMsg(`Registered successfully! User ID: ${data.user_id}`);
        setRegUser("");
        setRegEmail("");
        setRegPass("");
      } else {
        setRegError(data.detail || "Registration failed");
      }
    } catch (e) {
      setRegError("Could not reach auth service");
    }
  }

  return (
    <div>
      <h2>Auth</h2>

      <div style={{ display: "flex", gap: "24px", flexWrap: "wrap" }}>

        {/* Login */}
        <div className="auth-section">
          <h3>Login</h3>
          <input
            value={loginUser}
            onChange={(e) => setLoginUser(e.target.value)}
            placeholder="Username"
          />
          <input
            type="password"
            value={loginPass}
            onChange={(e) => setLoginPass(e.target.value)}
            placeholder="Password"
          />
          {loginError && <p style={{ color: "var(--red)", marginBottom: 8 }}>{loginError}</p>}
          {token
            ? <button onClick={logout} style={{ background: "var(--red)" }}>Logout</button>
            : <button onClick={login}>Login</button>
          }

          {token && (
            <div style={{ marginTop: 16 }}>
              <h4>JWT Token</h4>
              <code>{token}</code>
            </div>
          )}
        </div>

        {/* Register */}
        <div className="auth-section">
          <h3>Register</h3>
          <input
            placeholder="Username"
            value={regUser}
            onChange={(e) => setRegUser(e.target.value)}
          />
          <input
            placeholder="Email"
            value={regEmail}
            onChange={(e) => setRegEmail(e.target.value)}
          />
          <input
            type="password"
            placeholder="Password"
            value={regPass}
            onChange={(e) => setRegPass(e.target.value)}
          />
          {regError && <p style={{ color: "var(--red)", marginBottom: 8 }}>{regError}</p>}
          {regMsg && <p style={{ color: "var(--green)", marginBottom: 8 }}>{regMsg}</p>}
          <button onClick={register}>Register</button>
        </div>

      </div>
    </div>
  );
}
