import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, type Agent, type AgentCreate } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import { Bot, Plus, Trash2, Pencil } from "lucide-react";

function AgentForm({
  initial,
  onSave,
  onCancel,
}: {
  initial?: Partial<AgentCreate>;
  onSave: (v: AgentCreate) => void;
  onCancel: () => void;
}) {
  const [name, setName] = useState(initial?.name ?? "");
  const [desc, setDesc] = useState(initial?.description ?? "");
  const [prompt, setPrompt] = useState(initial?.system_prompt ?? "");

  return (
    <div className="rounded-lg border p-4 space-y-3 bg-card">
      <div className="space-y-1">
        <label className="text-xs font-medium">Name *</label>
        <input
          className="w-full rounded-md border px-3 py-1.5 text-sm bg-background focus:outline-none focus:ring-2 focus:ring-primary"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="My Agent"
        />
      </div>
      <div className="space-y-1">
        <label className="text-xs font-medium">Description</label>
        <input
          className="w-full rounded-md border px-3 py-1.5 text-sm bg-background focus:outline-none focus:ring-2 focus:ring-primary"
          value={desc}
          onChange={(e) => setDesc(e.target.value)}
          placeholder="What does this agent do?"
        />
      </div>
      <div className="space-y-1">
        <label className="text-xs font-medium">System Prompt</label>
        <textarea
          rows={3}
          className="w-full rounded-md border px-3 py-1.5 text-sm bg-background focus:outline-none focus:ring-2 focus:ring-primary resize-none"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="You are a helpful assistant..."
        />
      </div>
      <div className="flex gap-2 justify-end">
        <button
          onClick={onCancel}
          className="px-3 py-1.5 text-sm rounded-md border hover:bg-accent"
        >
          Cancel
        </button>
        <button
          disabled={!name.trim()}
          onClick={() =>
            onSave({ name, description: desc, system_prompt: prompt })
          }
          className="px-3 py-1.5 text-sm rounded-md bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
        >
          Save
        </button>
      </div>
    </div>
  );
}

export default function Agents() {
  const qc = useQueryClient();
  const [creating, setCreating] = useState(false);
  const [editing, setEditing] = useState<Agent | null>(null);

  const { data: agents = [], isLoading } = useQuery({
    queryKey: ["agents"],
    queryFn: () => api.agents.list(),
  });

  const createMut = useMutation({
    mutationFn: (body: AgentCreate) => api.agents.create(body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["agents"] });
      setCreating(false);
    },
  });

  const updateMut = useMutation({
    mutationFn: ({ id, body }: { id: string; body: Partial<AgentCreate> }) =>
      api.agents.update(id, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["agents"] });
      setEditing(null);
    },
  });

  const deleteMut = useMutation({
    mutationFn: (id: string) => api.agents.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["agents"] }),
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Agents</h1>
          <p className="text-muted-foreground text-sm mt-1">
            Manage your memory-enabled AI agents
          </p>
        </div>
        <button
          onClick={() => setCreating(true)}
          className="flex items-center gap-2 px-3 py-1.5 text-sm rounded-md bg-primary text-primary-foreground hover:bg-primary/90"
        >
          <Plus className="h-4 w-4" /> New Agent
        </button>
      </div>

      {creating && (
        <AgentForm
          onSave={(v) => createMut.mutate(v)}
          onCancel={() => setCreating(false)}
        />
      )}

      {isLoading && (
        <p className="text-sm text-muted-foreground">Loading…</p>
      )}

      {!isLoading && agents.length === 0 && !creating && (
        <div className="rounded-lg border border-dashed px-6 py-10 text-center">
          <Bot className="h-8 w-8 text-muted-foreground mx-auto mb-2" />
          <p className="text-sm text-muted-foreground">No agents yet.</p>
        </div>
      )}

      <div className="rounded-lg border divide-y">
        {agents.map((agent) => (
          <div key={agent.id}>
            {editing?.id === agent.id ? (
              <div className="p-4">
                <AgentForm
                  initial={agent}
                  onSave={(v) => updateMut.mutate({ id: agent.id, body: v })}
                  onCancel={() => setEditing(null)}
                />
              </div>
            ) : (
              <div className="flex items-center gap-3 px-4 py-3">
                <Bot className="h-4 w-4 text-muted-foreground shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium">{agent.name}</p>
                  <p className="text-xs text-muted-foreground font-mono">
                    {agent.id}
                  </p>
                  {agent.description && (
                    <p className="text-xs text-muted-foreground mt-0.5">
                      {agent.description}
                    </p>
                  )}
                </div>
                <span className="text-xs text-muted-foreground hidden md:block">
                  {formatDate(agent.created_at)}
                </span>
                <button
                  onClick={() => setEditing(agent)}
                  className="p-1.5 rounded hover:bg-accent"
                >
                  <Pencil className="h-3.5 w-3.5 text-muted-foreground" />
                </button>
                <button
                  onClick={() => {
                    if (confirm(`Delete agent "${agent.name}"?`))
                      deleteMut.mutate(agent.id);
                  }}
                  className="p-1.5 rounded hover:bg-destructive/10"
                >
                  <Trash2 className="h-3.5 w-3.5 text-destructive" />
                </button>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
