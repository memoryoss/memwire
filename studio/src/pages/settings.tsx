import * as React from "react"
import {
  ArrowRightLeftIcon,
  CheckIcon,
  MonitorIcon,
  MoonIcon,
  RotateCcwIcon,
  SunIcon,
  TrashIcon,
  UploadIcon,
  UsersIcon,
} from "lucide-react"
import { toast } from "sonner"

import { useAuth } from "@/components/auth-provider"
import { useTheme } from "@/components/theme-provider"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
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
  CardFooter,
} from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import {
  InputGroup,
  InputGroupAddon,
  InputGroupInput,
} from "@/components/ui/input-group"
import { Label } from "@/components/ui/label"
import { Progress } from "@/components/ui/progress"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Separator } from "@/components/ui/separator"
import { Switch } from "@/components/ui/switch"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Textarea } from "@/components/ui/textarea"
import { api } from "@/lib/api"
import { useApi } from "@/lib/use-api"
import { cn } from "@/lib/utils"

type SectionId =
  | "profile"
  | "workspace"
  | "connection"
  | "appearance"
  | "notifications"
  | "billing"
  | "danger"

const TABS: { value: SectionId; label: string }[] = [
  { value: "profile", label: "Profile" },
  { value: "workspace", label: "Workspace" },
  { value: "connection", label: "Connection" },
  { value: "appearance", label: "Appearance" },
  { value: "notifications", label: "Notifications" },
  { value: "billing", label: "Billing" },
  { value: "danger", label: "Danger Zone" },
]

function SectionHeader({
  id,
  title,
  helper,
  refEl,
}: {
  id: SectionId
  title: string
  helper: string
  refEl: React.RefObject<HTMLDivElement | null>
}) {
  return (
    <div ref={refEl} id={id} className="scroll-mt-20">
      <h2 className="text-base font-semibold tracking-tight">{title}</h2>
      <p className="text-sm text-muted-foreground mt-1.5 mb-6">{helper}</p>
    </div>
  )
}

function SwitchRow({
  title,
  helper,
  defaultChecked,
}: {
  title: string
  helper: string
  defaultChecked?: boolean
}) {
  return (
    <div className="flex items-start justify-between gap-4 py-1">
      <div className="space-y-1">
        <p className="text-sm font-medium">{title}</p>
        <p className="text-xs text-muted-foreground">{helper}</p>
      </div>
      <Switch defaultChecked={defaultChecked} />
    </div>
  )
}

function ThemeCard({
  value,
  label,
  icon: Icon,
  swatches,
  selected,
  onClick,
}: {
  value: "light" | "dark" | "system"
  label: string
  icon: React.ComponentType<{ className?: string }>
  swatches: string[]
  selected: boolean
  onClick: () => void
}) {
  return (
    <button
      type="button"
      role="radio"
      aria-checked={selected}
      data-value={value}
      onClick={onClick}
      className={cn(
        "group flex flex-col items-start gap-3 rounded-xl border bg-card p-4 text-left transition-all outline-none",
        "hover:border-foreground/30 focus-visible:ring-3 focus-visible:ring-ring/50",
        selected
          ? "border-primary ring-1 ring-primary"
          : "border-border"
      )}
    >
      <div className="flex w-full items-center justify-between">
        <div className="flex items-center gap-2">
          <Icon className="size-4 text-muted-foreground" />
          <span className="text-sm font-medium">{label}</span>
        </div>
        {selected ? (
          <span className="inline-flex size-4 items-center justify-center rounded-full bg-primary text-primary-foreground">
            <CheckIcon className="size-3" />
          </span>
        ) : null}
      </div>
      <div className="flex w-full items-center gap-1 rounded-md border border-border/60 p-1">
        {swatches.map((cls, i) => (
          <div key={i} className={cn("h-4 flex-1 rounded-sm", cls)} />
        ))}
      </div>
    </button>
  )
}

function UsageBar({
  label,
  used,
  total,
  display,
}: {
  label: string
  used: number
  total: number
  display: string
}) {
  const pct = Math.min(100, Math.round((used / total) * 100))
  return (
    <div className="space-y-2">
      <div className="flex items-baseline justify-between">
        <span className="text-sm font-medium">{label}</span>
        <span className="text-sm tabular-nums text-muted-foreground">
          {display}
        </span>
      </div>
      <Progress value={pct} />
      <p className="text-xs tabular-nums text-muted-foreground">
        {pct}% used
      </p>
    </div>
  )
}

