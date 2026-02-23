import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api, type Agent } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import { MessageSquare, User } from "lucide-react";

export default function Sessions() {
  const [agentId, setAgentId] = useState("");
  const [userId, setUserId] = useState("");

  const { data: agents = [] } = useQuery({
    queryKey: ["agents"],
    queryFn: () => api.agents.list(),
  });

  const { data: history, isLoading } = useQuery({
    queryKey: ["sessions", agentId, userId],
    queryFn: () => api.memory.history(agentId, userId, 100),
    enabled: !!agentId && !!userId,
  });

  const turns = history?.turns ?? [];

  // Group turns into sessions by rough time gap (>30 min = new session)
  const sessions: typeof turns[] = [];
  let current: typeof turns = [];
  for (let i = 0; i < turns.length; i++) {
    if (i === 0) {
      current.push(turns[i]);
    } else {
      const gap =
        new Date(turns[i].created_at).getTime() -
        new Date(turns[i - 1].created_at).getTime();
      if (gap > 30 * 60 * 1000) {
        sessions.push(current);
        current = [];
      }
      current.push(turns[i]);
    }
  }
  if (current.length > 0) sessions.push(current);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Sessions</h1>
        <p className="text-muted-foreground text-sm mt-1">
          View conversation sessions grouped by inactivity gaps
        </p>
      </div>

      <div className="flex flex-wrap gap-3">
        <select
          className="rounded-md border px-3 py-1.5 text-sm bg-background focus:outline-none"
          value={agentId}
          onChange={(e) => setAgentId(e.target.value)}
        >
          <option value="">Select agent…</option>
          {agents.map((a: Agent) => (
            <option key={a.id} value={a.id}>
              {a.name}
            </option>
          ))}
        </select>
        <input
          className="rounded-md border px-3 py-1.5 text-sm bg-background focus:outline-none w-48"
          placeholder="User ID"
          value={userId}
          onChange={(e) => setUserId(e.target.value)}
        />
      </div>

      {!agentId || !userId ? (
        <div className="rounded-lg border border-dashed px-6 py-10 text-center">
          <MessageSquare className="h-8 w-8 text-muted-foreground mx-auto mb-2" />
          <p className="text-sm text-muted-foreground">
            Select an agent and enter a user ID to view sessions.
          </p>
        </div>
      ) : isLoading ? (
        <p className="text-sm text-muted-foreground">Loading…</p>
      ) : sessions.length === 0 ? (
        <p className="text-sm text-muted-foreground">No sessions found.</p>
      ) : (
        <div className="space-y-4">
          {sessions.map((session, si) => (
            <details key={si} className="rounded-lg border" open={si === sessions.length - 1}>
              <summary className="flex items-center gap-3 px-4 py-3 cursor-pointer select-none">
                <MessageSquare className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm font-medium">
                  Session {si + 1}
                </span>
                <span className="text-xs text-muted-foreground ml-auto">
                  {session.length} turns ·{" "}
                  {formatDate(session[0].created_at)}
                </span>
              </summary>
              <div className="border-t divide-y">
                {session.map((turn, ti) => (
                  <div key={ti} className="px-4 py-3 flex gap-3">
                    <User
                      className={`h-3.5 w-3.5 mt-0.5 shrink-0 ${
                        turn.role === "user"
                          ? "text-primary"
                          : "text-muted-foreground"
                      }`}
                    />
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-medium capitalize mb-0.5">
                        {turn.role}
                      </p>
                      <p className="text-sm leading-relaxed">{turn.content}</p>
                    </div>
                  </div>
                ))}
              </div>
            </details>
          ))}
        </div>
      )}
    </div>
  );
}
