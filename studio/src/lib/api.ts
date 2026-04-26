// Typed Memwire API client.
//
// - Reads X-API-Key from localStorage (key: mw_api_key)
// - Injects it on every request
// - On 401, clears the stored key and throws ApiError
// - Base URL is empty by default (relative paths) — set VITE_API_URL to override
//   (e.g. when Studio is hosted on a different origin than the backend)

const API_BASE = (import.meta.env.VITE_API_URL ?? "") as string
const KEY_STORAGE = "mw_api_key"

export class ApiError extends Error {
  status: number
  constructor(message: string, status: number) {
    super(message)
    this.status = status
    this.name = "ApiError"
  }
}

export function getApiKey(): string | null {
  if (typeof window === "undefined") return null
  return localStorage.getItem(KEY_STORAGE)
}

export function setApiKey(key: string | null) {
  if (typeof window === "undefined") return
  if (key) localStorage.setItem(KEY_STORAGE, key)
  else localStorage.removeItem(KEY_STORAGE)
  window.dispatchEvent(new CustomEvent("mw:auth-changed"))
}

function qs(params: Record<string, unknown>): string {
  const usp = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) {
    if (v === undefined || v === null || v === "") continue
    usp.set(k, String(v))
  }
  return usp.toString()
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const key = getApiKey()
  const headers = new Headers(init.headers)
  if (key) headers.set("X-API-Key", key)
  if (
    init.body &&
    !(init.body instanceof FormData) &&
    !headers.has("Content-Type")
  ) {
    headers.set("Content-Type", "application/json")
  }
  let res: Response
  try {
    res = await fetch(API_BASE + path, { ...init, headers })
  } catch (e) {
    throw new ApiError(
      e instanceof Error ? e.message : "Network error",
      0,
    )
  }
  if (res.status === 401) {
    setApiKey(null)
    throw new ApiError("Invalid or missing API key", 401)
  }
  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = await res.json()
      detail = body.detail || JSON.stringify(body)
    } catch {
      // fallthrough — keep statusText
    }
    throw new ApiError(detail, res.status)
  }
  if (res.status === 204 || res.headers.get("content-length") === "0") {
    return undefined as unknown as T
  }
  return (await res.json()) as T
}

// ─── Types (mirror server schemas) ────────────────────────────────

export type Health = { status: string; version: string }

export type Memory = {
  memory_id: string
  user_id: string
  content: string
  role: string
  category?: string | null
  strength: number
  timestamp: number
  node_ids: string[]
  agent_id?: string | null
}

export type MemoryListItem = Memory & {
  workspace_id?: string | null
  app_id?: string | null
  org_id?: string | null
  access_count: number
}

export type MemoryListResponse = {
  items: MemoryListItem[]
  total: number
  limit: number
  offset: number
}

export type RecallPath = { tokens: string[]; score: number; memories: Memory[] }

export type KnowledgeChunkResult = {
  chunk_id: string
  kb_id: string
  content: string
  score: number
  metadata: Record<string, unknown>
}

export type RecallResponse = {
  query: string
  supporting: RecallPath[]
  conflicting: RecallPath[]
  knowledge: KnowledgeChunkResult[]
  formatted: string
  has_conflicts: boolean
}

export type SearchHit = { memory: Memory; score: number }

export type FeedbackResponse = { strengthened: number; weakened: number }

export type KnowledgeBase = {
  kb_id: string
  name: string
  description: string
  user_id: string
  agent_id?: string | null
  workspace_id?: string | null
  app_id?: string | null
  chunk_count: number
  created_at: number
}

export type KnowledgeListResponse = {
  items: KnowledgeBase[]
  total: number
  limit: number
  offset: number
}

export type IngestResponse = { kb_id: string; name: string; chunks: number }

export type DashboardStats = {
  total_memories: number
  distinct_users: number
  total_nodes: number
  total_edges: number
  total_knowledge_bases: number
  total_anchors: number
  by_category: Record<string, number>
  by_role: Record<string, number>
  timeseries: { ts: number; count: number }[]
}

export type ActivityItem = {
  type: string
  timestamp: number
  user_id: string
  summary: string
  related_id: string
  role?: string | null
  category?: string | null
}

export type ActivityResponse = { items: ActivityItem[] }

export type Workspace = {
  workspace_id: string | null
  memory_count: number
  user_count: number
  last_active: number
}

export type WorkspaceListResponse = { items: Workspace[] }

export type ChatMessage = { role: string; content: string }

export type ChatRequestBody = {
  user_id: string
  messages: ChatMessage[]
  model?: string
  agent_id?: string
  app_id?: string
  workspace_id?: string
}

export type ChatUsage = {
  prompt_tokens: number
  completion_tokens: number
  total_tokens: number
}

export type ChatResponse = {
  message: ChatMessage
  model: string
  recall: RecallResponse
  usage?: ChatUsage
  recall_ms?: number
  llm_ms?: number
}

export type ProviderInfo = {
  configured: boolean
  base_url: string
  default_model: string
  available_models: string[]
}

export type ProvidersResponse = {
  providers: Record<string, ProviderInfo>
}

export type GraphNode = {
  node_id: string
  token: string
  memory_ids: string[]
  connections: number
}

