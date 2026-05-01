import * as React from "react"
import {
  CheckCircle2Icon,
  CheckIcon,
  CircleSlashIcon,
  CpuIcon,
  EyeIcon,
  EyeOffIcon,
  Loader2Icon,
  LockIcon,
  PlugIcon,
  PlugZapIcon,
  RotateCcwIcon,
  SaveIcon,
  ShieldAlertIcon,
  SlidersHorizontalIcon,
  Trash2Icon,
  UnplugIcon,
  XCircleIcon,
} from "lucide-react"
import { toast } from "sonner"

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Skeleton } from "@/components/ui/skeleton"
import {
  ApiError,
  api,
  type LLMConfigResponse,
  type LLMTestResponse,
} from "@/lib/api"
import { useApi } from "@/lib/use-api"
import { cn } from "@/lib/utils"

type Preset = {
  id: string
  label: string
  base_url: string
  default_model: string
  available_models: string[]
  hint?: string
}

const PRESETS: Preset[] = [
  {
    id: "openai",
    label: "OpenAI",
    base_url: "https://api.openai.com/v1",
    default_model: "gpt-4o-mini",
    available_models: ["gpt-4o-mini", "gpt-4o"],
  },
  {
    id: "ollama",
    label: "Ollama",
    base_url: "http://host.docker.internal:11434/v1",
    default_model: "llama3.2",
    available_models: ["llama3.2", "qwen2.5", "mistral"],
    hint: "Use host.docker.internal only when calling Ollama from inside Docker; use http://localhost:11434/v1 from the host.",
  },
  {
    id: "together",
    label: "Together",
    base_url: "https://api.together.xyz/v1",
    default_model: "meta-llama/Llama-3-8b-chat-hf",
    available_models: ["meta-llama/Llama-3-8b-chat-hf"],
  },
  {
    id: "groq",
    label: "Groq",
    base_url: "https://api.groq.com/openai/v1",
    default_model: "llama-3.1-8b-instant",
    available_models: ["llama-3.1-8b-instant", "llama-3.3-70b-versatile"],
  },
  {
    id: "custom",
    label: "Custom",
    base_url: "",
    default_model: "",
    available_models: [],
  },
]

type DraftState = {
  api_key: string
  base_url: string
  default_model: string
  available_models: string
}

function parseModels(raw: string): string[] {
  return raw
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean)
}

function configToDraft(cfg: LLMConfigResponse | null): DraftState {
  if (!cfg) {
    return { api_key: "", base_url: "", default_model: "", available_models: "" }
  }
  return {
    api_key: "",
    base_url: cfg.base_url ?? "",
    default_model: cfg.default_model ?? "",
    available_models: (cfg.available_models ?? []).join(", "),
  }
}

function StatPill({
  label,
  value,
  mono,
}: {
  label: string
  value: string
  mono?: boolean
}) {
  return (
    <div className="flex flex-col gap-0.5 rounded-md border bg-muted/40 px-2.5 py-1.5">
      <span className="text-[11px] text-muted-foreground">{label}</span>
      <span
        className={cn(
          "truncate text-xs font-medium tabular-nums",
          mono && "font-mono",
        )}
        title={value}
      >
        {value}
      </span>
    </div>
  )
}

