import type {
  AcceptAcceleratorCandidatePayload,
  AcceleratorCandidate,
  AcceleratorSpecExtractionResponse,
  AcceleratorSpecRecord,
  AskResponse,
  Channel,
  ChannelPayload,
  ChannelProbeRun,
  ChannelSecretPayload,
  ChannelSecretResponse,
  ChannelUpdatePayload,
  CodexJob,
  Domain,
  FetchRun,
  GraphResponse,
  HealthResponse,
  IngestTask,
  ManualIngestResponse,
  QueueTask,
  RunSummary,
  SearchResult,
  SettingsResponse,
  SourceProfile,
  SourcePayload,
  TrustAcceleratorCandidatesResponse,
  ValidationResponse,
  WikiPageDetail,
  WikiPageSummary,
  WikiMetricsResponse,
  WikiGraphResponse
} from "./types";

const API_BASE = resolveApiBase(
  import.meta.env.VITE_API_BASE ?? import.meta.env.VITE_API_BASE_URL,
  typeof window === "undefined" ? undefined : window.location.host
);

type RequestBody = object | undefined;

class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly detail: unknown
  ) {
    super(message);
    this.name = "ApiError";
  }
}

function resolveApiBase(configured?: string, browserHost?: string): string {
  const trimmed = configured?.trim();
  if (!trimmed) {
    return "/api";
  }

  const withoutTrailingSlash = trimmed.replace(/\/+$/, "");
  if (shouldUseProxyForRemoteLoopback(withoutTrailingSlash, browserHost)) {
    return "/api";
  }
  return withoutTrailingSlash.endsWith("/api") ? withoutTrailingSlash : `${withoutTrailingSlash}/api`;
}

function shouldUseProxyForRemoteLoopback(configuredBase: string, browserHost?: string) {
  if (!browserHost) {
    return false;
  }

  const pageHostname = browserHost.split(":")[0]?.toLowerCase();
  if (pageHostname === "localhost" || pageHostname === "127.0.0.1" || pageHostname === "::1") {
    return false;
  }

  try {
    const apiUrl = new URL(configuredBase);
    return apiUrl.hostname === "localhost" || apiUrl.hostname === "127.0.0.1" || apiUrl.hostname === "::1";
  } catch {
    return false;
  }
}

function withQuery(path: string, params: Record<string, string | number | boolean | null | undefined> = {}) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      query.set(key, String(value));
    }
  });
  const suffix = query.toString();
  return suffix ? `${path}?${suffix}` : path;
}

async function request<T>(path: string, options: { method?: string; body?: RequestBody } = {}): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: options.method ?? "GET",
    headers: options.body ? { "Content-Type": "application/json" } : undefined,
    body: options.body ? JSON.stringify(options.body) : undefined
  });

  const contentType = response.headers.get("content-type") ?? "";
  const payload = contentType.includes("application/json") ? await response.json() : await response.text();

  if (!response.ok) {
    const message =
      typeof payload === "object" && payload !== null && "detail" in payload
        ? JSON.stringify(payload.detail)
        : `请求失败：${response.status}`;
    throw new ApiError(message, response.status, payload);
  }

  return payload as T;
}

export async function getHealth(): Promise<HealthResponse> {
  return request<HealthResponse>("/health");
}

export async function getDomains(): Promise<Domain[]> {
  return request<Domain[]>("/domains");
}

export async function getSources(): Promise<SourceProfile[]> {
  return request<SourceProfile[]>("/sources");
}

export async function getSourcesForChannel(domain?: string, channelId?: string): Promise<SourceProfile[]> {
  return request<SourceProfile[]>(withQuery("/sources", { domain, channel_id: channelId }));
}

export async function createSource(payload: SourcePayload): Promise<SourceProfile> {
  return request<SourceProfile>("/sources", { method: "POST", body: payload });
}

export async function updateSource(id: string, payload: Partial<SourcePayload>): Promise<SourceProfile> {
  return request<SourceProfile>(`/sources/${encodeURIComponent(id)}`, { method: "PATCH", body: payload });
}

export async function getChannels(domain?: string): Promise<Channel[]> {
  return request<Channel[]>(withQuery("/channels", { domain }));
}

export async function createChannel(payload: ChannelPayload): Promise<Channel> {
  return request<Channel>("/channels", { method: "POST", body: payload });
}

export async function updateChannel(id: string, payload: ChannelUpdatePayload): Promise<Channel> {
  return request<Channel>(`/channels/${encodeURIComponent(id)}`, { method: "PATCH", body: payload });
}

export async function setChannelSecret(id: string, payload: ChannelSecretPayload): Promise<ChannelSecretResponse> {
  return request<ChannelSecretResponse>(`/channels/${encodeURIComponent(id)}/secret`, { method: "POST", body: payload });
}

export async function deleteChannelSecret(id: string): Promise<ChannelSecretResponse> {
  return request<ChannelSecretResponse>(`/channels/${encodeURIComponent(id)}/secret`, { method: "DELETE" });
}

export async function probeChannel(id: string): Promise<ChannelProbeRun> {
  return request<ChannelProbeRun>(`/channels/${encodeURIComponent(id)}/probe`, { method: "POST" });
}

export async function getChannelProbeRuns(id: string): Promise<ChannelProbeRun[]> {
  return request<ChannelProbeRun[]>(`/channels/${encodeURIComponent(id)}/probe-runs`);
}

export async function runSource(id: string): Promise<RunSummary> {
  return request<RunSummary>(`/sources/${encodeURIComponent(id)}/run`, { method: "POST" });
}

