import * as React from "react"
import {
  AlertTriangleIcon,
  CheckCircle2Icon,
  CheckIcon,
  EyeIcon,
  EyeOffIcon,
  KeyRoundIcon,
  RotateCcwIcon,
  ShieldAlertIcon,
  XCircleIcon,
} from "lucide-react"
import { toast } from "sonner"

import { useAuth } from "@/components/auth-provider"
import { CodeBlock } from "@/components/code-block"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { api } from "@/lib/api"
import { useApi } from "@/lib/use-api"

function StatusDot({ ok }: { ok: boolean }) {
  return (
    <span
      className={
        "inline-flex size-2 rounded-full " +
        (ok ? "bg-emerald-500" : "bg-destructive")
      }
      aria-hidden
    />
  )
}

function maskKey(key: string | null): string {
  if (!key) return "—"
  if (key.length <= 8) return `${key}…`
  return `${key.slice(0, 8)}…`
}

export default function ApiKeysPage() {
  const { apiKey, setApiKey } = useAuth()
  const [revealed, setRevealed] = React.useState(false)
  const { data: health, loading, error, refetch } = useApi(() => api.health(), [])
  const authInfoQuery = useApi(() => api.authInfo(), [])
  const authInfo = authInfoQuery.data

  const callerPrefix = apiKey?.slice(0, 8) ?? null
  const prefixMatches =
    !!authInfo &&
    !!authInfo.current_key_prefix &&
    !!callerPrefix &&
    authInfo.current_key_prefix === callerPrefix

  const connected = !!health && !error
  const status = loading
    ? "loading"
    : connected
      ? "connected"
      : "disconnected"

  function handleReset() {
    setApiKey(null)
    toast.success("Connection reset", {
      description: "Studio will prompt you for a new API key.",
    })
  }

  return (
    <div className="flex flex-col gap-6 py-6">
      <div className="px-4">
        <h1 className="text-2xl font-semibold tracking-tight">API Keys</h1>
        <p className="text-sm text-muted-foreground">
          Keys grant programmatic access to your Memwire deployment.
        </p>
      </div>

      <div className="grid gap-4 px-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <ShieldAlertIcon className="size-4" />
              Authentication mode
            </CardTitle>
            <CardDescription>
              Configured via environment variable
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            <CodeBlock
              language="env"
              filename=".env"
              code={"MEMWIRE_API_KEYS=key1,key2,..."}
            />
            <p className="text-xs text-muted-foreground">
              Memwire reads the comma-separated keys from the{" "}
              <code className="font-mono text-foreground">MEMWIRE_API_KEYS</code>{" "}
              env var on container start. Restart the backend after changes.
              Requests authenticate via the{" "}
              <code className="font-mono text-foreground">X-API-Key</code> header.
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <KeyRoundIcon className="size-4" />
              Current connection
            </CardTitle>
            <CardDescription>
              Studio's stored credential and live health status.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <div className="flex items-center justify-between gap-3 rounded-md border bg-muted/40 px-3 py-2.5">
              <div className="flex items-center gap-2">
                {status === "loading" ? (
                  <Skeleton className="size-2 rounded-full" />
                ) : (
                  <StatusDot ok={connected} />
                )}
                <span className="text-sm font-medium">
                  {status === "loading"
                    ? "Checking…"
                    : connected
                      ? "Connected"
                      : "Disconnected"}
                </span>
              </div>
              <Button
                variant="ghost"
                size="icon-sm"
                onClick={refetch}
                aria-label="Re-check status"
              >
                <RotateCcwIcon />
              </Button>
            </div>

            {error && (
              <Alert variant="destructive">
                <XCircleIcon />
                <AlertTitle>Health check failed</AlertTitle>
                <AlertDescription>{error.message}</AlertDescription>
              </Alert>
            )}

            <div className="grid grid-cols-2 gap-2 text-xs">
              <div className="flex flex-col gap-0.5 rounded-md border bg-muted/40 px-2.5 py-1.5">
                <span className="text-[11px] text-muted-foreground">
                  status
                </span>
                <span className="font-medium">
                  {health?.status ?? (loading ? "—" : "unknown")}
                </span>
              </div>
              <div className="flex flex-col gap-0.5 rounded-md border bg-muted/40 px-2.5 py-1.5">
                <span className="text-[11px] text-muted-foreground">
                  version
                </span>
                <span className="font-mono">
                  {health?.version ?? (loading ? "—" : "unknown")}
                </span>
              </div>
            </div>

            <div className="flex flex-col gap-1.5">
              <span className="text-xs text-muted-foreground">
                Server keys configured
              </span>
              <div className="flex items-center justify-between gap-3 rounded-md border bg-muted/40 px-2.5 py-1.5">
                {authInfoQuery.loading && !authInfo ? (
                  <Skeleton className="h-4 w-24" />
                ) : authInfoQuery.error ? (
                  <span className="text-xs text-muted-foreground">
                    unavailable
                  </span>
                ) : authInfo?.configured ? (
                  <span className="text-xs">
                    {authInfo.configured_count}{" "}
                    {authInfo.configured_count === 1 ? "key" : "keys"} configured
                  </span>
                ) : (
                  <span className="text-xs text-muted-foreground">
                    Auth disabled — no keys set
                  </span>
                )}
                {authInfo?.configured ? (
                  <Badge variant="secondary" className="font-mono tabular-nums">
                    {authInfo.configured_count}
                  </Badge>
                ) : authInfo ? (
                  <Badge variant="outline">open</Badge>
                ) : null}
              </div>
            </div>

            <div className="flex flex-col gap-1.5">
              <span className="text-xs text-muted-foreground">
                Caller prefix matches server
              </span>
              <div className="flex items-center justify-between gap-3 rounded-md border bg-muted/40 px-2.5 py-1.5">
                {authInfoQuery.loading && !authInfo ? (
                  <Skeleton className="h-4 w-24" />
                ) : !authInfo?.configured ? (
                  <span className="text-xs text-muted-foreground">
                    No keys to match against
                  </span>
                ) : !callerPrefix ? (
                  <span className="text-xs text-muted-foreground">
                    No key stored locally
                  </span>
                ) : prefixMatches ? (
                  <span className="flex items-center gap-1.5 text-xs">
                    <CheckIcon className="size-3.5 text-emerald-500" />
                    Server is checking against{" "}
                    <code className="font-mono">{callerPrefix}…</code>
                  </span>
                ) : (
                  <span className="flex items-center gap-1.5 text-xs">
                    <AlertTriangleIcon className="size-3.5 text-destructive" />
                    Studio key{" "}
                    <code className="font-mono">{callerPrefix}…</code> differs
                    from server&apos;s{" "}
                    <code className="font-mono">
                      {authInfo.current_key_prefix ?? "—"}
                    </code>
                  </span>
                )}
                {authInfo?.configured && callerPrefix && (
                  <Badge
                    variant={prefixMatches ? "secondary" : "destructive"}
                    className="font-mono text-[10px]"
                  >
                    {prefixMatches ? "match" : "key drift"}
                  </Badge>
                )}
              </div>
            </div>

            <div className="flex flex-col gap-1.5">
              <span className="text-xs text-muted-foreground">
                Studio's stored key
              </span>
              <div className="flex items-center gap-2">
                <code className="flex-1 truncate rounded-md border bg-muted px-2.5 py-1.5 font-mono text-xs">
                  {revealed ? (apiKey ?? "—") : maskKey(apiKey)}
                </code>
                <Button
                  variant="outline"
                  size="icon-sm"
                  onClick={() => setRevealed((v) => !v)}
                  aria-label={revealed ? "Hide key" : "Reveal key"}
                  disabled={!apiKey}
                >
                  {revealed ? <EyeOffIcon /> : <EyeIcon />}
                </Button>
              </div>
            </div>

            <Button variant="outline" onClick={handleReset}>
              <RotateCcwIcon />
              Reset connection
            </Button>
          </CardContent>
        </Card>
      </div>

      <div className="px-4">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CheckCircle2Icon className="size-4" />
              Adding more keys
            </CardTitle>
            <CardDescription>
              Three ways to set the{" "}
              <code className="font-mono text-foreground">
                MEMWIRE_API_KEYS
              </code>{" "}
              environment variable.
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-3 lg:grid-cols-3">
            <div className="flex flex-col gap-2">
              <Badge variant="outline" className="self-start">
                .env file
              </Badge>
              <CodeBlock
                language="env"
                filename=".env"
                code={"MEMWIRE_API_KEYS=foo,bar,baz"}
              />
            </div>
            <div className="flex flex-col gap-2">
              <Badge variant="outline" className="self-start">
                docker compose
              </Badge>
              <CodeBlock
                language="yaml"
                filename="docker-compose.yml"
                code={`services:
  memwire:
    image: memwire/server
    environment:
      MEMWIRE_API_KEYS: foo,bar,baz`}
              />
            </div>
            <div className="flex flex-col gap-2">
              <Badge variant="outline" className="self-start">
                shell
              </Badge>
              <CodeBlock
                language="bash"
                filename="bash"
                code={`export MEMWIRE_API_KEYS=foo,bar,baz
uvicorn memwire.server.app:app`}
              />
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
