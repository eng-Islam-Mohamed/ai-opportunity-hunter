import type { Bootstrap, Campaign, Lead, LeadDetail } from "./types";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ??
  (process.env.NODE_ENV === "production" ? "/api/backend" : "http://localhost:8000");

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    throw new Error(payload?.detail ?? `Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  bootstrap: () => request<Bootstrap>("/api/v1/bootstrap", { method: "POST" }),
  campaigns: (workspaceId: string) =>
    request<Campaign[]>(`/api/v1/campaigns?workspace_id=${workspaceId}`),
  createCampaign: (payload: object) =>
    request<Campaign>("/api/v1/campaigns", { method: "POST", body: JSON.stringify(payload) }),
  startCampaign: (campaignId: string) =>
    request(`/api/v1/campaigns/${campaignId}/start`, { method: "POST" }),
  campaign: (campaignId: string) => request<Campaign>(`/api/v1/campaigns/${campaignId}`),
  leads: (campaignId: string) => request<Lead[]>(`/api/v1/campaigns/${campaignId}/leads`),
  lead: (leadId: string) => request<LeadDetail>(`/api/v1/leads/${leadId}`),
  exportCsv: (campaignId: string) =>
    request<{ external_url: string }>(`/api/v1/campaigns/${campaignId}/export/csv`, {
      method: "POST",
    }),
  exportSheets: (campaignId: string) =>
    request<{ external_url: string }>(
      `/api/v1/campaigns/${campaignId}/export/google-sheets`,
      { method: "POST" },
    ),
};
