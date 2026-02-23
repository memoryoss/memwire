import { Brain, BookOpen, KeyRound } from "lucide-react";

const CODE_SNIPPET = `// 1. Store a conversation turn
await fetch("/v1/memory/store", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
    "Authorization": "Bearer mw_your_api_key",
  },
  body: JSON.stringify({
    agent_id:          "my-agent",
    user_id:           "user-123",
    user_message:      "I prefer dark mode and concise answers.",
    assistant_message: "Got it! I'll keep that in mind.",
  }),
});

// 2. Retrieve memories for an agent (optionally scoped to a user)
const res = await fetch(
  "/v1/memory/retrieve?agent_id=my-agent&user_id=user-123",
  { headers: { "Authorization": "Bearer mw_your_api_key" } }
).then(r => r.json());
// res.memories → [{ id, memory, topics, user_id, timestamp }, ...]

// 3. Build a memory-aware system prompt
const facts = res.memories.map(m => m.memory).join("\\n");
const systemPrompt = "Known user preferences:\\n" + facts; // inject into LLM ✅`;

function StatCard({
  icon: Icon,
  label,
  value,
}: {
  icon: React.ElementType;
  label: string;
  value: string | number;
}) {
  return (
    <div className="rounded-lg border bg-card px-5 py-4 flex items-center gap-4">
      <div className="p-2 rounded-md bg-primary/10">
        <Icon className="h-5 w-5 text-primary" />
      </div>
      <div>
        <p className="text-xs text-muted-foreground">{label}</p>
        <p className="text-2xl font-semibold">{value}</p>
      </div>
    </div>
  );
}

export default function Dashboard() {
  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold">Dashboard</h1>
        <p className="text-muted-foreground text-sm mt-1">
          Memory infrastructure for your AI application
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        <StatCard icon={Brain} label="Memory Turns" value="—" />
        <StatCard icon={BookOpen} label="KB Documents" value="—" />
        <StatCard icon={KeyRound} label="API Keys" value="—" />
      </div>

      {/* Quick start */}
      <div>
        <h2 className="text-base font-medium mb-3">Quick Start</h2>
        <pre className="rounded-lg border bg-muted p-4 text-xs overflow-x-auto text-muted-foreground leading-5">
          {CODE_SNIPPET}
        </pre>
      </div>

    </div>
  );
}
