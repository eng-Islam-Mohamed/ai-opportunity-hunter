export type Bootstrap = {
  workspace_id: string;
  service_ids: string[];
  created: boolean;
};

export type Campaign = {
  id: string;
  workspace_id: string;
  name: string;
  status: string;
  target: { query: string; location_text: string; country_code: string };
  limits: { max_discovery_candidates?: number };
  progress: { requested?: number; discovered?: number; analyzed?: number; qualified?: number };
  created_at: string;
};

export type Lead = {
  lead_id: string;
  company_id: string;
  company_name: string;
  website: string | null;
  phone: string | null;
  location: string | null;
  main_problem: string | null;
  recommended_solution: string | null;
  final_score: number;
  band: string;
  confidence: number;
  sales_angle: string | null;
  status: string;
};

export type LeadDetail = Lead & {
  opening_message: string | null;
  score_dimensions: Record<string, number>;
  top_reasons: string[];
  evidence: Array<{
    id: string;
    evidence_type: string;
    claim: string;
    source_kind: string;
    source_url: string | null;
    confidence: number;
  }>;
  limitations: string[];
};
