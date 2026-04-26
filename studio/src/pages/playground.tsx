import * as React from "react"
import { Link } from "react-router-dom"
import {
  AlertTriangleIcon,
  ArrowUpIcon,
  ArrowRightIcon,
  BotIcon,
  BrainIcon,
  RefreshCwIcon,
  SparklesIcon,
  Trash2Icon,
  UserIcon,
  ZapIcon,
} from "lucide-react"
import { toast } from "sonner"

import { Markdown } from "@/components/markdown"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Textarea } from "@/components/ui/textarea"
import {
  type ChatMessage,
  type ChatResponse,
  type ProvidersResponse,
  api,
  ApiError,
} from "@/lib/api"
import { useApi } from "@/lib/use-api"
import { cn } from "@/lib/utils"

import { MemorySidebar } from "./playground/memory-sidebar"

type ChatTurn =
  | { id: string; kind: "user"; content: string }
  | {
      id: string
      kind: "assistant"
      content: string
      model: string
      usage?: { prompt_tokens: number; completion_tokens: number; total_tokens: number }
      hasContext?: boolean
      recall_ms?: number
      llm_ms?: number
    }
  | {
      id: string
      kind: "context"
      content: string
    }
  | {
      id: string
      kind: "error"
      content: string
      retry: { messages: ChatMessage[] }
    }

const USER_ID_STORAGE = "mw_playground_user_id"

const SAMPLE_PROMPTS = [
  "I prefer dark mode after sunset.",
  "Standups moved to 9:30 AM Tuesdays.",
  "What do I prefer at night?",
  "Where do roadmap docs live?",
]

function loadUserId(): string {
  if (typeof window === "undefined") return "studio-user"
  return window.localStorage.getItem(USER_ID_STORAGE) || "studio-user"
}

function makeId(): string {
  return `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 7)}`
}

function turnsToMessages(turns: ChatTurn[]): ChatMessage[] {
  // The server expects only role/content pairs. Drop context/error rows.
  const out: ChatMessage[] = []
  for (const t of turns) {
    if (t.kind === "user") out.push({ role: "user", content: t.content })
    else if (t.kind === "assistant")
      out.push({ role: "assistant", content: t.content })
  }
  return out
}

function ProviderBanner({
  providers,
  loading,
  error,
}: {
  providers: ProvidersResponse | null
  loading: boolean
  error: ApiError | null
}) {
  if (loading) return null
  if (error) {
    return (
      <Alert variant="destructive" className="mx-4">
        <AlertTriangleIcon />
        <AlertTitle>Could not reach /v1/chat/providers</AlertTitle>
        <AlertDescription>{error.message}</AlertDescription>
      </Alert>
    )
  }
  const openai = providers?.providers?.openai
  if (openai && !openai.configured) {
    return (
      <div className="mx-4">
        <Alert>
          <AlertTriangleIcon />
          <AlertTitle>LLM provider not configured</AlertTitle>
          <AlertDescription>
            <div className="flex flex-col gap-2.5">
              <span>
                Configure a provider from the LLM Provider page, or set{" "}
                <code className="font-mono text-foreground">
                  OPENAI_API_KEY
                </code>{" "}
                on the backend. Memwire still ingests memories without a model —
                chat responses just won't generate.
              </span>
              <div>
                <Button asChild size="sm">
                  <Link to="/setup/llm">
                    Configure provider
                    <ArrowRightIcon />
                  </Link>
                </Button>
              </div>
            </div>
          </AlertDescription>
        </Alert>
      </div>
    )
  }
  return null
}

