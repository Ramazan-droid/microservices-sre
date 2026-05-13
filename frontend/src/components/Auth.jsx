import { useState } from "react";

export default function Auth() {
  const [token, setToken] = useState(null);

  const [loginUser, setLoginUser] = useState("admin");
  const [loginPass, setLoginPass] = useState("password123");

  const [regUser, setRegUser] = useState("");
  const [regEmail, setRegEmail] = useState("");
  const [regPass, setRegPass] = useState("");

  async function login() {
    try {
      const r = await fetch("/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username: loginUser,
          password: loginPass,
        }),
      });

      const data = await r.json();
      if (r.ok) setToken(data.access_token);
    } catch (e) {
      console.error(e);
    }
  }

  async function register() {
    try {
      await fetch("/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username: regUser,
          email: regEmail,
          password: regPass,
        }),
      });
    } catch (e) {
      console.error(e);
    }
  }

  return (
    <div>
      <h2>Auth</h2>

      <h3>Login</h3>
      <input value={loginUser} onChange={(e) => setLoginUser(e.target.value)} />
      <input type="password" value={loginPass} onChange={(e) => setLoginPass(e.target.value)} />
      <button onClick={login}>Login</button>

      <h3>Register</h3>
      <input placeholder="username" value={regUser} onChange={(e) => setRegUser(e.target.value)} />
      <input placeholder="email" value={regEmail} onChange={(e) => setRegEmail(e.target.value)} />
      <input placeholder="password" value={regPass} onChange={(e) => setRegPass(e.target.value)} />
      <button onClick={register}>Register</button>

      {token && (
        <div style={{ marginTop: "20px" }}>
          <h4>JWT Token</h4>
          <code>{token}</code>
        </div>
      )}
    </div>
  );
}