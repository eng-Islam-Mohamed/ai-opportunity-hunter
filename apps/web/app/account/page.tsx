"use client";

import { FormEvent, useEffect, useState } from "react";

export default function AccountPage() {
  const [account, setAccount] = useState<{email: string; daily_runs_remaining: number} | null>(null);
  const [current, setCurrent] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    fetch("/api/backend/api/v1/auth/me", { cache: "no-store" }).then(async r => {
      if (r.status === 401) { window.location.assign("/login?next=/account"); return; }
      if (!r.ok) throw new Error("Could not load your account.");
      setAccount(await r.json());
    }).catch(e => setMessage(e.message));
  }, []);
  async function logout() {
    await fetch("/api/auth/logout", { method: "POST" });
    window.location.assign("/login");
  }
  async function changePassword(event: FormEvent) {
    event.preventDefault();
    if (password !== confirm) { setMessage("The new passwords do not match."); return; }
    setBusy(true); setMessage("");
    try {
      const r = await fetch("/api/backend/api/v1/auth/change-password", {
        method: "POST", headers: { "content-type": "application/json" },
        body: JSON.stringify({ current_password: current, new_password: password })
      });
      const result = await r.json();
      if (!r.ok) throw new Error(typeof result.detail === "string" ? result.detail : "Could not change password.");
      setCurrent(""); setPassword(""); setConfirm("");
      setMessage("Password changed. Sign in again with your new password. Other sessions are also signed out.");
      await fetch("/api/auth/logout", { method: "POST" });
    } catch (e) { setMessage(e instanceof Error ? e.message : "Please try again."); }
    finally { setBusy(false); }
  }
  return <main className="login-page"><section className="login-card">
    <a href="/workspace">← Back to workspace</a>
    <h1>Your <em>account.</em></h1>
    <p>{account?.email}</p>
    <p>{account ? `${account.daily_runs_remaining} of 10 searches remaining today.` : "Loading allowance…"} Resets at midnight UTC. Each started campaign counts once.</p>
    <form onSubmit={changePassword}>
      <label htmlFor="current">Current password</label>
      <input id="current" type="password" autoComplete="current-password" required maxLength={128} value={current} onChange={e => setCurrent(e.target.value)} />
      <label htmlFor="new">New password</label>
      <input id="new" type="password" autoComplete="new-password" required minLength={10} maxLength={128} value={password} onChange={e => setPassword(e.target.value)} />
      <label htmlFor="confirm">Confirm new password</label>
      <input id="confirm" type="password" autoComplete="new-password" required minLength={10} maxLength={128} value={confirm} onChange={e => setConfirm(e.target.value)} />
      <small>Use at least 10 characters.</small>
      <button className="primary-button" disabled={busy}>{busy ? "Saving…" : "Change password"}</button>
    </form>
    {message && <p role="status">{message}</p>}
    <div className="auth-tabs"><a href="/login">Sign in</a><button onClick={() => void logout()}>Sign out</button></div>
  </section></main>;
}