function MessageBubble({ turn }: { turn: ChatTurn }) {
  if (turn.kind === "user") {
    return (
      <div className="flex justify-end">
        <div className="flex max-w-[78%] gap-2.5">
          <div className="flex flex-col items-end gap-1">
            <div className="rounded-2xl bg-foreground px-3.5 py-2 text-sm leading-relaxed text-background">
              {turn.content}
            </div>
            <span className="text-[10px] text-muted-foreground">you</span>
          </div>
          <span className="mt-0.5 inline-flex size-7 shrink-0 items-center justify-center rounded-full border bg-muted text-muted-foreground">
            <UserIcon className="size-3.5" />
          </span>
        </div>
      </div>
    )
  }

  if (turn.kind === "assistant") {
    return (
      <div className="flex justify-start">
        <div className="flex max-w-[85%] gap-2.5">
          <span className="mt-0.5 inline-flex size-7 shrink-0 items-center justify-center rounded-full border bg-card text-foreground">
            <BotIcon className="size-3.5" />
          </span>
          <div className="flex flex-col items-start gap-1">
            <div className="rounded-2xl border bg-card px-3.5 py-2 text-foreground">
              <Markdown text={turn.content} />
            </div>
            <div className="flex items-center gap-2 text-[10px] text-muted-foreground">
              <span className="font-mono">{turn.model}</span>
              {turn.usage && (
                <>
                  <span>·</span>
                  <span className="tabular-nums">
                    {turn.usage.total_tokens} tok
                  </span>
                </>
              )}
              {typeof turn.recall_ms === "number" && (
                <>
                  <span>·</span>
                  <span className="inline-flex items-center gap-1 tabular-nums">
                    <BrainIcon className="size-2.5" />
                    recall {Math.round(turn.recall_ms)}ms
                  </span>
                </>
              )}
              {typeof turn.llm_ms === "number" && (
                <>
                  <span>·</span>
                  <span className="tabular-nums">
                    LLM {Math.round(turn.llm_ms)}ms
                  </span>
                </>
              )}
              {turn.hasContext && !turn.recall_ms && (
                <>
                  <span>·</span>
                  <span className="inline-flex items-center gap-1">
                    <BrainIcon className="size-2.5" />
                    memory recalled
                  </span>
                </>
              )}
            </div>
          </div>
        </div>
      </div>
    )
  }

  if (turn.kind === "context") {
    return (
      <div className="flex w-full justify-center">
        <div className="flex w-full max-w-full items-start gap-2 rounded-md bg-muted/50 px-3 py-1.5 text-[11px] text-muted-foreground">
          <Badge
            variant="outline"
            className="h-4 shrink-0 px-1.5 font-mono text-[9px] tracking-wide uppercase"
          >
            context
          </Badge>
          <span className="flex-1 leading-relaxed">{turn.content}</span>
        </div>
      </div>
    )
  }

  return (
    <div className="flex justify-start">
      <div className="flex max-w-[85%] gap-2.5">
        <span className="mt-0.5 inline-flex size-7 shrink-0 items-center justify-center rounded-full border border-destructive/40 bg-destructive/10 text-destructive">
          <AlertTriangleIcon className="size-3.5" />
        </span>
        <div className="flex flex-col items-start gap-1.5">
          <div className="rounded-2xl border border-destructive/40 bg-destructive/5 px-3.5 py-2 text-sm text-destructive">
            {turn.content}
          </div>
        </div>
      </div>
    </div>
  )
}

function LoadingBubble() {
  return (
    <div className="flex justify-start">
      <div className="flex max-w-[85%] gap-2.5">
        <span className="mt-0.5 inline-flex size-7 shrink-0 items-center justify-center rounded-full border bg-card text-foreground">
          <BotIcon className="size-3.5" />
        </span>
        <div className="flex h-9 items-center gap-1.5 rounded-2xl border bg-card px-3.5">
          <span className="size-1.5 animate-pulse rounded-full bg-muted-foreground [animation-delay:-0.3s]" />
          <span className="size-1.5 animate-pulse rounded-full bg-muted-foreground [animation-delay:-0.15s]" />
          <span className="size-1.5 animate-pulse rounded-full bg-muted-foreground" />
        </div>
      </div>
    </div>
  )
}

function EmptyChat({
  onPick,
  disabled,
}: {
  onPick: (s: string) => void
  disabled?: boolean
}) {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-4 px-4 py-10 text-center">
      <span className="inline-flex size-12 items-center justify-center rounded-full border bg-card text-foreground">
        <SparklesIcon className="size-5" />
      </span>
      <div className="flex flex-col gap-1">
        <h2 className="text-base font-semibold">Start a conversation</h2>
        <p className="max-w-sm text-xs text-muted-foreground">
          Memwire pulls relevant memories before each response. Try one of these
          to seed the graph.
        </p>
      </div>
      <div className="flex max-w-md flex-wrap justify-center gap-1.5">
        {SAMPLE_PROMPTS.map((p) => (
          <Badge
            key={p}
            asChild
            variant="outline"
            className={cn(
              "cursor-pointer transition-colors",
              disabled
                ? "pointer-events-none opacity-50"
                : "hover:bg-muted hover:text-foreground",
            )}
          >
            <button type="button" onClick={() => onPick(p)} disabled={disabled}>
              {p}
            </button>
          </Badge>
        ))}
      </div>
    </div>
  )
}

