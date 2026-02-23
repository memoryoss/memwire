// ---------------------------------------------------------------------------
// MemWire API client
// All requests use the Bearer token stored in localStorage under "mw_api_key".
// ---------------------------------------------------------------------------

const getApiUrl = () =>
  (import.meta as Record<string, unknown>).env?.VITE_API_URL as string ?? "";

const getKey = () => localStorage.getItem("mw_api_key") ?? "";

async function request<T>(
  path: string,
  init: RequestInit = {}
): Promise<T> {
  const url = `${getApiUrl()}${path}`;
  const res = await fetch(url, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${getKey()}`,
      ...(init.headers ?? {}),
    },
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `HTTP ${res.status}`);
  }
  return res.json() as Promise<T>;
}

// ── Types ──────────────────────────────────────────────────────────────────

export interface APIKey {
  id: string;
  agent_id: string;
  name: string;
  prefix: string;
  last_used_at?: string;
  created_at: string;
}

export interface APIKeyCreated extends APIKey {
  key: string; // full key — only returned once
}

export interface MemoryTurn {
  id: string;
  memory: string;
  topics: string[];
  user_id: string;
  timestamp?: string;
}

export interface MemoryHistoryResponse {
  agent_id: string;
  user_id: string;
  memories: MemoryTurn[];
  total: number;
}

export interface MemoryListResponse {
  memories: MemoryTurn[];
  total: number;
}

export interface KBDocument {
  doc_id: string;
  doc_name: string;
  source_type: "text" | "url" | "file";
  source?: string;
  chunk_count: number;
  created_at: string;
}

export interface KBUploadResponse {
  success: boolean;
  doc_id: string;
  doc_name: string;
  chunks_created: number;
}

export interface ContextSnapshot {
  agent_id: string;
  user_id: string;
  context: string;
  memory_hits: number;
  knowledge_hits: number;
  token_estimate: number;
}

// ── Settings types ─────────────────────────────────────────────────────────

export interface LLMConfig {
  provider: string;
  model: string;
  api_key_set: boolean;
  base_url?: string;
  azure_deployment?: string;
  azure_api_version?: string;
}

export interface EmbedderConfig {
  provider: string;
  model: string;
  api_key_set: boolean;
  base_url?: string;
  dimensions: number;
}

export interface DatabaseConfig {
  use_bundled: boolean;
  host?: string;
  port: number;
  database?: string;
  username?: string;
}

export interface AppSettings {
  llm: LLMConfig;
  embedder: EmbedderConfig;
  database: DatabaseConfig;
}

export interface SettingsUpdate {
  llm?: {
    provider: string;
    model: string;
    api_key?: string;
    base_url?: string;
    azure_deployment?: string;
    azure_api_version?: string;
  };
  embedder?: {
    provider: string;
    model: string;
    api_key?: string;
    base_url?: string;
    dimensions?: number;
  };
  database?: {
    use_bundled: boolean;
    host?: string;
    port?: number;
    database?: string;
    username?: string;
    password?: string;
  };
}

// ── API object ─────────────────────────────────────────────────────────────
export const api = {
  // ── API Keys ──────────────────────────────────────────────────────────────
  apiKeys: {
    list: (agentId: string) =>
      request<{ keys: APIKey[]; total: number }>(`/v1/api-keys?agent_id=${agentId}`).then((r) => r.keys),
    create: (agentId: string, name: string) =>
      request<APIKeyCreated>("/v1/api-keys", {
        method: "POST",
        body: JSON.stringify({ agent_id: agentId, name }),
      }),
    delete: (id: string) =>
      request<{ success: boolean }>(`/v1/api-keys/${id}`, {
        method: "DELETE",
      }),
  },

  // ── Memory ────────────────────────────────────────────────────────────────
  memory: {    list: (agentId?: string, userId?: string, limit = 100) => {
      const p = new URLSearchParams({ limit: String(limit) });
      if (agentId) p.set("agent_id", agentId);
      if (userId) p.set("user_id", userId);
      return request<MemoryListResponse>(`/v1/memory/list?${p}`);
    },    history: (agentId: string, userId: string, limit = 50) =>
      request<MemoryHistoryResponse>(
        `/v1/memory/history?agent_id=${agentId}&user_id=${userId}&limit=${limit}`
      ),    store: (
      agentId: string,
      userId: string,
      userMessage: string,
      assistantMessage: string,
      sessionId?: string,
    ) =>
      request<{ success: boolean; memory_id: string }>("/v1/memory/store", {
        method: "POST",
        body: JSON.stringify({
          agent_id: agentId,
          user_id: userId,
          user_message: userMessage,
          assistant_message: assistantMessage,
          session_id: sessionId,
        }),
      }),    search: (agentId: string, userId: string, query: string) =>
      request<{ results: MemoryTurn[] }>(
        `/v1/memory/search?agent_id=${agentId}&user_id=${userId}&query=${encodeURIComponent(query)}`
      ),
    clear: (agentId: string, userId: string) =>
      request<{ cleared: boolean }>("/v1/memory/clear", {
        method: "DELETE",
        body: JSON.stringify({ agent_id: agentId, user_id: userId }),
      }),
  },

  // ── Knowledge ─────────────────────────────────────────────────────────────
  knowledge: {
    list: (agentId: string) =>
      request<{ agent_id: string; documents: KBDocument[]; total: number }>(
        `/v1/knowledge?agent_id=${agentId}`
      ).then((r) => r.documents),
    search: (agentId: string, query: string, limit = 5) =>
      request<{ results: KBDocument[]; total: number }>("/v1/knowledge/search", {
        method: "POST",
        body: JSON.stringify({ agent_id: agentId, query, limit }),
      }).then((r) => r.results),
    uploadText: (agentId: string, docName: string, content: string) =>
      request<KBUploadResponse>("/v1/knowledge/upload/text", {
        method: "POST",
        body: JSON.stringify({ agent_id: agentId, doc_name: docName, content }),
      }),
    uploadUrl: (agentId: string, url: string, docName?: string) =>
      request<KBUploadResponse>("/v1/knowledge/upload/url", {
        method: "POST",
        body: JSON.stringify({ agent_id: agentId, url, doc_name: docName }),
      }),
    uploadFile: async (agentId: string, file: File): Promise<KBUploadResponse> => {
      const form = new FormData();
      form.append("agent_id", agentId);
      form.append("file", file);
      const res = await fetch(`${getApiUrl()}/v1/knowledge/upload/file`, {
        method: "POST",
        // No Content-Type header — browser sets multipart/form-data with boundary
        headers: { Authorization: `Bearer ${getKey()}` },
        body: form,
      });
      if (!res.ok) {
        const text = await res.text();
        throw new Error(text || `HTTP ${res.status}`);
      }
      return res.json() as Promise<KBUploadResponse>;
    },
    delete: (agentId: string, docId: string) =>
      request<{ success: boolean }>(`/v1/knowledge/${docId}?agent_id=${agentId}`, {
        method: "DELETE",
      }),
  },

  // ── Context ───────────────────────────────────────────────────────────────
  context: {
    snapshot: (agentId: string, userId: string, query?: string) =>
      request<ContextSnapshot>("/v1/context/snapshot", {
        method: "POST",
        body: JSON.stringify({ agent_id: agentId, user_id: userId, query }),
      }),
  },

  // ── Settings ──────────────────────────────────────────────────────────────
  settings: {
    get: () => request<AppSettings>("/v1/settings"),
    update: (body: SettingsUpdate) =>
      request<AppSettings>("/v1/settings", {
        method: "PUT",
        body: JSON.stringify(body),
      }),
  },

  // ── Health ────────────────────────────────────────────────────────────────
  health: {
    get: () => request<{ status: string; version: string }>("/health"),
  },
};
