import * as React from "react"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { KeyRoundIcon, ShieldAlertIcon } from "lucide-react"
import { useAuth } from "@/components/auth-provider"
import { api, ApiError } from "@/lib/api"

export function AuthGate({ children }: { children: React.ReactNode }) {
  const { hasKey, setApiKey } = useAuth()
  const [draft, setDraft] = React.useState("")
  const [submitting, setSubmitting] = React.useState(false)
  const [error, setError] = React.useState<string | null>(null)
  // null = probing, true = auth required, false = auth disabled (gate skipped)
  const [authRequired, setAuthRequired] = React.useState<boolean | null>(null)

  // On mount, probe the server without credentials. If the server reports that
  // no API keys are configured (auth disabled), skip the gate entirely.
  React.useEffect(() => {
    let cancelled = false
    async function probe() {
      try {
        const info = await api.authInfo()
        if (!cancelled) {
          // configured=false means the server has no API keys set — gate not needed
          setAuthRequired(info.configured)
        }
      } catch {
        // 401 (auth enabled) or network error — show gate
        if (!cancelled) setAuthRequired(true)
      }
    }
    probe()
    return () => { cancelled = true }
  }, [])

  // Show gate when auth is required on the server AND no key is stored locally.
  const open = authRequired === true && !hasKey

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!draft.trim()) return
    setSubmitting(true)
    setError(null)
    setApiKey(draft.trim())
    try {
      // probe an authenticated endpoint to validate the key
      await api.stats()
      setDraft("")
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        setError("That key was rejected by the server.")
      } else if (err instanceof ApiError && err.status === 0) {
        setError(
          "Could not reach the server. Is memwire running on port 8000?",
        )
      } else {
        // Backend reachable but probe failed for another reason — accept the
        // key anyway; the user can investigate from inside the app.
        setDraft("")
      }
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <>
      {children}
      <Dialog open={open}>
        <DialogContent
          showCloseButton={false}
          onEscapeKeyDown={(e) => e.preventDefault()}
          onPointerDownOutside={(e) => e.preventDefault()}
          onInteractOutside={(e) => e.preventDefault()}
          className="sm:max-w-md"
        >
          <DialogHeader>
            <div className="mb-2 flex size-10 items-center justify-center rounded-full bg-muted">
              <KeyRoundIcon className="size-5" />
            </div>
            <DialogTitle>Connect to Memwire</DialogTitle>
            <DialogDescription>
              Paste an API key from your <code className="text-xs">MEMWIRE_API_KEYS</code>{" "}
              environment. Stored locally — never sent anywhere except your
              Memwire backend.
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="api-key">API key</Label>
              <Input
                id="api-key"
                type="password"
                autoFocus
                placeholder="mw_live_..."
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                autoComplete="off"
                spellCheck={false}
              />
            </div>
            {error && (
              <Alert variant="destructive">
                <ShieldAlertIcon />
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}
            <DialogFooter>
              <Button type="submit" disabled={!draft.trim() || submitting}>
                {submitting ? "Verifying…" : "Connect"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </>
  )
}