export default function PlaygroundPage() {
  const [userId, setUserIdState] = React.useState<string>(() => loadUserId())
  const [pendingUserId, setPendingUserId] = React.useState<string>(() =>
    loadUserId(),
  )
  const [model, setModel] = React.useState<string>("")
  const [turns, setTurns] = React.useState<ChatTurn[]>([])
  const [input, setInput] = React.useState("")
  const [loading, setLoading] = React.useState(false)
  const [unconfigured, setUnconfigured] = React.useState(false)
  const [refreshTick, setRefreshTick] = React.useState(0)

  const scrollRef = React.useRef<HTMLDivElement>(null)
  const textareaRef = React.useRef<HTMLTextAreaElement>(null)

  const providersQuery = useApi<ProvidersResponse>(
    () => api.chatProviders(),
    [],
  )

  const openai = providersQuery.data?.providers?.openai
  const configured = !!openai?.configured
  const availableModels = openai?.available_models ?? []

  // Pick a default model once providers load
  React.useEffect(() => {
    if (!model && openai) {
      setModel(openai.default_model || availableModels[0] || "")
    }
  }, [openai, model, availableModels])

  // Persist userId on commit and reset thread when it changes.
  const commitUserId = React.useCallback(() => {
    const next = pendingUserId.trim() || "studio-user"
    if (next === userId) return
    setUserIdState(next)
    if (typeof window !== "undefined") {
      window.localStorage.setItem(USER_ID_STORAGE, next)
    }
    setTurns([])
    setUnconfigured(false)
  }, [pendingUserId, userId])

  // Auto-scroll on new messages
  React.useEffect(() => {
    const el = scrollRef.current
    if (!el) return
    el.scrollTo({ top: el.scrollHeight, behavior: "smooth" })
  }, [turns, loading])

  // Auto-grow textarea
  React.useEffect(() => {
    const ta = textareaRef.current
    if (!ta) return
    ta.style.height = "auto"
    const max = 180
    ta.style.height = `${Math.min(max, ta.scrollHeight)}px`
  }, [input])

  async function send(messages: ChatMessage[], userTurn: ChatTurn) {
    setLoading(true)
    try {
      const res: ChatResponse = await api.chat({
        user_id: userId,
        messages,
        ...(model ? { model } : {}),
      })
      const recallNote = summarizeRecall(res)
      const next: ChatTurn[] = []
      if (recallNote) {
        next.push({
          id: makeId(),
          kind: "context",
          content: recallNote,
        })
      }
      next.push({
        id: makeId(),
        kind: "assistant",
        content: res.message.content,
        model: res.model,
        usage: res.usage,
        hasContext: !!recallNote,
        recall_ms: res.recall_ms,
        llm_ms: res.llm_ms,
      })
      setTurns((prev) => [...prev, ...next])
      setUnconfigured(false)
      setRefreshTick((n) => n + 1)
    } catch (err) {
      if (err instanceof ApiError && err.status === 503) {
        setUnconfigured(true)
        // remove the optimistic user turn so the user can retry once configured
        setTurns((prev) => prev.filter((t) => t.id !== userTurn.id))
        toast.error("LLM not configured", {
          description: "Set OPENAI_API_KEY on the backend.",
        })
      } else {
        const msg =
          err instanceof ApiError ? err.message : "Chat request failed"
        setTurns((prev) => [
          ...prev,
          {
            id: makeId(),
            kind: "error",
            content: msg,
            retry: { messages },
          },
        ])
      }
    } finally {
      setLoading(false)
    }
  }

  function handleSubmit() {
    const text = input.trim()
    if (!text || loading || !configured) return
    const userTurn: ChatTurn = {
      id: makeId(),
      kind: "user",
      content: text,
    }
    const nextTurns = [...turns, userTurn]
    setTurns(nextTurns)
    setInput("")
    const messages = turnsToMessages(nextTurns)
    void send(messages, userTurn)
  }

  function retry(messages: ChatMessage[], errorTurnId: string) {
    setTurns((prev) => prev.filter((t) => t.id !== errorTurnId))
    const last = messages[messages.length - 1]
    const userTurn: ChatTurn = {
      id: makeId(),
      kind: "user",
      content: last?.content ?? "",
    }
    void send(messages, userTurn)
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (
      (e.metaKey || e.ctrlKey) &&
      (e.key === "Enter" || e.key === "Return")
    ) {
      e.preventDefault()
      handleSubmit()
    }
  }

  const canSend = input.trim().length > 0 && !loading && configured
  const lastUsage = React.useMemo(() => {
    for (let i = turns.length - 1; i >= 0; i--) {
      const t = turns[i]
      if (t.kind === "assistant" && t.usage) return t.usage
    }
    return null
  }, [turns])
  const lastTiming = React.useMemo(() => {
    for (let i = turns.length - 1; i >= 0; i--) {
      const t = turns[i]
      if (
        t.kind === "assistant" &&
        (typeof t.recall_ms === "number" || typeof t.llm_ms === "number")
      ) {
        return { recall_ms: t.recall_ms, llm_ms: t.llm_ms }
      }
    }
    return null
  }, [turns])

  return (
    <div className="flex flex-col gap-4 py-6">
      <div className="flex flex-col gap-1 px-4">
        <h1 className="text-2xl font-semibold tracking-tight">Playground</h1>
        <p className="text-sm text-muted-foreground">
          Chat with your Memwire-backed agent. Memories build up live in the
          sidebar.
        </p>
      </div>

      <div className="flex flex-wrap items-end gap-3 px-4">
        <div className="flex min-w-[180px] flex-1 flex-col gap-1.5 sm:max-w-[220px]">
          <Label htmlFor="user-id" className="text-xs text-muted-foreground">
            user_id
          </Label>
          <Input
            id="user-id"
            value={pendingUserId}
            onChange={(e) => setPendingUserId(e.target.value)}
            onBlur={commitUserId}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault()
                commitUserId()
              }
            }}
            placeholder="studio-user"
            className="h-8 font-mono text-xs"
          />
        </div>
        <div className="flex min-w-[200px] flex-1 flex-col gap-1.5 sm:max-w-[280px]">
          <Label htmlFor="model" className="text-xs text-muted-foreground">
            model
          </Label>
          <Select
            value={model}
            onValueChange={setModel}
            disabled={!configured || availableModels.length === 0}
          >
            <SelectTrigger id="model" className="h-8 w-full text-xs">
              <SelectValue placeholder="Select a model" />
            </SelectTrigger>
            <SelectContent>
              {availableModels.map((m) => (
                <SelectItem key={m} value={m} className="font-mono text-xs">
                  {m}
                </SelectItem>
              ))}
              {availableModels.length === 0 && (
                <SelectItem value="__none" disabled>
                  No models
                </SelectItem>
              )}
            </SelectContent>
          </Select>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => {
            setTurns([])
            toast.success("Thread cleared", {
              description: "Server-side memories are unaffected.",
            })
          }}
          disabled={turns.length === 0}
        >
          <Trash2Icon />
          Clear thread
        </Button>
      </div>

      <ProviderBanner
        providers={providersQuery.data}
        loading={providersQuery.loading}
        error={providersQuery.error}
      />

      <div className="grid gap-4 px-4 lg:grid-cols-5">
        <div className="flex min-h-[640px] flex-col overflow-hidden rounded-xl border bg-card lg:col-span-3 lg:min-h-[680px]">
          <div className="flex items-center justify-between gap-2 border-b bg-muted/30 px-4 py-2">
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <ZapIcon className="size-3.5" />
              <span className="font-mono">{model || "no model"}</span>
              {lastUsage && (
                <>
                  <span>·</span>
                  <span className="tabular-nums">
                    {lastUsage.total_tokens} tokens
                  </span>
                </>
              )}
              {lastTiming && typeof lastTiming.recall_ms === "number" && (
                <>
                  <span>·</span>
                  <span className="inline-flex items-center gap-1 tabular-nums">
                    <BrainIcon className="size-3" />
                    recall {Math.round(lastTiming.recall_ms)}ms
                  </span>
                </>
              )}
              {lastTiming && typeof lastTiming.llm_ms === "number" && (
                <>
                  <span>·</span>
                  <span className="tabular-nums">
                    LLM {Math.round(lastTiming.llm_ms)}ms
                  </span>
                </>
              )}
            </div>
            <Badge variant="outline" className="font-mono text-[10px]">
              POST /v1/chat
            </Badge>
          </div>

          <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-4">
            {turns.length === 0 && !loading ? (
              <EmptyChat onPick={setInput} disabled={!configured} />
            ) : (
              <div className="space-y-3">
                {turns.map((t) =>
                  t.kind === "error" ? (
                    <div key={t.id} className="space-y-1.5">
                      <MessageBubble turn={t} />
                      <div className="flex justify-start pl-9">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => retry(t.retry.messages, t.id)}
                        >
                          <RefreshCwIcon />
                          Retry
                        </Button>
                      </div>
                    </div>
                  ) : (
                    <MessageBubble key={t.id} turn={t} />
                  ),
                )}
                {loading && <LoadingBubble />}
              </div>
            )}
          </div>

          {unconfigured && (
            <div className="border-t border-destructive/30 bg-destructive/5 px-4 py-2 text-xs text-destructive">
              <span className="inline-flex items-center gap-1.5">
                <AlertTriangleIcon className="size-3.5" />
                LLM not configured. Set{" "}
                <code className="font-mono">OPENAI_API_KEY</code> on the
                backend.
              </span>
            </div>
          )}

          <div className="border-t bg-background p-3">
            <div className="relative flex items-end gap-2 rounded-xl border bg-card focus-within:ring-2 focus-within:ring-ring/40">
              <Textarea
                ref={textareaRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                rows={2}
                placeholder={
                  configured
                    ? "Send a message — Cmd/Ctrl+Enter to send"
                    : "LLM not configured"
                }
                disabled={!configured}
                className="min-h-[44px] resize-none border-0 bg-transparent px-3.5 py-2.5 text-sm shadow-none focus-visible:ring-0"
              />
              <div className="flex items-center gap-1.5 px-2 pb-2">
                <Button
                  type="button"
                  size="icon-sm"
                  onClick={handleSubmit}
                  disabled={!canSend}
                  aria-label="Send message"
                >
                  <ArrowUpIcon />
                </Button>
              </div>
            </div>
            <div className="mt-1.5 flex items-center justify-between px-1 text-[10px] text-muted-foreground">
              <span>
                Cmd/Ctrl+Enter to send · memories indexed for{" "}
                <code className="font-mono">{userId}</code>
              </span>
              {turns.length > 0 && (
                <span className="tabular-nums">
                  {turns.filter((t) => t.kind === "user" || t.kind === "assistant").length}{" "}
                  msgs
                </span>
              )}
            </div>
          </div>
        </div>

        <div className="lg:col-span-2">
          <MemorySidebar userId={userId} refreshTick={refreshTick} />
        </div>
      </div>
    </div>
  )
}

function summarizeRecall(res: ChatResponse): string | null {
  const supporting = res.recall?.supporting?.length ?? 0
  const conflicting = res.recall?.conflicting?.length ?? 0
  const knowledge = res.recall?.knowledge?.length ?? 0
  if (supporting + conflicting + knowledge === 0) return null
  const parts: string[] = []
  if (supporting > 0) {
    parts.push(`${supporting} supporting path${supporting === 1 ? "" : "s"}`)
  }
  if (conflicting > 0) {
    parts.push(
      `${conflicting} conflicting path${conflicting === 1 ? "" : "s"}`,
    )
  }
  if (knowledge > 0) {
    parts.push(`${knowledge} knowledge chunk${knowledge === 1 ? "" : "s"}`)
  }
  return `Recalled ${parts.join(", ")} for "${res.recall.query.slice(0, 60)}${res.recall.query.length > 60 ? "…" : ""}"`
}