function StatusCard({ cfg }: { cfg: LLMConfigResponse }) {
  const source = cfg.env_locked ? "env" : cfg.configured ? "ui" : "—"
  const keyMasked =
    cfg.api_key_prefix && cfg.api_key_suffix
      ? `${cfg.api_key_prefix}…${cfg.api_key_suffix}`
      : null

  let pill: React.ReactNode
  let helper: React.ReactNode

  if (cfg.env_locked) {
    pill = (
      <Badge variant="outline" className="gap-1.5">
        <LockIcon className="size-3" />
        Configured via env var
      </Badge>
    )
    helper = (
      <span>
        Set via{" "}
        <code className="font-mono text-foreground">OPENAI_API_KEY</code> in
        .env. UI is read-only — unset and restart to manage from here.
      </span>
    )
  } else if (cfg.configured) {
    pill = (
      <Badge
        variant="outline"
        className="gap-1.5 border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
      >
        <span className="inline-flex size-1.5 rounded-full bg-emerald-500" />
        Configured via UI
      </Badge>
    )
    helper = keyMasked ? (
      <span>
        Active key{" "}
        <code className="font-mono text-foreground">{keyMasked}</code>
      </span>
    ) : (
      <span>Provider is live for /v1/chat.</span>
    )
  } else {
    pill = <Badge variant="outline">Not configured</Badge>
    helper = <span>Set up below to enable /v1/chat.</span>
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <PlugIcon className="size-4" />
          Provider status
        </CardTitle>
        <CardDescription>
          What the backend will use for chat completions.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <div className="flex flex-wrap items-center justify-between gap-2 rounded-md border bg-muted/40 px-3 py-2.5">
          <div className="flex items-center gap-2">{pill}</div>
          <span className="text-xs text-muted-foreground">{helper}</span>
        </div>

        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          <StatPill label="Base URL" value={cfg.base_url || "—"} mono />
          <StatPill
            label="Default model"
            value={cfg.default_model || "—"}
            mono
          />
          <StatPill
            label="Models available"
            value={(cfg.available_models?.length ?? 0).toString()}
          />
          <StatPill label="Source" value={source} />
        </div>
      </CardContent>
    </Card>
  )
}

function PresetRow({
  cfg,
  onPick,
  disabled,
}: {
  cfg: LLMConfigResponse
  onPick: (p: Preset) => void
  disabled: boolean
}) {
  const activeId = React.useMemo(() => {
    const match = PRESETS.find(
      (p) => p.id !== "custom" && p.base_url && p.base_url === cfg.base_url,
    )
    return match?.id ?? null
  }, [cfg.base_url])

  return (
    <div className="flex flex-col gap-2 rounded-lg border bg-muted/20 p-3">
      <div className="flex items-center gap-2">
        <SlidersHorizontalIcon className="size-3.5 text-muted-foreground" />
        <span className="text-xs font-medium">Provider presets</span>
        <span className="text-[11px] text-muted-foreground">
          one click to pre-fill base URL, default model, and the picker list
        </span>
      </div>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-5">
        {PRESETS.map((p) => {
          const isActive = activeId === p.id
          return (
            <button
              key={p.id}
              type="button"
              onClick={() => onPick(p)}
              disabled={disabled}
              className={cn(
                "group/preset flex flex-col items-start gap-1 rounded-lg border bg-card px-3 py-2.5 text-left transition-colors",
                "hover:bg-muted/60 focus:outline-none focus-visible:ring-3 focus-visible:ring-ring/50",
                "disabled:pointer-events-none disabled:opacity-50",
                isActive && "border-foreground/30 bg-muted/40",
              )}
            >
              <div className="flex w-full items-center justify-between gap-1.5">
                <span className="text-sm font-medium">{p.label}</span>
                {isActive && (
                  <span className="inline-flex size-4 items-center justify-center rounded-full bg-foreground text-background">
                    <CheckIcon className="size-2.5" />
                  </span>
                )}
              </div>
              <span className="line-clamp-1 font-mono text-[10px] text-muted-foreground">
                {p.id === "custom" ? "blank slate" : p.default_model || "—"}
              </span>
            </button>
          )
        })}
      </div>
      <p className="text-[11px] leading-snug text-muted-foreground">
        {PRESETS.find((p) => p.id === "ollama")?.hint}
      </p>
    </div>
  )
}

function TestAlert({ result }: { result: LLMTestResponse }) {
  if (result.ok) {
    return (
      <Alert>
        <CheckCircle2Icon className="text-emerald-500" />
        <AlertTitle>Connected</AlertTitle>
        <AlertDescription>
          Reached{" "}
          <code className="font-mono text-foreground">
            {result.model ?? "—"}
          </code>
          {typeof result.latency_ms === "number" && (
            <>
              {" "}
              in{" "}
              <span className="font-mono tabular-nums text-foreground">
                {result.latency_ms}ms
              </span>
            </>
          )}
          .
        </AlertDescription>
      </Alert>
    )
  }
  return (
    <Alert variant="destructive">
      <ShieldAlertIcon />
      <AlertTitle>Connection failed</AlertTitle>
      <AlertDescription>
        {result.error ?? "Unknown error from provider."}
      </AlertDescription>
    </Alert>
  )
}

