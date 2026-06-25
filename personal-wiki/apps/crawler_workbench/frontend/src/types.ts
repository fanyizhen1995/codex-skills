export type PageKey = "overview" | "sources" | "queue" | "knowledge" | "sourceWorkbench" | "settings";

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
  auto_ingest: boolean;
  auth_required: boolean;
  auth_state: string;
  topic: string;
  enabled: boolean;
  last_run_at?: string;
  last_run_status?: string;
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
  [key: string]: unknown;
}

export interface IngestTask {
  id: number;
  source_id?: string;
  target_domain?: string;
  status: string;
  title?: string;
  path?: string;
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
  score?: number;
  [key: string]: unknown;
}

export interface GraphResponse {
  nodes?: unknown[];
  edges?: unknown[];
  [key: string]: unknown;
}

export interface ValidationResponse {
  status: "succeeded" | "failed";
  stdout: string;
  stderr: string;
  validation_run_id: number;
}

export interface AskResponse {
  job_id: number;
}
