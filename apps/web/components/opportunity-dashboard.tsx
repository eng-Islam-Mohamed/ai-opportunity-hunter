"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Bootstrap, Campaign, Lead, LeadDetail } from "@/lib/types";
import { CampaignForm } from "./campaign-form";
import { LeadDrawer } from "./lead-drawer";
import { LeadTable } from "./lead-table";

const completedStatuses = ["READY_FOR_REVIEW", "COMPLETED"];

function readableStatus(status: string) {
  return status.replaceAll("_", " ").toLowerCase();
}

export function OpportunityDashboard() {
  const [bootstrap, setBootstrap] = useState<Bootstrap | null>(null);
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [activeCampaign, setActiveCampaign] = useState<Campaign | null>(null);
  const [leads, setLeads] = useState<Lead[]>([]);
  const [selectedLead, setSelectedLead] = useState<LeadDetail | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("Connecting to research engine…");

  const loadCampaigns = useCallback(async (workspaceId: string, selectedCampaignId?: string) => {
    const result = await api.campaigns(workspaceId);
    setCampaigns(result);
    const selectedCampaign = result.find((campaign) => campaign.id === selectedCampaignId) ?? result[0];
    if (selectedCampaign) {
      setActiveCampaign(selectedCampaign);
      setLeads(await api.leads(selectedCampaign.id));
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    api.bootstrap()
      .then(async (result) => {
        if (controller.signal.aborted) return;
        setBootstrap(result);
        await loadCampaigns(result.workspace_id);
        setMessage("Workspace ready");
      })
      .catch((error: Error) => setMessage(error.message));
    return () => controller.abort();
  }, [loadCampaigns]);

  async function createAndRun(values: { name: string; location: string; sector: string; maximum: number }) {
    if (!bootstrap) return;
    setBusy(true);
    setMessage("Creating campaign…");
    try {
      const campaign = await api.createCampaign({
        workspace_id: bootstrap.workspace_id,
        name: values.name,
        target: { query: values.sector, location_text: values.location, country_code: "AE", language: "en" },
        limits: { max_discovery_candidates: values.maximum, max_enriched_candidates: values.maximum, max_full_audits: values.maximum, max_llm_analyses: values.maximum },
        service_catalog_item_ids: bootstrap.service_ids,
        qualification: { contactability_required: true },
        analysis_preferences: { languages: ["en", "ar"], focus_categories: ["booking", "website_ux", "automation"] },
        export: { google_sheets_enabled: false, minimum_score: 70 },
      });
      setActiveCampaign(campaign);
      setLeads([]);
      await api.startCampaign(campaign.id);
      setMessage(`Research running: 0 / ${values.maximum} discovered…`);
      const deadline = Date.now() + Math.min(Math.max(values.maximum * 2_000, 60_000), 300_000);
      let completed = false;
      while (Date.now() < deadline) {
        await new Promise((resolve) => setTimeout(resolve, 700));
        const updated = await api.campaign(campaign.id);
        setActiveCampaign(updated);
        setMessage(`Research running: ${updated.progress.discovered ?? 0} / ${values.maximum} discovered…`);
        if ([...completedStatuses, "FAILED"].includes(updated.status)) {
          completed = true;
          break;
        }
      }
      setLeads(await api.leads(campaign.id));
      await loadCampaigns(bootstrap.workspace_id, campaign.id);
      setMessage(completed ? "Campaign ready for review" : "Research continues in the background. Results will update shortly.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Campaign failed");
    } finally {
      setBusy(false);
    }
  }

  async function selectCampaign(campaign: Campaign) {
    setActiveCampaign(campaign);
    setSelectedLead(null);
    try {
      setLeads(await api.leads(campaign.id));
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not load leads");
    }
  }

  async function exportResults(provider: "csv" | "sheets") {
    if (!activeCampaign) {
      setMessage("Run or select a campaign before exporting.");
      return;
    }
    if (!completedStatuses.includes(activeCampaign.status)) {
      setMessage("Please wait until the current campaign finishes before exporting.");
      return;
    }
    try {
      const result = provider === "csv" ? await api.exportCsv(activeCampaign.id) : await api.exportSheets(activeCampaign.id);
      setMessage(`Export ready: ${result.external_url}`);
      if (result.external_url.startsWith("https://")) window.open(result.external_url, "_blank", "noopener,noreferrer");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Export failed");
    }
  }

  const hotLeads = leads.filter((lead) => lead.final_score >= 80).length;
  const averageScore = leads.length ? Math.round(leads.reduce((total, lead) => total + lead.final_score, 0) / leads.length) : 0;
  const discovered = activeCampaign?.progress.discovered ?? 0;
  const requested = activeCampaign?.progress.requested ?? activeCampaign?.limits.max_discovery_candidates ?? 0;

  return (
    <main className="app-shell">
      <aside className="sidebar" aria-label="Campaign navigation">
        <div className="brand-lockup">
          <div className="brand-symbol" aria-hidden="true"><span /><span /><span /><span /></div>
          <div><strong>Opportunity<br />Hunter<span className="brand-period">.</span></strong><small>Business intelligence studio</small></div>
        </div>
        <div className="sidebar-section-label"><span>01</span> Campaign archive <span className="sidebar-count">{campaigns.length}</span></div>
        <div className="campaign-list">
          {campaigns.length === 0 && <p className="sidebar-empty">Your research runs will appear here.</p>}
          {campaigns.map((campaign) => (
            <button
              className={activeCampaign?.id === campaign.id ? "campaign-item active" : "campaign-item"}
              key={campaign.id}
              onClick={() => void selectCampaign(campaign)}
              aria-current={activeCampaign?.id === campaign.id ? "page" : undefined}
            >
              <span className="campaign-item-name">{campaign.name}</span>
              <small>{readableStatus(campaign.status)} <span aria-hidden="true">↗</span></small>
            </button>
          ))}
        </div>
        <div className="sidebar-bottom">
          <div className="sidebar-rule" />
          <span className="sidebar-kicker">The operating principle</span>
          <p>Find the evidence.<br />Then make the offer.</p>
          <div className="system-status" role="status" aria-live="polite"><i aria-hidden="true" /><span>{message}</span></div>
        </div>
      </aside>

      <div className="workspace">
        <div className="topline"><span>Intelligence / Campaign workspace</span><a href="/account">Account & daily allowance ↗</a></div>

        <header className="hero">
          <div className="hero-copy">
            <span className="eyebrow"><span className="eyebrow-line" /> Prospecting, with proof</span>
            <h1>Find the signal.<br /><em>Win the work.</em></h1>
            <p>A clearer view of who needs your services, why they need them, and what to say first.</p>
          </div>
          <div className="hero-aside" aria-hidden="true">
            <span className="hero-aside-label">Opportunity / No. 001</span>
            <div className="hero-orbit"><span className="orbit-core" /><span className="orbit-node orbit-node-one" /><span className="orbit-node orbit-node-two" /></div>
            <span className="hero-aside-bottom">Research → evidence → action</span>
          </div>
        </header>

        <section className="metrics" aria-label="Campaign overview">
          <article><span className="metric-index">01 / Leads found</span><strong>{leads.length.toString().padStart(2, "0")}</strong><small><b>{hotLeads}</b> high-priority opportunities</small></article>
          <article><span className="metric-index">02 / Discovery</span><strong>{discovered}<span className="metric-divider"> / {requested}</span></strong><small>Real businesses matching your search</small></article>
          <article><span className="metric-index">03 / Average score</span><strong>{averageScore}<span className="metric-unit"> / 100</span></strong><small>Confidence-adjusted ranking</small></article>
          <article className="metric-status"><span className="metric-index">04 / Pipeline state</span><strong>{activeCampaign ? readableStatus(activeCampaign.status) : "Standing by"}</strong><small><span className="status-dot" /> {activeCampaign ? activeCampaign.name : "Ready for your first run"}</small></article>
        </section>

        <section className="section-block research-section" aria-labelledby="research-heading">
          <div className="section-title"><span className="section-number">01</span><div><span className="eyebrow">Define the search</span><h2 id="research-heading">A focused brief gets better leads.</h2></div><p>Choose a market, a business type and a search limit. The engine turns that brief into ranked opportunities.</p></div>
          <CampaignForm busy={busy || !bootstrap} onCreate={createAndRun} />
        </section>

        <section className="section-block results-section" aria-labelledby="results-heading">
          <div className="section-title results-title"><span className="section-number">02</span><div><span className="eyebrow">The shortlist</span><h2 id="results-heading">Opportunity ledger</h2></div><div className="results-actions"><span className="result-count">{leads.length} {leads.length === 1 ? "result" : "results"}</span><button className="secondary-button" onClick={() => void exportResults("csv")}>Export CSV <span aria-hidden="true">↗</span></button><button className="primary-button" onClick={() => void exportResults("sheets")}>Send to Sheets <span aria-hidden="true">↗</span></button></div></div>
          <LeadTable leads={leads} onSelect={(leadId) => void api.lead(leadId).then(setSelectedLead).catch((error: Error) => setMessage(error.message))} />
        </section>

        <footer className="workspace-footer"><span>OH / Evidence-first prospecting</span><span>Human judgment stays in the loop.</span></footer>
      </div>
      <LeadDrawer lead={selectedLead} onClose={() => setSelectedLead(null)} />
    </main>
  );
}
