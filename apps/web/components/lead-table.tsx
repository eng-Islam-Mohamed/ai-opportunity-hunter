import type { Lead } from "@/lib/types";

type LeadTableProps = { leads: Lead[]; onSelect: (leadId: string) => void };

export function LeadTable({ leads, onSelect }: LeadTableProps) {
  if (leads.length === 0) {
    return <div className="empty-state"><span className="empty-state-symbol" aria-hidden="true">◎</span><div><strong>The ledger is waiting for its first lead.</strong><p>Launch a research run above. Evidence-backed opportunities will appear here, ready to review and export.</p></div><span className="empty-state-code">NO RESULTS / YET</span></div>;
  }
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr><th>Company / Market</th><th>Detected opportunity</th><th>Recommended offer</th><th>Score</th><th>Brief</th></tr>
        </thead>
        <tbody>
          {leads.map((lead) => (
            <tr key={lead.lead_id}>
              <td><strong>{lead.company_name}</strong><small>{lead.location || "Location unverified"}</small></td>
              <td className="problem-cell">{lead.main_problem || "No supported problem yet"}</td>
              <td className="offer-cell">{lead.recommended_solution || "Awaiting review"}</td>
              <td><span className={`score score-${lead.band.toLowerCase()}`}>{Math.round(lead.final_score)}</span></td>
              <td><button className="text-button" onClick={() => onSelect(lead.lead_id)} aria-label={`View brief for ${lead.company_name}`}>Open <span aria-hidden="true">↗</span></button></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