export type GraphEdge = {
  source_id: string
  target_id: string
  weight: number
}

export type GraphResponse = {
  nodes: GraphNode[]
  edges: GraphEdge[]
  total_nodes: number
  total_edges: number
  truncated: boolean
}

export type AuthInfoResponse = {
  configured: boolean
  configured_count: number
  current_key_prefix: string | null
}

export type LLMConfigItem = {
  api_key: string
  base_url?: string
  default_model?: string
  available_models?: string[]
}

export type LLMConfigResponse = {
  configured: boolean
  env_locked: boolean
  base_url: string
  default_model: string
  available_models: string[]
  api_key_prefix?: string | null
  api_key_suffix?: string | null
}

export type LLMTestRequest = {
  api_key?: string
  base_url?: string
  default_model?: string
}

export type LLMTestResponse = {
  ok: boolean
  model?: string | null
  error?: string | null
  latency_ms?: number | null
}

// ─── Filter param types ───────────────────────────────────────────

export type Scope = {
  user_id?: string
  agent_id?: string
  app_id?: string
  workspace_id?: string
}

export type ListMemoriesParams = Scope & {
  category?: string
  role?: string
  since?: number
  until?: number
  search?: string
  limit?: number
  offset?: number
}

export type ListKnowledgeParams = Scope & {
  search?: string
  limit?: number
  offset?: number
}

// ─── Endpoint methods ─────────────────────────────────────────────

export const api = {
  health: () => request<Health>("/health"),

  stats: (org_id?: string) =>
    request<DashboardStats>(`/v1/stats${org_id ? `?${qs({ org_id })}` : ""}`),

  activity: (limit = 50) =>
    request<ActivityResponse>(`/v1/activity?${qs({ limit })}`),

  workspaces: () => request<WorkspaceListResponse>("/v1/workspaces"),

  listMemories: (params: ListMemoriesParams = {}) =>
    request<MemoryListResponse>(`/v1/memories?${qs(params)}`),

  addMemory: (body: {
    user_id: string
    messages: { role: string; content: string }[]
    agent_id?: string
    app_id?: string
    workspace_id?: string
  }) =>
    request<Memory[]>("/v1/memories", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  recall: (body: {
    query: string
    user_id: string
    agent_id?: string
    app_id?: string
    workspace_id?: string
  }) =>
    request<RecallResponse>("/v1/memories/recall", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  search: (body: {
    query: string
    user_id: string
    agent_id?: string
    app_id?: string
    workspace_id?: string
    category?: string
    limit?: number
  }) =>
    request<SearchHit[]>("/v1/memories/search", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  feedback: (body: {
    assistant_response: string
    user_id: string
    agent_id?: string
    app_id?: string
    workspace_id?: string
  }) =>
    request<FeedbackResponse>("/v1/memories/feedback", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  listKnowledge: (params: ListKnowledgeParams = {}) =>
    request<KnowledgeListResponse>(`/v1/knowledge?${qs(params)}`),

  addKnowledge: (body: {
    name: string
    chunks: { content: string; metadata?: Record<string, unknown> }[]
    user_id: string
    agent_id?: string
    app_id?: string
    workspace_id?: string
  }) =>
    request<{ kb_id: string }>("/v1/knowledge", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  ingest: (
    file: File,
    params: {
      user_id: string
      name?: string
      agent_id?: string
      app_id?: string
      workspace_id?: string
      chunk_max_characters?: number
      chunk_overlap?: number
    },
  ) => {
    const fd = new FormData()
    fd.append("file", file)
    for (const [k, v] of Object.entries(params)) {
      if (v !== undefined && v !== null) fd.append(k, String(v))
    }
    return request<IngestResponse>("/v1/knowledge/ingest", {
      method: "POST",
      body: fd,
    })
  },

  searchKnowledge: (body: {
    query: string
    user_id: string
    agent_id?: string
    app_id?: string
    workspace_id?: string
    limit?: number
  }) =>
    request<KnowledgeChunkResult[]>("/v1/knowledge/search", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  deleteKnowledge: (kbId: string, userId: string) =>
    request<{ deleted: string }>(
      `/v1/knowledge/${encodeURIComponent(kbId)}?user_id=${encodeURIComponent(userId)}`,
      { method: "DELETE" },
    ),

  chat: (body: ChatRequestBody) =>
    request<ChatResponse>("/v1/chat", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  chatProviders: () => request<ProvidersResponse>("/v1/chat/providers"),

  graph: (userId: string, limit = 200) =>
    request<GraphResponse>(`/v1/graph?${qs({ user_id: userId, limit })}`),

  authInfo: () => request<AuthInfoResponse>("/v1/auth/info"),

  llmConfig: () => request<LLMConfigResponse>("/v1/llm/config"),
  saveLlmConfig: (body: LLMConfigItem) =>
    request<LLMConfigResponse>("/v1/llm/config", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  clearLlmConfig: () =>
    request<LLMConfigResponse>("/v1/llm/config", { method: "DELETE" }),
  testLlm: (body: LLMTestRequest) =>
    request<LLMTestResponse>("/v1/llm/test", {
      method: "POST",
      body: JSON.stringify(body),
    }),
}