export async function createManualIngest(payload: {
  url: string;
  domain: string;
  auto_commit_enabled: boolean;
}): Promise<ManualIngestResponse> {
  return request<ManualIngestResponse>("/manual-ingests", { method: "POST", body: payload });
}

export async function getAcceleratorCandidates(): Promise<AcceleratorCandidate[]> {
  return request<AcceleratorCandidate[]>("/accelerator-candidates");
}

export async function acceptAcceleratorCandidate(
  id: number,
  payload: AcceptAcceleratorCandidatePayload
): Promise<AcceleratorCandidate> {
  return request<AcceleratorCandidate>(`/accelerator-candidates/${id}/accept`, { method: "POST", body: payload });
}

export async function trustAcceleratorCandidateSource(id: number): Promise<TrustAcceleratorCandidatesResponse> {
  return request<TrustAcceleratorCandidatesResponse>(`/accelerator-candidates/${id}/trust-source`, { method: "POST" });
}

export async function rejectAcceleratorCandidate(id: number): Promise<AcceleratorCandidate> {
  return request<AcceleratorCandidate>(`/accelerator-candidates/${id}/reject`, { method: "POST" });
}

export async function getAcceleratorSpecs(): Promise<AcceleratorSpecRecord[]> {
  return request<AcceleratorSpecRecord[]>("/accelerator-specs");
}

export async function extractAcceleratorSpecs(): Promise<AcceleratorSpecExtractionResponse> {
  return request<AcceleratorSpecExtractionResponse>("/accelerator-specs/extract", { method: "POST" });
}

export async function getRuns(): Promise<FetchRun[]> {
  return request<FetchRun[]>("/runs");
}

export async function getQueue(): Promise<IngestTask[]> {
  return request<IngestTask[]>("/queue");
}

export async function getWikiMetrics(): Promise<WikiMetricsResponse> {
  return request<WikiMetricsResponse>("/wiki/metrics");
}

export async function getWikiPages(domain: string): Promise<WikiPageSummary[]> {
  return request<WikiPageSummary[]>(withQuery("/wiki/pages", { domain }));
}

export async function getWikiPage(domain: string, path: string): Promise<WikiPageDetail> {
  return request<WikiPageDetail>(withQuery("/wiki/page", { domain, path }));
}

export async function approveTask(id: number): Promise<Record<string, unknown>> {
  return request<Record<string, unknown>>(`/queue/${id}/approve`, { method: "POST" });
}

export async function rejectTask(id: number, reason: string): Promise<Record<string, unknown>> {
  return request<Record<string, unknown>>(`/queue/${id}/reject`, { method: "POST", body: { reason } });
}

export async function trustQueueSource(
  id: number,
  payload: { mode: "manual" | "scheduled"; frequency?: "daily" | "weekly" | "monthly" }
): Promise<Record<string, unknown>> {
  return request<Record<string, unknown>>(`/queue/${id}/trust-source`, { method: "POST", body: payload });
}

export async function searchWiki(query: string, domain?: string): Promise<SearchResult[]> {
  return request<SearchResult[]>(withQuery("/search", { q: query, domain }));
}

export async function askCodex(domain: string, question: string, persist: boolean): Promise<{ job_id: number }> {
  return request<AskResponse>("/ask", { method: "POST", body: { domain, question, persist } });
}

export async function getJob(id: number): Promise<CodexJob> {
  return request<CodexJob>(`/jobs/${id}`);
}

export async function getLatestJob(domain?: string): Promise<CodexJob | null> {
  return request<CodexJob | null>(withQuery("/jobs/latest", { domain }));
}

export async function getGraph(domain?: string): Promise<WikiGraphResponse> {
  return request<WikiGraphResponse>(withQuery("/graph", { domain }));
}

export async function validateWiki(domain?: string): Promise<ValidationResponse> {
  return request<ValidationResponse>("/validate", { method: "POST", body: { domain } });
}

export async function rebuildSearch(domain?: string): Promise<{ indexed: number }> {
  return request<{ indexed: number }>(withQuery("/search/rebuild", { domain }), { method: "POST" });
}

export const api = {
  health: getHealth,
  settings: () => request<SettingsResponse>("/settings"),
  domains: getDomains,
  sources: getSources,
  sourcesForChannel: getSourcesForChannel,
  createSource,
  updateSource,
  channels: getChannels,
  createChannel,
  updateChannel,
  setChannelSecret,
  deleteChannelSecret,
  probeChannel,
  channelProbeRuns: getChannelProbeRuns,
  runSource,
  createManualIngest,
  acceleratorCandidates: getAcceleratorCandidates,
  acceptAcceleratorCandidate,
  trustAcceleratorCandidateSource,
  rejectAcceleratorCandidate,
  acceleratorSpecs: getAcceleratorSpecs,
  extractAcceleratorSpecs,
  runs: getRuns,
  queue: getQueue,
  wikiMetrics: getWikiMetrics,
  wikiPages: getWikiPages,
  wikiPage: getWikiPage,
  approveQueueTask: approveTask,
  rejectQueueTask: rejectTask,
  trustQueueSource,
  runQueueTask: (taskId: number, autoCommitEnabled = false) =>
    request<QueueTask>(`/queue/${taskId}/run`, { method: "POST", body: { auto_commit_enabled: autoCommitEnabled } }),
  commit: (payload: { domain: string; paths: string[]; message: string; source_id?: string }) =>
    request<Record<string, unknown>>("/commit", { method: "POST", body: payload }),
  search: searchWiki,
  rebuildSearch,
  ask: askCodex,
  graph: (domain?: string) => getGraph(domain) as Promise<GraphResponse>,
  validate: validateWiki,
  job: getJob,
  latestJob: getLatestJob
};

export { ApiError, request, resolveApiBase };
