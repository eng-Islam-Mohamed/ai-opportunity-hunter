import type { LeadDetail } from "@/lib/types";

type LeadDrawerProps = { lead: LeadDetail | null; onClose: () => void };

export function LeadDrawer({ lead, onClose }: LeadDrawerProps) {
  if (!lead) return null;
  return (
    <div className="drawer-layer">
      <button className="drawer-backdrop" onClick={onClose} aria-label="Close opportunity brief" />
      <aside className="drawer" role="dialog" aria-modal="true" aria-label={`Opportunity brief for ${lead.company_name}`}>
        <div className="drawer-header"><div><span className="eyebrow">Lead dossier / Evidence file</span><h2>{lead.company_name}</h2><p>{lead.location || "Location unverified"}</p></div><button className="icon-button" onClick={onClose} aria-label="Close brief">×</button></div>
        <div className="brief-score"><span>Opportunity score<br /><small>{lead.band} / confidence {Math.round(lead.confidence * 100)}%</small></span><strong>{Math.round(lead.final_score)}<small>/100</small></strong></div>
        <div className="brief-contact">{lead.phone && <a href={`tel:${lead.phone.replace(/[^+\d]/g, "")}`}>Call {lead.phone} ↗</a>}{lead.website && <a href={lead.website} target="_blank" rel="noopener noreferrer">Open website ↗</a>}{!lead.phone && !lead.website && <span>No verified direct contact yet</span>}</div>
        <section><h3><span>01</span> Observed problem</h3><p>{lead.main_problem || "No evidence-backed problem recorded."}</p></section>
        <section><h3><span>02</span> Recommended offer</h3><p>{lead.recommended_solution || "Awaiting review."}</p>{lead.sales_angle && <p className="sales-angle">{lead.sales_angle}</p>}</section>
        <section><h3><span>03</span> Suggested opening</h3><blockquote>{lead.opening_message || "No opening message has been prepared."}</blockquote></section>
        <section><h3><span>04</span> Evidence trail</h3>{lead.evidence.length === 0 && <p>No source evidence has been recorded.</p>}{lead.evidence.map((item) => <article className="evidence" key={item.id}><span>{Math.round(item.confidence * 100)}%</span><div><p>{item.claim}</p>{item.source_url && <a href={item.source_url} target="_blank" rel="noreferrer">View source ↗</a>}</div></article>)}</section>
        <section><h3><span>05</span> Score breakdown</h3><div className="dimension-grid">{Object.entries(lead.score_dimensions).map(([key, value]) => <div key={key}><span>{key.replaceAll("_", " ")}</span><strong>{Math.round(value)}</strong></div>)}</div></section>
      </aside>
    </div>
  );
}