function DangerRow({
  title,
  helper,
  action,
}: {
  title: string
  helper: string
  action: React.ReactNode
}) {
  return (
    <div className="flex flex-col gap-3 py-2 sm:flex-row sm:items-center sm:justify-between sm:gap-6">
      <div className="space-y-1">
        <p className="text-sm font-medium">{title}</p>
        <p className="text-xs text-muted-foreground">{helper}</p>
      </div>
      <div className="shrink-0">{action}</div>
    </div>
  )
}

function maskKey(key: string | null): string {
  if (!key) return "—"
  if (key.length <= 8) return `${key}…`
  return `${key.slice(0, 8)}…`
}

function ConnectionRow({
  label,
  children,
}: {
  label: string
  children: React.ReactNode
}) {
  return (
    <div className="flex flex-col gap-2 py-2 sm:flex-row sm:items-center sm:justify-between sm:gap-6">
      <p className="text-sm font-medium">{label}</p>
      <div className="flex items-center gap-2 sm:justify-end">{children}</div>
    </div>
  )
}

function ConnectionSection() {
  const { apiKey, setApiKey } = useAuth()
  const [revealed, setRevealed] = React.useState(false)
  const { data: health, loading, error, refetch } = useApi(
    () => api.health(),
    [],
  )
  const apiBase =
    (import.meta.env.VITE_API_URL as string | undefined) ||
    (typeof window !== "undefined" ? window.location.origin : "")

  function handleReset() {
    setApiKey(null)
    toast.success("Connection reset", {
      description: "Studio will prompt you for a new API key.",
    })
  }

  const connected = !loading && !error && !!health

  return (
    <Card>
      <CardContent className="space-y-2 pt-2">
        <ConnectionRow label="Active key">
          <code
            className="rounded-md border bg-muted px-2 py-1 font-mono text-xs"
            title={revealed ? apiKey ?? "" : undefined}
          >
            {revealed ? apiKey ?? "—" : maskKey(apiKey)}
          </code>
          <div className="flex items-center gap-1.5">
            <Switch
              checked={revealed}
              onCheckedChange={setRevealed}
              disabled={!apiKey}
              aria-label="Reveal key"
            />
            <span className="text-[11px] text-muted-foreground">Reveal</span>
          </div>
          <Button variant="outline" size="sm" onClick={handleReset}>
            <RotateCcwIcon />
            Reset
          </Button>
        </ConnectionRow>
        <Separator />
        <ConnectionRow label="Server">
          <code className="rounded-md border bg-muted px-2 py-1 font-mono text-xs">
            {apiBase || "—"}
          </code>
        </ConnectionRow>
        <Separator />
        <ConnectionRow label="Status">
          {loading ? (
            <Badge variant="outline" className="text-muted-foreground">
              Checking…
            </Badge>
          ) : connected ? (
            <Badge variant="outline" className="gap-1.5">
              <span className="inline-flex size-1.5 rounded-full bg-emerald-500" />
              Connected
              {health?.version && (
                <span className="text-muted-foreground">· v{health.version}</span>
              )}
            </Badge>
          ) : (
            <Badge variant="destructive" className="gap-1.5">
              <span className="inline-flex size-1.5 rounded-full bg-destructive" />
              Disconnected
            </Badge>
          )}
          <Button
            variant="ghost"
            size="icon-sm"
            onClick={refetch}
            aria-label="Re-check status"
          >
            <RotateCcwIcon />
          </Button>
        </ConnectionRow>
        {error && (
          <p className="text-xs text-destructive">{error.message}</p>
        )}
      </CardContent>
    </Card>
  )
}

