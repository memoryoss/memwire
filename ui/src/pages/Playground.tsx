import { useState, useRef, useEffect } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Send, Brain, RefreshCw, Trash2, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";

interface ChatMessage {
  role: "user" | "assistant" | "system";
  content: string;
}

const DEFAULT_AGENT = "playground";
const DEFAULT_USER = "demo-user";
const ASSISTANT_ACK = "Got it — I'll keep that in mind.";

export default function Playground() {
  const [agentId, setAgentId] = useState(DEFAULT_AGENT);
  const [userId, setUserId] = useState(DEFAULT_USER);
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: "system",
      content:
        "Send messages with personal preferences, facts, or context — watch Agno extract memories in real time.",
    },
  ]);
  const bottomRef = useRef<HTMLDivElement>(null);
  const qc = useQueryClient();

  const memKey = ["playground-memories", agentId, userId];

  const { data: memData, isLoading: memLoading } = useQuery({
    queryKey: memKey,
    queryFn: () => api.memory.retrieve(agentId, userId, 50),
    enabled: Boolean(agentId),
    refetchInterval: false,
  });

  const storeMut = useMutation({
    mutationFn: ({
      userMsg,
      assistantMsg,
    }: {
      userMsg: string;
      assistantMsg: string;
    }) => api.memory.store(agentId, userId, userMsg, assistantMsg),
    onSuccess: () => qc.invalidateQueries({ queryKey: memKey }),
  });

  const clearMut = useMutation({
    mutationFn: () => api.memory.clear(agentId, userId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: memKey });
      setMessages([
        {
          role: "system",
          content: "Memory cleared. Start a fresh conversation.",
        },
      ]);
    },
  });

  const handleSend = () => {
    const text = input.trim();
    if (!text || !agentId || !userId || storeMut.isPending) return;
    setInput("");

    setMessages((prev) => [
      ...prev,
      { role: "user", content: text },
      { role: "assistant", content: ASSISTANT_ACK },
    ]);

    storeMut.mutate({ userMsg: text, assistantMsg: ASSISTANT_ACK });
  };

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, storeMut.isPending]);

  const memories = memData?.memories ?? [];
  const ready = Boolean(agentId && userId);

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)] gap-4 overflow-hidden">
      {/* Header */}
      <div className="shrink-0">
        <h1 className="text-2xl font-semibold flex items-center gap-2">
          <Sparkles className="h-5 w-5 text-primary" />
          Playground
        </h1>
        <p className="text-muted-foreground text-sm mt-1">
          Chat and watch MemWire extract memories in real time
        </p>
      </div>

      {/* Config bar */}
      <div className="shrink-0 flex flex-wrap gap-2 items-center">
        <input
          className="rounded-md border px-3 py-1.5 text-sm bg-background focus:outline-none w-44"
          placeholder="Agent ID"
          value={agentId}
          onChange={(e) => setAgentId(e.target.value)}
        />
        <input
          className="rounded-md border px-3 py-1.5 text-sm bg-background focus:outline-none w-44"
          placeholder="User ID"
          value={userId}
          onChange={(e) => setUserId(e.target.value)}
        />
        <button
          onClick={() => qc.invalidateQueries({ queryKey: memKey })}
          className="flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-md border hover:bg-accent transition-colors"
          title="Refresh memories"
        >
          <RefreshCw className="h-3.5 w-3.5" />
          Refresh
        </button>
        <button
          onClick={() => clearMut.mutate()}
          disabled={clearMut.isPending || !ready}
          className="flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-md border border-destructive text-destructive hover:bg-destructive/10 disabled:opacity-40 transition-colors"
        >
          <Trash2 className="h-3.5 w-3.5" />
          {clearMut.isPending ? "Clearing…" : "Clear Memory"}
        </button>
      </div>

      {/* Main split — fills remaining height */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-2 gap-4 min-h-0">
        {/* ── Chat panel ── */}
        <div className="rounded-lg border bg-card flex flex-col min-h-0">
          <div className="px-4 py-3 border-b text-sm font-medium shrink-0">
            Conversation
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            {messages.map((m, i) => {
              if (m.role === "system") {
                return (
                  <p
                    key={i}
                    className="text-center text-xs text-muted-foreground py-4"
                  >
                    {m.content}
                  </p>
                );
              }
              return (
                <div
                  key={i}
                  className={cn(
                    "flex",
                    m.role === "user" ? "justify-end" : "justify-start"
                  )}
                >
                  <div
                    className={cn(
                      "max-w-[75%] rounded-2xl px-4 py-2 text-sm leading-relaxed",
                      m.role === "user"
                        ? "bg-primary text-primary-foreground rounded-br-sm"
                        : "bg-muted text-foreground rounded-bl-sm"
                    )}
                  >
                    {m.content}
                  </div>
                </div>
              );
            })}

            {storeMut.isPending && (
              <div className="flex justify-start">
                <div className="bg-muted rounded-2xl rounded-bl-sm px-4 py-2 text-sm text-muted-foreground animate-pulse">
                  Storing memory…
                </div>
              </div>
            )}

            <div ref={bottomRef} />
          </div>

          {/* Input */}
          <div className="shrink-0 border-t p-3">
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleSend();
              }}
              className="flex gap-2"
            >
              <input
                className="flex-1 rounded-md border px-3 py-2 text-sm bg-background focus:outline-none disabled:opacity-50"
                placeholder={
                  ready
                    ? "Type a message with preferences, facts, context…"
                    : "Set Agent ID and User ID first"
                }
                value={input}
                onChange={(e) => setInput(e.target.value)}
                disabled={!ready || storeMut.isPending}
                autoFocus
              />
              <button
                type="submit"
                disabled={!input.trim() || !ready || storeMut.isPending}
                className="p-2 rounded-md bg-primary text-primary-foreground disabled:opacity-40 hover:bg-primary/90 transition-colors"
              >
                <Send className="h-4 w-4" />
              </button>
            </form>
          </div>
        </div>

        {/* ── Memories panel ── */}
        <div className="rounded-lg border bg-card flex flex-col min-h-0">
          <div className="px-4 py-3 border-b flex items-center justify-between shrink-0">
            <span className="text-sm font-medium flex items-center gap-2">
              <Brain className="h-4 w-4 text-primary" />
              Extracted Memories
            </span>
            <span className="text-xs text-muted-foreground">
              {memLoading ? (
                <span className="animate-pulse">Loading…</span>
              ) : (
                `${memories.length} fact${memories.length !== 1 ? "s" : ""}`
              )}
            </span>
          </div>

          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            {!memLoading && memories.length === 0 && (
              <div className="flex flex-col items-center justify-center h-full text-center gap-3 py-8">
                <Brain className="h-10 w-10 text-muted-foreground/30" />
                <div>
                  <p className="text-sm text-muted-foreground font-medium">
                    No memories yet
                  </p>
                  <p className="text-xs text-muted-foreground mt-1 max-w-xs">
                    Send messages with personal preferences, habits, or facts —
                    Agno will extract and store them here automatically.
                  </p>
                </div>
                <div className="text-xs text-muted-foreground bg-muted rounded-md p-3 text-left max-w-xs space-y-1 mt-2">
                  <p className="font-medium mb-1">Try sending:</p>
                  <p>• "I prefer dark mode and concise answers"</p>
                  <p>• "My name is Alex and I work in Python"</p>
                  <p>• "I'm vegetarian and live in Berlin"</p>
                </div>
              </div>
            )}

            {memories.map((m) => (
              <div
                key={m.id}
                className="rounded-lg border bg-muted/40 p-3 space-y-2"
              >
                <p className="text-sm leading-relaxed">{m.memory}</p>
                {m.topics?.length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {m.topics.map((t) => (
                      <span
                        key={t}
                        className="inline-flex items-center px-1.5 py-0.5 rounded text-xs bg-primary/10 text-primary font-medium"
                      >
                        {t}
                      </span>
                    ))}
                  </div>
                )}
                {m.timestamp && (
                  <p className="text-xs text-muted-foreground">
                    {new Date(m.timestamp).toLocaleTimeString([], {
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
