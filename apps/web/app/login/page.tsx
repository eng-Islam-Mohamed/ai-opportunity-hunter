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
    try {
    const response = await fetch(`/api/auth/${mode}`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    setBusy(false);
    if (!response.ok) {
      const payload = await response.json().catch(() => null);
      setError(typeof payload?.detail === "string" ? payload.detail : "Check your email and use a password of at least 10 characters.");
      return;
    }
    const next = searchParams.get("next");
    router.replace(next?.startsWith("/") && !next.startsWith("//") && next !== "/" ? next : "/workspace");
    router.refresh();
    } catch { setError("Could not connect. Please try again."); }
    finally { setBusy(false); }
  }

  return (
    <main className="login-page">
      <section className="login-card">
        <div className="login-symbol" aria-hidden="true"><span /><span /><span /><span /></div>
        <span className="eyebrow"><span className="eyebrow-line" /> Your private workspace</span>
        <h1>Opportunity<br /><em>Hunter.</em></h1>
        <p>Create an account to save private campaigns. Every account gets 10 research runs per day, resetting at midnight UTC.</p>
        <div className="auth-tabs"><button type="button" className={mode === "login" ? "active" : ""} onClick={() => setMode("login")}>Sign in</button><button type="button" className={mode === "register" ? "active" : ""} onClick={() => setMode("register")}>Create account</button></div>
        <form onSubmit={signIn}>
          <label htmlFor="account-email">Email address</label>
          <input id="account-email" type="email" autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} required />
          <label htmlFor="operator-password">Password</label>
          <input id="operator-password" type="password" minLength={10} maxLength={128} autoComplete={mode === "register" ? "new-password" : "current-password"} value={password} onChange={(event) => setPassword(event.target.value)} required />
          <small>At least 10 characters.</small>
          {error && <p className="login-error" role="alert">{error}</p>}
          <button className="primary-button" disabled={busy} type="submit">{busy ? "Checking…" : mode === "login" ? "Sign in" : "Create account"} <span aria-hidden="true">↗</span></button>
        </form>
      </section>
    </main>
  );
}
