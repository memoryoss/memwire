import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import { Brain, Search, Trash2, Tag } from "lucide-react";

export default function Memory() {
  const [agentId, setAgentId] = useState("");
  const [userId, setUserId] = useState("");
  const [search, setSearch] = useState("");
  const qc = useQueryClient();

  const listKey = ["memory", "list", agentId, userId];

  const { data, isLoading } = useQuery({
    queryKey: listKey,
    queryFn: () => api.memory.list(agentId || undefined, userId || undefined),
  });

  const clearMut = useMutation({
    mutationFn: () => api.memory.clear(agentId, userId),
    onSuccess: () => qc.invalidateQueries({ queryKey: listKey }),
  });

  const memories = data?.memories ?? [];

  const filtered = memories.filter(
    (m) =>
      !search ||
      m.memory.toLowerCase().includes(search.toLowerCase()) ||
      m.topics.some((t) => t.toLowerCase().includes(search.toLowerCase()))
  );

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Memory</h1>
        <p className="text-muted-foreground text-sm mt-1">
          Browse conversation memory · powered by Agno MemoryManager
        </p>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <input
          className="rounded-md border px-3 py-1.5 text-sm bg-background focus:outline-none w-52"
          placeholder="Agent ID (optional)"
          value={agentId}
          onChange={(e) => setAgentId(e.target.value)}
        />
        <input
          className="rounded-md border px-3 py-1.5 text-sm bg-background focus:outline-none w-52"
          placeholder="User ID (optional)"
          value={userId}
          onChange={(e) => setUserId(e.target.value)}
        />
        <div className="flex items-center gap-2 border rounded-md px-3 py-1.5 flex-1 min-w-48">
          <Search className="h-4 w-4 text-muted-foreground" />
          <input
            className="text-sm bg-transparent focus:outline-none flex-1"
            placeholder="Filter memories or topics…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        {agentId && userId && (
          <button
            onClick={() => {
              if (confirm("Clear all memories for this user?")) clearMut.mutate();
            }}
            disabled={clearMut.isPending}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-md border border-destructive text-destructive hover:bg-destructive/10 disabled:opacity-50"
          >
            <Trash2 className="h-3.5 w-3.5" />
            {clearMut.isPending ? "Clearing…" : "Clear"}
          </button>
        )}
      </div>

      {/* Memory list */}
      {isLoading ? (
        <p className="text-sm text-muted-foreground">Loading…</p>
      ) : memories.length === 0 ? (
        <div className="rounded-lg border border-dashed px-6 py-10 text-center">
          <Brain className="h-8 w-8 text-muted-foreground mx-auto mb-2" />
          <p className="text-sm text-muted-foreground">No memories found.</p>
        </div>
      ) : filtered.length === 0 ? (
        <p className="text-sm text-muted-foreground">No memories match your filter.</p>
      ) : (
        <div className="space-y-3">
          <p className="text-xs text-muted-foreground">
            {filtered.length} of {memories.length} memories
          </p>
          {filtered.map((mem) => (
            <div
              key={mem.id}
              className="rounded-lg border bg-card px-4 py-3 text-sm space-y-2"
            >
              <div className="flex items-start gap-2">
                <Brain className="h-4 w-4 text-primary mt-0.5 shrink-0" />
                <p className="leading-relaxed flex-1">{mem.memory}</p>
                <div className="flex flex-col items-end gap-0.5 shrink-0">
                  {mem.user_id && (
                    <span className="text-xs text-muted-foreground">{mem.user_id}</span>
                  )}
                  {mem.timestamp && (
                    <span className="text-xs text-muted-foreground whitespace-nowrap">
                      {formatDate(mem.timestamp)}
                    </span>
                  )}
                </div>
              </div>

              {mem.topics && mem.topics.length > 0 && (
                <div className="flex flex-wrap items-center gap-1.5 pl-6">
                  <Tag className="h-3 w-3 text-muted-foreground" />
                  {mem.topics.map((topic) => (
                    <span
                      key={topic}
                      className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-primary/10 text-primary"
                    >
                      {topic}
                    </span>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