function DeleteWorkspaceDialog({ workspaceName }: { workspaceName: string }) {
  const [confirm, setConfirm] = React.useState("")
  const [open, setOpen] = React.useState(false)
  const matches = confirm === workspaceName

  React.useEffect(() => {
    if (!open) setConfirm("")
  }, [open])

  return (
    <AlertDialog open={open} onOpenChange={setOpen}>
      <AlertDialogTrigger asChild>
        <Button variant="destructive">
          <TrashIcon />
          Delete workspace
        </Button>
      </AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Delete this workspace?</AlertDialogTitle>
          <AlertDialogDescription>
            This permanently removes the workspace, every project inside it,
            and all stored memories. This cannot be undone.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <div className="space-y-2">
          <Label htmlFor="confirm-name" className="text-xs">
            Type{" "}
            <span className="font-mono text-foreground">{workspaceName}</span>{" "}
            to confirm.
          </Label>
          <Input
            id="confirm-name"
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            autoComplete="off"
            spellCheck={false}
          />
        </div>
        <AlertDialogFooter>
          <AlertDialogCancel>Cancel</AlertDialogCancel>
          <AlertDialogAction variant="destructive" disabled={!matches}>
            Delete workspace
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}

export default function SettingsPage() {
  const { theme, setTheme } = useTheme()
  const [active, setActive] = React.useState<SectionId>("profile")

  const refs = {
    profile: React.useRef<HTMLDivElement | null>(null),
    workspace: React.useRef<HTMLDivElement | null>(null),
    connection: React.useRef<HTMLDivElement | null>(null),
    appearance: React.useRef<HTMLDivElement | null>(null),
    notifications: React.useRef<HTMLDivElement | null>(null),
    billing: React.useRef<HTMLDivElement | null>(null),
    danger: React.useRef<HTMLDivElement | null>(null),
  } as const

  const handleTabChange = (v: string) => {
    const id = v as SectionId
    setActive(id)
    refs[id].current?.scrollIntoView({ behavior: "smooth", block: "start" })
  }

  // workspace state
  const [workspaceName, setWorkspaceName] = React.useState("Memwire Labs")
  const [slug, setSlug] = React.useState("memwire-labs")
  const [description, setDescription] = React.useState(
    "Production memory infrastructure for our agent stack — graph recall, ingestion pipelines, and webhook routing."
  )
  const [scope, setScope] = React.useState("strict")
  const [density, setDensity] = React.useState("comfortable")

  return (
    <div className="mx-auto w-full max-w-3xl px-6 py-10">
      <header className="mb-8">
        <h1 className="text-2xl font-semibold tracking-tight">Settings</h1>
        <p className="mt-1.5 text-sm text-muted-foreground">
          Manage your account, workspace, and preferences.
        </p>
      </header>

      <div className="sticky top-14 z-10 -mx-6 mb-10 border-b bg-background/80 px-6 py-3 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <Tabs value={active} onValueChange={handleTabChange}>
          <TabsList variant="line" className="flex w-full flex-wrap gap-1">
            {TABS.map((t) => (
              <TabsTrigger key={t.value} value={t.value}>
                {t.label}
              </TabsTrigger>
            ))}
          </TabsList>
        </Tabs>
      </div>

      <div className="space-y-12">
        {/* PROFILE */}
        <section>
          <SectionHeader
            id="profile"
            title="Profile"
            helper="How your identity appears across the Memwire studio and audit logs."
            refEl={refs.profile}
          />
          <Card>
            <CardContent className="space-y-6 pt-2">
              <div className="flex items-center gap-4">
                <Avatar size="lg" className="size-16">
                  <AvatarFallback className="text-base">HM</AvatarFallback>
                </Avatar>
                <div className="flex flex-wrap items-center gap-2">
                  <Button variant="outline">
                    <UploadIcon />
                    Upload new
                  </Button>
                  <Button variant="ghost">Remove</Button>
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="name">Name</Label>
                <Input id="name" defaultValue="Harshal More" />
              </div>

              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
                  defaultValue="harshal@memwire.dev"
                />
                <p className="text-xs text-muted-foreground mt-1.5">
                  Used for login and notifications.
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="role">Role</Label>
                <Select disabled defaultValue="Owner">
                  <SelectTrigger id="role" className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="Owner">Owner</SelectItem>
                    <SelectItem value="Admin">Admin</SelectItem>
                    <SelectItem value="Member">Member</SelectItem>
                    <SelectItem value="Viewer">Viewer</SelectItem>
                  </SelectContent>
                </Select>
                <p className="text-xs text-muted-foreground mt-1.5">
                  Roles are assigned by a workspace owner.
                </p>
              </div>
            </CardContent>
            <CardFooter className="justify-end gap-2">
              <Button variant="ghost">Reset</Button>
              <Button>Save changes</Button>
            </CardFooter>
          </Card>
        </section>

        {/* WORKSPACE */}
        <section>
          <SectionHeader
            id="workspace"
            title="Workspace"
            helper="The shared context that groups projects, members, and billing."
            refEl={refs.workspace}
          />
          <Card>
            <CardContent className="space-y-6 pt-2">
              <div className="space-y-2">
                <Label htmlFor="ws-name">Workspace name</Label>
                <Input
                  id="ws-name"
                  value={workspaceName}
                  onChange={(e) => setWorkspaceName(e.target.value)}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="ws-slug">Slug</Label>
                <InputGroup>
                  <InputGroupAddon>memwire.dev/</InputGroupAddon>
                  <InputGroupInput
                    id="ws-slug"
                    value={slug}
                    onChange={(e) => setSlug(e.target.value)}
                  />
                </InputGroup>
                <p className="text-xs text-muted-foreground mt-1.5">
                  Lowercase letters, numbers and dashes. Used in API URLs and
                  invite links.
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="ws-desc">Description</Label>
                <Textarea
                  id="ws-desc"
                  rows={4}
                  maxLength={280}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                />
                <p className="text-xs tabular-nums text-muted-foreground mt-1.5">
                  {description.length} / 280
                </p>
              </div>

              <div className="space-y-3">
                <Label>Default user scope</Label>
                <RadioGroup
                  value={scope}
                  onValueChange={setScope}
                  className="gap-3"
                >
                  {[
                    {
                      value: "strict",
                      title: "Strict isolation",
                      helper:
                        "Memories are scoped to a single agent and a single app. Highest privacy, lowest reuse.",
                    },
                    {
                      value: "cross-agent",
                      title: "Cross-agent",
                      helper:
                        "Memories are shared across agents inside the same app. Useful for multi-agent stacks.",
                    },
                    {
                      value: "cross-app",
                      title: "Cross-app",
                      helper:
                        "Memories follow the user across every app in this workspace. Maximum reuse.",
                    },
                  ].map((opt) => (
                    <Label
                      key={opt.value}
                      htmlFor={`scope-${opt.value}`}
                      className={cn(
                        "flex cursor-pointer items-start gap-3 rounded-lg border bg-card p-3 transition-colors",
                        scope === opt.value
                          ? "border-primary ring-1 ring-primary"
                          : "border-border hover:border-foreground/30"
                      )}
                    >
                      <RadioGroupItem
                        value={opt.value}
                        id={`scope-${opt.value}`}
                        className="mt-0.5"
                      />
                      <div className="space-y-1">
                        <p className="text-sm font-medium">{opt.title}</p>
                        <p className="text-xs text-muted-foreground">
                          {opt.helper}
                        </p>
                      </div>
                    </Label>
                  ))}
                </RadioGroup>
              </div>
            </CardContent>
            <CardFooter className="justify-end">
              <Button>Save changes</Button>
            </CardFooter>
          </Card>
        </section>

        {/* CONNECTION */}
        <section>
          <SectionHeader
            id="connection"
            title="API connection"
            helper="Manage how Studio talks to your Memwire backend."
            refEl={refs.connection}
          />
          <ConnectionSection />
        </section>

        {/* APPEARANCE */}
        <section>
          <SectionHeader
            id="appearance"
            title="Appearance"
            helper="Tune how the studio renders. Changes apply immediately on this device."
            refEl={refs.appearance}
          />
          <Card>
            <CardContent className="space-y-8 pt-2">
              <div className="space-y-3">
                <Label>Theme</Label>
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                  <ThemeCard
                    value="light"
                    label="Light"
                    icon={SunIcon}
                    swatches={[
                      "bg-background border border-border",
                      "bg-muted",
                      "bg-primary",
                      "bg-accent",
                    ]}
                    selected={theme === "light"}
                    onClick={() => setTheme("light")}
                  />
                  <ThemeCard
                    value="dark"
                    label="Dark"
                    icon={MoonIcon}
                    swatches={[
                      "bg-foreground",
                      "bg-muted-foreground/40",
                      "bg-primary",
                      "bg-accent",
                    ]}
                    selected={theme === "dark"}
                    onClick={() => setTheme("dark")}
                  />
                  <ThemeCard
                    value="system"
                    label="System"
                    icon={MonitorIcon}
                    swatches={[
                      "bg-background border border-border",
                      "bg-foreground",
                      "bg-primary",
                      "bg-muted",
                    ]}
                    selected={theme === "system"}
                    onClick={() => setTheme("system")}
                  />
                </div>
                <p className="text-xs text-muted-foreground mt-1.5">
                  System follows your OS preference.
                </p>
              </div>

              <div className="space-y-3">
                <Label>Density</Label>
                <RadioGroup
                  value={density}
                  onValueChange={setDensity}
                  className="grid grid-cols-2 gap-3"
                >
                  {[
                    { value: "comfortable", label: "Comfortable" },
                    { value: "compact", label: "Compact" },
                  ].map((opt) => (
                    <Label
                      key={opt.value}
                      htmlFor={`density-${opt.value}`}
                      className={cn(
                        "flex cursor-pointer items-center gap-3 rounded-lg border bg-card p-3 transition-colors",
                        density === opt.value
                          ? "border-primary ring-1 ring-primary"
                          : "border-border hover:border-foreground/30"
                      )}
                    >
                      <RadioGroupItem
                        value={opt.value}
                        id={`density-${opt.value}`}
                      />
                      <span className="text-sm font-medium">{opt.label}</span>
                    </Label>
                  ))}
                </RadioGroup>
              </div>

              <div className="space-y-2">
                <SwitchRow
                  title="Start collapsed on desktop"
                  helper="The sidebar opens collapsed on widescreen displays."
                />
                <Separator />
                <SwitchRow
                  title="Use tabular numbers in data tables"
                  helper="Aligns digits in metrics, charts, and recall scores."
                  defaultChecked
                />
              </div>
            </CardContent>
          </Card>
        </section>

        {/* NOTIFICATIONS */}
        <section>
          <SectionHeader
            id="notifications"
            title="Notifications"
            helper="Choose what gets sent to your inbox and what stays in-app only."
            refEl={refs.notifications}
          />
          <Card>
            <CardContent className="space-y-3 pt-2">
              <SwitchRow
                title="Weekly email digest"
                helper="A summary of recall volume, top users, and graph growth, every Monday."
                defaultChecked
              />
              <Separator />
              <SwitchRow
                title="Recall failures"
                helper="Get notified when recall returns 0 paths above threshold."
                defaultChecked
              />
              <Separator />
              <SwitchRow
                title="Webhook errors"
                helper="Alert when an outbound webhook returns non-2xx for more than 3 minutes."
                defaultChecked
              />
              <Separator />
              <SwitchRow
                title="Product updates"
                helper="Occasional emails about new releases, infra changes, and roadmap."
              />
            </CardContent>
            <CardFooter className="justify-end">
              <Button>Save preferences</Button>
            </CardFooter>
          </Card>
        </section>

        {/* BILLING */}
        <section>
          <SectionHeader
            id="billing"
            title="Billing"
            helper="Plan, usage, and the people on this workspace."
            refEl={refs.billing}
          />
          <Card>
            <CardContent className="space-y-8 pt-2">
              <div className="flex flex-wrap items-baseline gap-x-4 gap-y-2">
                <Badge>Pro</Badge>
                <span className="text-2xl font-semibold tabular-nums tracking-tight">
                  $49
                </span>
                <span className="text-sm text-muted-foreground">/ month</span>
                <span className="ml-auto text-sm text-muted-foreground">
                  Renews May 24, 2026
                </span>
              </div>

              <div className="space-y-6">
                <UsageBar
                  label="Memories used"
                  used={412008}
                  total={1000000}
                  display="412,008 / 1,000,000"
                />
                <UsageBar
                  label="API calls today"
                  used={8742}
                  total={10000}
                  display="8,742 / 10,000"
                />
                <UsageBar
                  label="Storage"
                  used={12.4}
                  total={50}
                  display="12.4 GB / 50 GB"
                />
              </div>

              <div className="flex items-center gap-3 rounded-lg border bg-muted/40 px-3 py-2.5">
                <UsersIcon className="size-4 text-muted-foreground" />
                <span className="text-sm">
                  <span className="font-medium tabular-nums">8</span>
                  <span className="text-muted-foreground"> of </span>
                  <span className="font-medium tabular-nums">10</span>
                  <span className="text-muted-foreground"> seats used</span>
                </span>
              </div>
            </CardContent>
            <CardFooter className="justify-end gap-2">
              <Button variant="outline">Manage billing</Button>
              <Button>Upgrade plan</Button>
            </CardFooter>
          </Card>
        </section>

        {/* DANGER */}
        <section>
          <SectionHeader
            id="danger"
            title="Danger zone"
            helper="Irreversible operations. Read the helper text before clicking."
            refEl={refs.danger}
          />
          <Card className="border-destructive/40 ring-destructive/20">
            <CardContent className="pt-2">
              <DangerRow
                title="Transfer workspace"
                helper="Move ownership to another member. You will keep admin access until they accept."
                action={
                  <Button variant="outline">
                    <ArrowRightLeftIcon />
                    Transfer
                  </Button>
                }
              />
              <Separator className="my-2" />
              <DangerRow
                title="Delete workspace"
                helper="Removes every project, memory, and audit record in this workspace. Cannot be undone."
                action={
                  <DeleteWorkspaceDialog workspaceName={workspaceName} />
                }
              />
            </CardContent>
          </Card>
        </section>
      </div>
    </div>
  )
}
