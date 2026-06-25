import type {
  AskResponse,
  Domain,
  FetchRun,
  GraphResponse,
  HealthResponse,
  QueueTask,
  SearchResult,
  SettingsResponse,
  SourceProfile,
  ValidationResponse
} from "./types";

const API_BASE = resolveApiBase(import.meta.env.VITE_API_BASE ?? import.meta.env.VITE_API_BASE_URL);

type RequestBody = Record<string, unknown> | undefined;

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

function resolveApiBase(configured?: string): string {
  const trimmed = configured?.trim();
  if (!trimmed) {
    return "/api";
  }

  const withoutTrailingSlash = trimmed.replace(/\/+$/, "");
  return withoutTrailingSlash.endsWith("/api") ? withoutTrailingSlash : `${withoutTrailingSlash}/api`;
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

export const api = {
  health: () => request<HealthResponse>("/health"),
  settings: () => request<SettingsResponse>("/settings"),
  domains: () => request<Domain[]>("/domains"),
  sources: () => request<SourceProfile[]>("/sources"),
  runSource: (sourceId: string) => request<Record<string, unknown>>(`/sources/${encodeURIComponent(sourceId)}/run`, { method: "POST" }),
  runs: () => request<FetchRun[]>("/runs"),
  queue: () => request<QueueTask[]>("/queue"),
  approveQueueTask: (taskId: number) => request<QueueTask>(`/queue/${taskId}/approve`, { method: "POST" }),
  rejectQueueTask: (taskId: number, reason: string) =>
    request<QueueTask>(`/queue/${taskId}/reject`, { method: "POST", body: { reason } }),
  runQueueTask: (taskId: number, autoCommitEnabled = false) =>
    request<QueueTask>(`/queue/${taskId}/run`, { method: "POST", body: { auto_commit_enabled: autoCommitEnabled } }),
  commit: (payload: { domain: string; paths: string[]; message: string; source_id?: string }) =>
    request<Record<string, unknown>>("/commit", { method: "POST", body: payload }),
  search: (query: string, domain?: string) => request<SearchResult[]>(withQuery("/search", { q: query, domain })),
  rebuildSearch: (domain?: string) => request<Record<string, unknown>>(withQuery("/search/rebuild", { domain }), { method: "POST" }),
  ask: (domain: string, question: string, persist = false) =>
    request<AskResponse>("/ask", { method: "POST", body: { domain, question, persist } }),
  graph: (domain?: string) => request<GraphResponse>(withQuery("/graph", { domain })),
  validate: (domain?: string) => request<ValidationResponse>("/validate", { method: "POST", body: { domain } }),
  job: (jobId: number) => request<Record<string, unknown>>(`/jobs/${jobId}`)
};

export { ApiError, request, resolveApiBase };
