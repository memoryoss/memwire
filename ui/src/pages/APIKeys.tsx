import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, type APIKey, type APIKeyCreated } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import { KeyRound, Plus, Trash2, Copy, Eye } from "lucide-react";

function CreatedKeyBanner({ apiKey }: { apiKey: APIKeyCreated }) {
  const [copied, setCopied] = useState(false);
  const copy = () => {
    navigator.clipboard.writeText(apiKey.key);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  return (
    <div className="rounded-lg border border-primary/30 bg-primary/5 p-4 space-y-2">
      <p className="text-sm font-medium text-primary">
        API key created — copy it now, it won't be shown again.
      </p>
      <div className="flex items-center gap-2">
        <code className="flex-1 rounded bg-muted px-2 py-1 text-xs font-mono break-all">
          {apiKey.key}
        </code>
        <button
          onClick={copy}
          className="p-1.5 rounded hover:bg-primary/10"
          title="Copy"
        >
          {copied ? (
            <Eye className="h-4 w-4 text-primary" />
          ) : (
            <Copy className="h-4 w-4 text-primary" />
          )}
        </button>
      </div>
    </div>
  );
}

export default function APIKeys() {
  const qc = useQueryClient();
  const agentId = "default";
  const [keyName, setKeyName] = useState("");
  const [newKey, setNewKey] = useState<APIKeyCreated | null>(null);

  const keysKey = ["api-keys", agentId];
  const { data: keys = [], isLoading } = useQuery<APIKey[]>({
    queryKey: keysKey,
    queryFn: () => api.apiKeys.list(agentId),
  });

  const createMut = useMutation({
    mutationFn: () => api.apiKeys.create(agentId, keyName),
    onSuccess: (created) => {
      qc.invalidateQueries({ queryKey: keysKey });
      setNewKey(created);
      setKeyName("");
    },
  });

  const deleteMut = useMutation({
    mutationFn: (id: string) => api.apiKeys.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: keysKey }),
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">API Keys</h1>
        <p className="text-muted-foreground text-sm mt-1">
          Create and manage API keys
        </p>
      </div>

      {/* New key banner */}
          {newKey && <CreatedKeyBanner apiKey={newKey} />}

          {/* Create form */}
          <div className="flex gap-2 items-center">
            <input
              className="rounded-md border px-3 py-1.5 text-sm bg-background focus:outline-none flex-1 max-w-xs"
              placeholder="Key name (e.g. production)"
              value={keyName}
              onChange={(e) => setKeyName(e.target.value)}
            />
            <button
              disabled={!keyName.trim()}
              onClick={() => createMut.mutate()}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-md bg-primary text-primary-foreground disabled:opacity-50"
            >
              <Plus className="h-3.5 w-3.5" /> Create Key
            </button>
          </div>

          {/* Keys list */}
          {isLoading ? (
            <p className="text-sm text-muted-foreground">Loading…</p>
          ) : keys.length === 0 ? (
            <div className="rounded-lg border border-dashed px-6 py-10 text-center">
              <KeyRound className="h-8 w-8 text-muted-foreground mx-auto mb-2" />
              <p className="text-sm text-muted-foreground">No API keys yet.</p>
            </div>
          ) : (
            <div className="rounded-lg border divide-y">
              {keys.map((k) => (
                <div
                  key={k.id}
                  className="flex items-center gap-3 px-4 py-3"
                >
                  <KeyRound className="h-4 w-4 text-muted-foreground shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium">{k.name}</p>
                    <p className="text-xs text-muted-foreground font-mono">
                      {k.prefix}•••••
                    </p>
                  </div>
                  <div className="text-xs text-muted-foreground hidden md:block">
                    {k.last_used_at
                      ? `Last used ${formatDate(k.last_used_at)}`
                      : "Never used"}
                  </div>
                  <button
                    onClick={() => {
                      if (confirm(`Revoke key "${k.name}"?`))
                        deleteMut.mutate(k.id);
                    }}
                    className="p-1.5 rounded hover:bg-destructive/10"
                  >
                    <Trash2 className="h-3.5 w-3.5 text-destructive" />
                  </button>
                </div>
              ))}
            </div>
          )}
    </div>
  );
}
