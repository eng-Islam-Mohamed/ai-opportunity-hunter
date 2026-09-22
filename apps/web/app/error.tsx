"use client";

export default function ErrorPage({ reset }: { reset: () => void }) {
  return (
    <main className="loading-screen">
      <p>Something interrupted the dashboard.</p>
      <button className="primary-button" onClick={reset}>Try again</button>
    </main>
  );
}
