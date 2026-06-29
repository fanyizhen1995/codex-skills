export type PageKey =
  | "overview"
  | "sources"
  | "queue"
  | "knowledge"
  | "wikiBrowser"
  | "acceleratorSpecs"
  | "sourceWorkbench"
  | "settings";

export type Status =
  | "ready"
  | "pending"
  | "running"
  | "succeeded"
  | "failed"
  | "needs_auth_config"
  | "trusted"
  | "untrusted";

export interface HealthResponse {
  status: string;
  bind_host: string;
  bind_port: number;
  authenticated: boolean;
  warning: string;
}

export interface SettingsResponse extends HealthResponse {
  wiki_root: string;
  database_path: string;
}

export interface Domain {
  id: string;
  name: string;
}

export interface SourceProfile {
  id: string;
  name: string;
  type: string;
  target_domain: string;
  url: string;
  trust_level: string;
  schedule: string;
  run_policy: "scheduled" | "once" | string;
  auto_ingest: boolean;
  auth_required: boolean;
  auth_state: string;
  topic: string;
  enabled: boolean;
  last_run_at?: string;
  last_run_status?: string;
}

export interface AcceleratorCandidate {
  id: number;
  vendor: string;
  model_name: string;
  normalized_model: string;
  scope: string;
  source_profile_id: string;
  source_url: string;
  evidence_url?: string | null;
  evidence_text: string;
  confidence: number;
  status: "pending" | "accepted" | "rejected" | string;
  accepted_source_id?: string | null;
  created_at: string;
  updated_at: string;
}

export interface AcceptAcceleratorCandidatePayload {
  source_id: string;
  name: string;
  url: string;
  scope: string[];
  source_rank: string;
}

export interface TrustAcceleratorCandidatesResponse {
  domain: string;
  accepted_count: number;
  candidate_ids: number[];
  accepted_source_ids: string[];
  candidates: AcceleratorCandidate[];
}

export interface AcceleratorObservation {
  id: number;
  field: string;
  value_text: string;
  value_number?: number | null;
  unit: string;
  source_profile_id: string;
  source_rank: string;
  raw_item_id?: number | null;
  raw_path: string;
  evidence_text: string;
  confidence: number;
}

export interface AcceleratorResolvedField {
  field: string;
  value_text: string;
  value_number?: number | null;
  unit: string;
  source_observation_id: number;
  resolved_by: string;
  confidence: string;
  conflict_status: string;
}

export interface AcceleratorSpecRecord {
  sku_id: string;
  vendor: string;
  model_name: string;
  normalized_model: string;
  scope: string;
  source_profile_id: string;
  source_url: string;
  raw_item_id?: number | null;
  raw_path: string;
  observations: AcceleratorObservation[];
  resolved_specs: AcceleratorResolvedField[];
}

export interface AcceleratorSpecExtractionResponse {
  skus: number;
  observations: number;
  resolved: number;
}

export interface RunSummary {
  source_id: string;
  status: string;
  run_id?: number;
  fetched_count?: number;
  changed_count?: number;
  failed_count?: number;
  [key: string]: unknown;
}

export interface FetchRun {
  id: number;
  source_id?: string;
  status: string;
  started_at?: string;
  finished_at?: string;
  fetched_count?: number;
  changed_count?: number;
  failed_count?: number;
  failure_reason?: string;
  error?: string;
  [key: string]: unknown;
}

export interface IngestTask {
  id: number;
  source_id?: string;
  target_domain?: string;
  status: string;
  title?: string;
  path?: string;
  canonical_url?: string;
  raw_path?: string;
  content_bytes?: number;
  content_preview?: string;
  metadata?: Record<string, unknown>;
  reason?: string;
  created_at?: string;
  updated_at?: string;
  [key: string]: unknown;
}

export type QueueTask = IngestTask;

export interface SearchResult {
  domain?: string;
  path: string;
  title?: string;
  snippet?: string;
  description?: string;
  score?: number;
  [key: string]: unknown;
}

export interface WikiGraphNode {
  id: string;
  title?: string;
  path?: string;
  type?: string;
  domain?: string;
  [key: string]: unknown;
}

export interface WikiGraphEdge {
  source: string;
  target: string;
  label?: string;
  type?: string;
  [key: string]: unknown;
}

export interface WikiGraphResponse {
  nodes: WikiGraphNode[];
  edges: WikiGraphEdge[];
  [key: string]: unknown;
}

export type GraphResponse = WikiGraphResponse;

export interface WikiPageSummary {
  domain: string;
  path: string;
  full_path: string;
  type?: string | null;
  title?: string | null;
  description?: string | null;
  status?: string | null;
  tags?: string[];
  source_refs?: string[];
}

export interface WikiPageDetail extends WikiPageSummary {
  content?: string;
  body?: string;
}

export interface ValidationResponse {
  status: "succeeded" | "failed";
  stdout: string;
  stderr: string;
  validation_run_id: number;
}

export interface WikiMetricsResponse {
  counts: {
    domain_count: number;
    wiki_page_count: number;
    raw_file_count: number;
    raw_item_count: number;
    total_file_count: number;
  };
  sizes: {
    total_bytes: number;
    wiki_bytes: number;
    raw_bytes: number;
    global_bytes: number;
    state_bytes: number;
  };
  health: {
    status: string;
    score: number;
    summary: string;
    latest_validation_status?: string | null;
    latest_validation_at?: string | null;
    failed_run_count: number;
    failed_task_count: number;
    pending_task_count: number;
  };
}

export interface AskResponse {
  job_id: number;
}

export interface CodexJob {
  id?: number;
  job_id?: number;
  status: "pending" | "running" | "succeeded" | "failed" | string;
  question?: string;
  answer?: string;
  stdout?: string;
  stderr?: string;
  error?: string;
  cited_paths?: string[];
  citations?: string[];
  related_pages?: SearchResult[];
  created_at?: string;
  updated_at?: string;
  [key: string]: unknown;
}
