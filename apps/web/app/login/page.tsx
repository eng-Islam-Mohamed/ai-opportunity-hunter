"use client";

import { FormEvent, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

export default function LoginPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function signIn(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    const response = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ password }),
    });
    setBusy(false);
    if (!response.ok) {
      setError("The password is not correct.");
      return;
    }
    router.replace(searchParams.get("next") || "/");
    router.refresh();
  }

  return (
    <main className="login-page">
      <section className="login-card">
        <div className="login-symbol" aria-hidden="true"><span /><span /><span /><span /></div>
        <span className="eyebrow"><span className="eyebrow-line" /> Private operator access</span>
        <h1>Opportunity<br /><em>Hunter.</em></h1>
        <p>This workspace contains prospecting research and is available only to its operator.</p>
        <form onSubmit={signIn}>
          <label htmlFor="operator-password">Access password</label>
          <input id="operator-password" type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} required />
          {error && <p className="login-error" role="alert">{error}</p>}
          <button className="primary-button" disabled={busy} type="submit">{busy ? "Checking…" : "Enter workspace"} <span aria-hidden="true">↗</span></button>
        </form>
      </section>
    </main>
  );
}
