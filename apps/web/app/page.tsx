import Link from "next/link";

export default function Home() {
  return (
    <main className="marketing-page">
      <nav className="marketing-nav">
        <div className="marketing-brand"><span className="marketing-symbol" aria-hidden="true"><i /><i /><i /><i /></span><strong>Opportunity<br />Hunter<span>.</span></strong></div>
        <div className="marketing-nav-actions"><Link href="/demo">Explore the demo</Link><Link className="nav-workspace-link" href="/login?next=/workspace">Sign in / Create account <span>↗</span></Link></div>
      </nav>
      <section className="marketing-hero">
        <div>
          <span className="eyebrow"><span className="eyebrow-line" /> B2B intelligence, evidence first</span>
          <h1>See where your<br /><em>best work</em> is needed.</h1>
          <p>Turn a market and a service into a shortlist of evidence-backed business opportunities — clear problems, practical offers, and a better first conversation.</p>
          <div className="marketing-cta"><Link className="marketing-primary" href="/demo">Try the interactive demo <span>↗</span></Link><span>No signup. No paid search. No credits used.</span></div>
        </div>
        <div className="marketing-map" aria-label="Example opportunity analysis">
          <div className="map-grid" /><span className="map-label map-label-top">Market signal</span><span className="map-label map-label-bottom">Qualified opportunity</span><i className="map-point map-point-one" /><i className="map-point map-point-two" /><i className="map-point map-point-three" /><i className="map-point map-point-main" />
          <div className="map-card"><span>Opportunity score</span><strong>87<span>/100</span></strong><p>Evidence, fit, and urgency aligned.</p></div>
        </div>
      </section>
      <section className="marketing-proof">
        <article><span>01</span><h2>Search with a point of view.</h2><p>Choose a market, category, and the services you actually sell.</p></article>
        <article><span>02</span><h2>Follow the evidence.</h2><p>Separate public facts, observations, and recommendations.</p></article>
        <article><span>03</span><h2>Make a useful offer.</h2><p>Rank the opportunities worth a human conversation.</p></article>
      </section>
      <section className="marketing-footer"><span>AI Opportunity Hunter / private operator platform</span><Link href="/demo">Open demo ↗</Link></section>
    </main>
  );
}