function ConfigForm({
  cfg,
  onSaved,
}: {
  cfg: LLMConfigResponse
  onSaved: (next: LLMConfigResponse) => void
}) {
  const locked = cfg.env_locked
  const [draft, setDraft] = React.useState<DraftState>(() => configToDraft(cfg))
  const [reveal, setReveal] = React.useState(false)
  const [saving, setSaving] = React.useState(false)
  const [testing, setTesting] = React.useState(false)
  const [testResult, setTestResult] = React.useState<LLMTestResponse | null>(
    null,
  )

  // When a fresh config arrives (after save / clear / preset hop), reset the
  // structural fields but keep whatever api_key the user is mid-edit on.
  React.useEffect(() => {
    setDraft((prev) => ({
      api_key: prev.api_key,
      base_url: cfg.base_url ?? "",
      default_model: cfg.default_model ?? "",
      available_models: (cfg.available_models ?? []).join(", "),
    }))
  }, [cfg])

  function applyPreset(p: Preset) {
    setDraft((prev) => ({
      api_key: prev.api_key,
      base_url: p.base_url,
      default_model: p.default_model,
      available_models: p.available_models.join(", "),
    }))
    setTestResult(null)
  }

  function handleReset() {
    setDraft(configToDraft(cfg))
    setReveal(false)
    setTestResult(null)
  }

  async function handleTest() {
    if (!draft.api_key && !cfg.configured) {
      toast.error("Add an API key first")
      return
    }
    setTesting(true)
    setTestResult(null)
    try {
      const res = await api.testLlm({
        ...(draft.api_key ? { api_key: draft.api_key } : {}),
        ...(draft.base_url ? { base_url: draft.base_url } : {}),
        ...(draft.default_model ? { default_model: draft.default_model } : {}),
      })
      setTestResult(res)
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : "Test failed"
      setTestResult({ ok: false, error: msg })
    } finally {
      setTesting(false)
    }
  }

  async function handleSave() {
    if (!draft.api_key.trim()) {
      toast.error("API key is required")
      return
    }
    if (!draft.default_model.trim()) {
      toast.error("Default model is required")
      return
    }
    setSaving(true)
    try {
      const next = await api.saveLlmConfig({
        api_key: draft.api_key.trim(),
        base_url: draft.base_url.trim() || undefined,
        default_model: draft.default_model.trim(),
        available_models: parseModels(draft.available_models),
      })
      toast.success("Provider saved — playground is live")
      // Clear the api_key out of the draft once it lands on the server.
      setDraft((prev) => ({ ...prev, api_key: "" }))
      setReveal(false)
      setTestResult(null)
      onSaved(next)
    } catch (err) {
      if (err instanceof ApiError && err.status === 423) {
        toast.error("Locked by environment", {
          description:
            "OPENAI_API_KEY is set on the backend. Unset and restart to use the UI.",
        })
        try {
          const next = await api.llmConfig()
          onSaved(next)
        } catch {
          // ignore — status card stays as-is
        }
      } else {
        const msg = err instanceof ApiError ? err.message : "Save failed"
        toast.error("Could not save provider", { description: msg })
      }
    } finally {
      setSaving(false)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <CpuIcon className="size-4" />
          Configuration
        </CardTitle>
        <CardDescription>
          Any OpenAI-compatible endpoint works. Saved keys are stored on the
          backend, never in the browser.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        {locked && (
          <Alert>
            <LockIcon />
            <AlertTitle>Locked by environment variable</AlertTitle>
            <AlertDescription>
              <code className="font-mono text-foreground">
                OPENAI_API_KEY
              </code>{" "}
              is set on the backend, so the UI is read-only. Unset it and
              restart the server to manage the provider from here.
            </AlertDescription>
          </Alert>
        )}

        {!locked && (
          <PresetRow cfg={cfg} onPick={applyPreset} disabled={locked} />
        )}

        <div className="grid gap-4">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="llm-api-key">API key</Label>
            <div className="flex items-center gap-2">
              <Input
                id="llm-api-key"
                type={reveal ? "text" : "password"}
                value={draft.api_key}
                onChange={(e) =>
                  setDraft((prev) => ({ ...prev, api_key: e.target.value }))
                }
                placeholder={
                  cfg.configured && !locked
                    ? "Leave blank to keep saved key"
                    : "sk-..."
                }
                disabled={locked}
                className="font-mono text-xs"
                autoComplete="off"
              />
              <Button
                variant="outline"
                size="icon-sm"
                type="button"
                onClick={() => setReveal((v) => !v)}
                disabled={locked || !draft.api_key}
                aria-label={reveal ? "Hide key" : "Reveal key"}
              >
                {reveal ? <EyeOffIcon /> : <EyeIcon />}
              </Button>
            </div>
            <span className="text-[11px] text-muted-foreground">
              Required to save. Sent over HTTPS to the backend.
            </span>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="llm-base-url">Base URL</Label>
              <Input
                id="llm-base-url"
                value={draft.base_url}
                onChange={(e) =>
                  setDraft((prev) => ({ ...prev, base_url: e.target.value }))
                }
                placeholder="https://api.openai.com/v1"
                disabled={locked}
                className="font-mono text-xs"
              />
              <span className="text-[11px] text-muted-foreground">
                OpenAI-compatible endpoint root.
              </span>
            </div>

            <div className="flex flex-col gap-1.5">
              <Label htmlFor="llm-default-model">Default model</Label>
              <Input
                id="llm-default-model"
                value={draft.default_model}
                onChange={(e) =>
                  setDraft((prev) => ({
                    ...prev,
                    default_model: e.target.value,
                  }))
                }
                placeholder="gpt-4o-mini"
                disabled={locked}
                className="font-mono text-xs"
              />
              <span className="text-[11px] text-muted-foreground">
                Used when callers don't specify a model.
              </span>
            </div>
          </div>

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="llm-models">Available models</Label>
            <Input
              id="llm-models"
              value={draft.available_models}
              onChange={(e) =>
                setDraft((prev) => ({
                  ...prev,
                  available_models: e.target.value,
                }))
              }
              placeholder="gpt-4o-mini, gpt-4o"
              disabled={locked}
              className="font-mono text-xs"
            />
            <span className="text-[11px] text-muted-foreground">
              Comma-separated. Models shown in the playground's model picker.
            </span>
          </div>
        </div>

        {testResult && <TestAlert result={testResult} />}

        <div className="flex flex-wrap items-center justify-between gap-2 border-t pt-4">
          <Button
            variant="ghost"
            type="button"
            onClick={handleTest}
            disabled={
              locked ||
              testing ||
              saving ||
              (!draft.api_key && !cfg.configured)
            }
          >
            {testing ? (
              <Loader2Icon className="animate-spin" />
            ) : (
              <PlugZapIcon />
            )}
            Test connection
          </Button>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              type="button"
              onClick={handleReset}
              disabled={locked || saving}
            >
              <RotateCcwIcon />
              Reset
            </Button>
            <Button
              type="button"
              onClick={handleSave}
              disabled={locked || saving}
            >
              {saving ? <Loader2Icon className="animate-spin" /> : <SaveIcon />}
              Save
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

function DangerZone({
  cfg,
  onCleared,
}: {
  cfg: LLMConfigResponse
  onCleared: (next: LLMConfigResponse) => void
}) {
  const [busy, setBusy] = React.useState(false)
  const [open, setOpen] = React.useState(false)

  if (cfg.env_locked || !cfg.configured) return null

  async function handleClear() {
    setBusy(true)
    try {
      const next = await api.clearLlmConfig()
      toast.success("Provider disconnected", {
        description: "Chat will return 503 until you configure another.",
      })
      onCleared(next)
      setOpen(false)
    } catch (err) {
      if (err instanceof ApiError && err.status === 423) {
        toast.error("Locked by environment", {
          description: "OPENAI_API_KEY is set on the backend.",
        })
      } else {
        const msg = err instanceof ApiError ? err.message : "Clear failed"
        toast.error("Could not disconnect", { description: msg })
      }
    } finally {
      setBusy(false)
    }
  }

  return (
    <Card className="border-destructive/30">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-destructive">
          <UnplugIcon className="size-4" />
          Danger zone
        </CardTitle>
        <CardDescription>
          Clears the saved provider. Existing memories are untouched.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <AlertDialog open={open} onOpenChange={setOpen}>
          <AlertDialogTrigger asChild>
            <Button variant="destructive">
              <Trash2Icon />
              Disconnect provider
            </Button>
          </AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Disconnect provider?</AlertDialogTitle>
              <AlertDialogDescription>
                The saved API key, base URL, and model list will be removed
                from the backend. /v1/chat will return 503 until you configure
                another provider.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel disabled={busy}>Cancel</AlertDialogCancel>
              <AlertDialogAction
                variant="destructive"
                disabled={busy}
                onClick={(e) => {
                  e.preventDefault()
                  void handleClear()
                }}
              >
                {busy ? (
                  <Loader2Icon className="animate-spin" />
                ) : (
                  <Trash2Icon />
                )}
                Disconnect
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </CardContent>
    </Card>
  )
}

function PageSkeleton() {
  return (
    <div className="flex flex-col gap-6 py-6">
      <div className="px-4">
        <Skeleton className="h-7 w-48" />
        <Skeleton className="mt-2 h-4 w-96 max-w-full" />
      </div>
      <div className="px-4">
        <Card>
          <CardHeader>
            <Skeleton className="h-5 w-40" />
            <Skeleton className="mt-1.5 h-3 w-64 max-w-full" />
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <Skeleton className="h-10 w-full" />
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
              <Skeleton className="h-12" />
              <Skeleton className="h-12" />
              <Skeleton className="h-12" />
              <Skeleton className="h-12" />
            </div>
          </CardContent>
        </Card>
      </div>
      <div className="px-4">
        <Card>
          <CardHeader>
            <Skeleton className="h-5 w-32" />
            <Skeleton className="mt-1.5 h-3 w-72 max-w-full" />
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <Skeleton className="h-9 w-full" />
            <Skeleton className="h-9 w-full" />
            <Skeleton className="h-9 w-full" />
            <div className="flex justify-between">
              <Skeleton className="h-8 w-32" />
              <Skeleton className="h-8 w-24" />
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

export default function LlmProviderPage() {
  const { data, loading, error, refetch } = useApi(() => api.llmConfig(), [])
  const [override, setOverride] = React.useState<LLMConfigResponse | null>(null)
  const cfg = override ?? data

  function handleUpdate(next: LLMConfigResponse) {
    setOverride(next)
  }

  if (loading && !cfg) {
    return <PageSkeleton />
  }

  if (error && !cfg) {
    return (
      <div className="flex flex-col gap-6 py-6">
        <div className="px-4">
          <h1 className="text-2xl font-semibold tracking-tight">LLM Provider</h1>
          <p className="text-sm text-muted-foreground">
            Configure the model that powers your Studio playground. Memwire
            still ingests memories without one — chat just won't generate.
          </p>
        </div>
        <div className="px-4">
          <Alert variant="destructive">
            <XCircleIcon />
            <AlertTitle>Couldn't load provider config</AlertTitle>
            <AlertDescription className="flex items-center justify-between gap-3">
              <span>{error.message}</span>
              <Button variant="outline" size="sm" onClick={refetch}>
                <RotateCcwIcon />
                Retry
              </Button>
            </AlertDescription>
          </Alert>
        </div>
      </div>
    )
  }

  if (!cfg) return null

  return (
    <div className="flex flex-col gap-6 py-6">
      <div className="flex items-start justify-between gap-3 px-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">LLM Provider</h1>
          <p className="text-sm text-muted-foreground">
            Configure the model that powers your Studio playground. Memwire
            still ingests memories without one — chat just won't generate.
          </p>
        </div>
        <Button variant="ghost" size="sm" onClick={refetch}>
          <RotateCcwIcon />
          Refresh
        </Button>
      </div>

      <div className="px-4">
        <StatusCard cfg={cfg} />
      </div>

      <div className="px-4">
        <ConfigForm cfg={cfg} onSaved={handleUpdate} />
      </div>

      {!cfg.env_locked && cfg.configured && (
        <div className="px-4">
          <DangerZone cfg={cfg} onCleared={handleUpdate} />
        </div>
      )}

      {!cfg.configured && !cfg.env_locked && (
        <div className="px-4">
          <div className="flex items-start gap-2 rounded-md border bg-muted/40 px-3 py-2.5 text-xs text-muted-foreground">
            <CircleSlashIcon className="mt-0.5 size-3.5 shrink-0" />
            <span>
              No provider yet. Pick a preset above or paste an API key to
              enable the playground.
            </span>
          </div>
        </div>
      )}
    </div>
  )
}
