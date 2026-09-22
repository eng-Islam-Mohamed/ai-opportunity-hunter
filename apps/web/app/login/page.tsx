"use client";

import { FormEvent, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

export default function LoginPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [mode, setMode] = useState<"login" | "register">("login");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function signIn(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    const response = await fetch(`/api/auth/${mode}`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    setBusy(false);
    if (!response.ok) {
      const payload = await response.json().catch(() => null);
      setError(payload?.detail || "Could not authenticate this account.");
      return;
    }
    router.replace(searchParams.get("next") || "/workspace");
    router.refresh();
  }

  return (
    <main className="login-page">
      <section className="login-card">
        <div className="login-symbol" aria-hidden="true"><span /><span /><span /><span /></div>
        <span className="eyebrow"><span className="eyebrow-line" /> Your private workspace</span>
        <h1>Opportunity<br /><em>Hunter.</em></h1>
        <p>Create an account to save private campaigns. Every account can start five live research runs per day.</p>
        <div className="auth-tabs"><button type="button" className={mode === "login" ? "active" : ""} onClick={() => setMode("login")}>Sign in</button><button type="button" className={mode === "register" ? "active" : ""} onClick={() => setMode("register")}>Create account</button></div>
        <form onSubmit={signIn}>
          <label htmlFor="account-email">Email address</label>
          <input id="account-email" type="email" autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} required />
          <label htmlFor="operator-password">Password</label>
          <input id="operator-password" type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} required />
          {error && <p className="login-error" role="alert">{error}</p>}
          <button className="primary-button" disabled={busy} type="submit">{busy ? "Checking…" : mode === "login" ? "Sign in" : "Create account"} <span aria-hidden="true">↗</span></button>
        </form>
      </section>
    </main>
  );
}
