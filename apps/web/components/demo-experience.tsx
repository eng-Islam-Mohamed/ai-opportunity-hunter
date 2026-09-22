"use client";

import Link from "next/link";
import { useState } from "react";
import type { Lead, LeadDetail } from "@/lib/types";
import { LeadDrawer } from "./lead-drawer";
import { LeadTable } from "./lead-table";

const demoLeads: LeadDetail[] = [
  { lead_id: "demo-1", company_id: "demo-company-1", company_name: "Atlas Dental Studio", website: "https://example.com", phone: "+213 770 12 34 56", location: "Aïn Beïda, Oum El Bouaghi", main_problem: "No verified online booking journey; appointment requests are routed through a generic contact path.", recommended_solution: "WhatsApp booking assistant + reminder flow", final_score: 91, band: "STRONG", confidence: 0.89, sales_angle: "Help patients request an appointment outside opening hours, while the team keeps control of confirmation.", status: "READY", opening_message: "I noticed your public booking journey appears to rely on a generic contact path. I prepared a small idea for turning WhatsApp inquiries into structured appointment requests.", score_dimensions: { problem_severity: 88, solution_fit: 95, evidence_strength: 89, urgency_signal: 80 }, top_reasons: [], evidence: [{ id: "demo-evidence-1", evidence_type: "website_observation", claim: "The public site did not expose a verified appointment-booking flow.", source_kind: "demo", source_url: null, confidence: 0.89 }], limitations: [] },
  { lead_id: "demo-2", company_id: "demo-company-2", company_name: "Cedar Home Interiors", website: "https://example.com", phone: "+213 660 45 89 10", location: "Constantine, Algeria", main_problem: "The public enquiry path does not capture project details before a sales conversation.", recommended_solution: "Lead qualification form + lightweight CRM", final_score: 84, band: "STRONG", confidence: 0.84, sales_angle: "Let sales staff receive better project context before returning a call.", status: "READY", opening_message: "Your work is visually strong. I noticed a simple opportunity to collect a few project details before inquiries reach your team.", score_dimensions: { problem_severity: 78, solution_fit: 91, evidence_strength: 83, urgency_signal: 72 }, top_reasons: [], evidence: [{ id: "demo-evidence-2", evidence_type: "conversion_observation", claim: "No structured project-brief capture was shown in this demonstration.", source_kind: "demo", source_url: null, confidence: 0.83 }], limitations: [] },
  { lead_id: "demo-3", company_id: "demo-company-3", company_name: "Northstar Legal Counsel", website: "https://example.com", phone: null, location: "Algiers, Algeria", main_problem: "The contact journey offers limited routing for different case types.", recommended_solution: "Case-intake agent + enquiry routing", final_score: 77, band: "QUALIFIED", confidence: 0.76, sales_angle: "Reduce back-and-forth by routing incoming requests to the right practice area.", status: "READY", opening_message: "I saw an opportunity to give new enquiries a clearer first step and help the right specialist receive the right context.", score_dimensions: { problem_severity: 70, solution_fit: 82, evidence_strength: 76, urgency_signal: 62 }, top_reasons: [], evidence: [{ id: "demo-evidence-3", evidence_type: "journey_observation", claim: "The demonstration shows a generic enquiry entry point without case-type routing.", source_kind: "demo", source_url: null, confidence: 0.76 }], limitations: [] },
];

export function DemoExperience() {
  const [selectedLead, setSelectedLead] = useState<LeadDetail | null>(null);
  return (
    <main className="demo-page">
      <nav className="demo-nav"><Link href="/">← Home</Link><span className="demo-badge">Interactive demo / No live data</span><Link href="/login?next=/workspace">Operator sign in ↗</Link></nav>
      <header className="demo-header"><span className="eyebrow"><span className="eyebrow-line" /> Example research outcome</span><h1>What a useful<br /><em>shortlist</em> looks like.</h1><p>These are illustrative sample companies. Opening a dossier does not call Google Places, an AI model, or Google Sheets.</p></header>
      <section className="demo-metrics"><div><span>Businesses reviewed</span><strong>30</strong></div><div><span>Qualified opportunities</span><strong>03</strong></div><div><span>Average opportunity score</span><strong>84<span>/100</span></strong></div><div><span>Demo credit usage</span><strong>0</strong></div></section>
      <section className="demo-ledger"><div className="demo-ledger-title"><div><span className="eyebrow">Evidence ledger</span><h2>Ranked opportunities</h2></div><span>Click “Open” to inspect the reasoning.</span></div><LeadTable leads={demoLeads as Lead[]} onSelect={(leadId) => setSelectedLead(demoLeads.find((lead) => lead.lead_id === leadId) ?? null)} /></section>
      <section className="demo-next"><span>Ready for a real market?</span><p>Your private workspace connects live discovery only when you deliberately start a campaign.</p><Link className="marketing-primary" href="/login?next=/workspace">Open operator workspace <span>↗</span></Link></section>
      <LeadDrawer lead={selectedLead} onClose={() => setSelectedLead(null)} />
    </main>
  );
}

