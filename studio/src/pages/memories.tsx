import * as React from "react"
import {
  ChevronLeftIcon,
  ChevronRightIcon,
  DatabaseIcon,
  PlayIcon,
  RotateCcwIcon,
  SearchIcon,
  XIcon,
} from "lucide-react"
import { Link } from "react-router-dom"

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import {
  InputGroup,
  InputGroupAddon,
  InputGroupInput,
} from "@/components/ui/input-group"
import { Input } from "@/components/ui/input"
import { Progress } from "@/components/ui/progress"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { type MemoryListItem, api } from "@/lib/api"
import { categoryTone, formatRelative } from "@/lib/format"
import { useApi } from "@/lib/use-api"
import { cn } from "@/lib/utils"

const ROLES = ["user", "assistant", "system"] as const
type RoleFilter = (typeof ROLES)[number] | "all"

const PAGE_SIZES = [25, 50, 100] as const

function useDebouncedValue<T>(value: T, delay = 300): T {
  const [debounced, setDebounced] = React.useState(value)
  React.useEffect(() => {
    const t = window.setTimeout(() => setDebounced(value), delay)
    return () => window.clearTimeout(t)
  }, [value, delay])
  return debounced
}

function StatsStrip() {
  const { data, loading } = useApi(() => api.stats(), [])
  const items: { label: string; value: string }[] = data
    ? [
        { label: "Total memories", value: data.total_memories.toLocaleString() },
        { label: "Distinct users", value: data.distinct_users.toLocaleString() },
        {
          label: "Knowledge bases",
          value: data.total_knowledge_bases.toLocaleString(),
        },
        {
          label: "Distinct categories",
          value: Object.keys(data.by_category ?? {}).length.toLocaleString(),
        },
      ]
    : [
        { label: "Total memories", value: "—" },
        { label: "Distinct users", value: "—" },
        { label: "Knowledge bases", value: "—" },
        { label: "Distinct categories", value: "—" },
      ]
  return (
    <Card>
      <CardContent className="flex flex-wrap divide-x divide-border px-0">
        {items.map((it) => (
          <div key={it.label} className="flex flex-col gap-0.5 px-6 py-3">
            <span className="text-xs text-muted-foreground">{it.label}</span>
            {loading ? (
              <Skeleton className="h-6 w-20" />
            ) : (
              <span className="text-xl font-semibold tabular-nums">
                {it.value}
              </span>
            )}
          </div>
        ))}
      </CardContent>
    </Card>
  )
}

function MiniGraph() {
  const nodes = [
    { x: 30, y: 30 },
    { x: 90, y: 18 },
    { x: 150, y: 40 },
    { x: 60, y: 80 },
    { x: 120, y: 80 },
    { x: 180, y: 70 },
  ]
  const edges: [number, number][] = [
    [0, 1],
    [1, 2],
    [0, 3],
    [1, 3],
    [2, 4],
    [3, 4],
    [4, 5],
  ]
  return (
    <svg
      viewBox="0 0 210 110"
      className="h-32 w-full text-muted-foreground"
      role="img"
      aria-label="Mini graph visualization"
    >
      {edges.map(([a, b], i) => (
        <line
          key={i}
          x1={nodes[a].x}
          y1={nodes[a].y}
          x2={nodes[b].x}
          y2={nodes[b].y}
          className="stroke-current"
          strokeWidth={1}
          strokeOpacity={0.5}
        />
      ))}
      {nodes.map((n, i) => (
        <circle
          key={i}
          cx={n.x}
          cy={n.y}
          r={6}
          className="fill-card stroke-border"
          strokeWidth={1.5}
        />
      ))}
    </svg>
  )
}

function Meta({
  label,
  value,
  mono = false,
}: {
  label: string
  value: string
  mono?: boolean
}) {
  return (
    <div className="flex flex-col gap-0.5 rounded-md border bg-muted/40 px-2.5 py-1.5">
      <span className="text-[11px] text-muted-foreground">{label}</span>
      <span className={cn("truncate text-xs", mono && "font-mono")}>
        {value}
      </span>
    </div>
  )
}

function MemorySheet({
  memory,
  open,
  onOpenChange,
}: {
  memory: MemoryListItem | null
  open: boolean
  onOpenChange: (v: boolean) => void
}) {
  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-full overflow-y-auto sm:max-w-md">
        {memory && (
          <>
            <SheetHeader className="border-b pb-3">
              <SheetTitle className="font-mono text-sm">
                {memory.memory_id}
              </SheetTitle>
              <SheetDescription className="flex flex-wrap items-center gap-2">
                <Badge variant="outline">{memory.role}</Badge>
                {memory.category && (
                  <Badge
                    variant={categoryTone(memory.category).variant}
                    className={categoryTone(memory.category).cls}
                  >
                    {memory.category}
                  </Badge>
                )}
              </SheetDescription>
            </SheetHeader>

            <div className="flex flex-col gap-4 px-4 pb-6">
              <Card size="sm">
                <CardContent>
                  <p className="text-sm leading-relaxed whitespace-pre-wrap">
                    {memory.content}
                  </p>
                </CardContent>
              </Card>

              <section className="flex flex-col gap-2">
                <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                  Metadata
                </h4>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <Meta label="user_id" value={memory.user_id} mono />
                  <Meta label="agent_id" value={memory.agent_id ?? "—"} mono />
                  <Meta label="app_id" value={memory.app_id ?? "—"} mono />
                  <Meta
                    label="workspace_id"
                    value={memory.workspace_id ?? "—"}
                    mono
                  />
                  <Meta label="org_id" value={memory.org_id ?? "—"} mono />
                  <Meta
                    label="created"
                    value={formatRelative(memory.timestamp)}
                  />
                  <Meta
                    label="access count"
                    value={memory.access_count.toString()}
                  />
                </div>
                <div className="mt-1 flex flex-col gap-1">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-muted-foreground">strength</span>
                    <span className="font-medium tabular-nums">
                      {memory.strength.toFixed(2)}
                    </span>
                  </div>
                  <Progress value={memory.strength * 100} />
                </div>
              </section>

              <section className="flex flex-col gap-2">
                <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                  Linked nodes
                </h4>
                <div className="flex flex-wrap items-center gap-1">
                  {memory.node_ids.length === 0 ? (
                    <span className="text-xs text-muted-foreground">
                      No nodes linked.
                    </span>
                  ) : (
                    memory.node_ids.slice(0, 8).map((t, i, arr) => (
                      <React.Fragment key={`${t}-${i}`}>
                        <Badge variant="outline" className="font-mono text-[10.5px]">
                          {t}
                        </Badge>
                        {i < arr.length - 1 && (
                          <ChevronRightIcon className="size-3 text-muted-foreground" />
                        )}
                      </React.Fragment>
                    ))
                  )}
                  {memory.node_ids.length > 8 && (
                    <Badge variant="outline" className="text-muted-foreground">
                      +{memory.node_ids.length - 8}
                    </Badge>
                  )}
                </div>
              </section>

              <section className="flex flex-col gap-2">
                <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                  Displacement graph
                </h4>
                <Card size="sm">
                  <CardContent>
                    <MiniGraph />
                  </CardContent>
                </Card>
              </section>
            </div>
          </>
        )}
      </SheetContent>
    </Sheet>
  )
}

function EmptyMemories() {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-xl border border-dashed bg-card py-16 text-center">
      <div className="rounded-full bg-muted p-3 text-muted-foreground">
        <DatabaseIcon className="size-6" />
      </div>
      <h3 className="text-base font-semibold">No memories yet</h3>
      <p className="max-w-sm text-sm text-muted-foreground">
        Add a memory through the Playground or via the API to see it here.
      </p>
      <Button asChild>
        <Link to="/playground">
          <PlayIcon />
          Open Playground
        </Link>
      </Button>
    </div>
  )
}

function getInitialFromQuery() {
  if (typeof window === "undefined") return { workspaceId: "" }
  const params = new URLSearchParams(window.location.search)
  return { workspaceId: params.get("workspace_id") ?? "" }
}

export default function MemoriesPage() {
  const initial = React.useMemo(getInitialFromQuery, [])
  const [userId, setUserId] = React.useState("")
  const [category, setCategory] = React.useState<string>("all")
  const [role, setRole] = React.useState<RoleFilter>("all")
  const [search, setSearch] = React.useState("")
  const [workspaceId, setWorkspaceId] = React.useState(initial.workspaceId)
  const [limit, setLimit] = React.useState<number>(25)
  const [offset, setOffset] = React.useState(0)
  const [openId, setOpenId] = React.useState<string | null>(null)

  const debouncedSearch = useDebouncedValue(search, 300)
  const debouncedUserId = useDebouncedValue(userId, 300)

  // Reset offset when filters change
  React.useEffect(() => {
    setOffset(0)
  }, [debouncedSearch, debouncedUserId, category, role, workspaceId, limit])

  const { data, loading, error, refetch } = useApi(
    () =>
      api.listMemories({
        user_id: debouncedUserId || undefined,
        category: category === "all" ? undefined : category,
        role: role === "all" ? undefined : role,
        workspace_id: workspaceId || undefined,
        search: debouncedSearch || undefined,
        limit,
        offset,
      }),
    [debouncedUserId, category, role, workspaceId, debouncedSearch, limit, offset],
  )

  const { data: stats } = useApi(() => api.stats(), [])
  const categoryOptions = React.useMemo(
    () => Object.keys(stats?.by_category ?? {}).sort(),
    [stats],
  )

  const items = data?.items ?? []
  const total = data?.total ?? 0
  const selected = items.find((m) => m.memory_id === openId) ?? null
  const startIdx = total === 0 ? 0 : offset + 1
  const endIdx = Math.min(offset + limit, total)

  const reset = () => {
    setSearch("")
    setUserId("")
    setCategory("all")
    setRole("all")
    setWorkspaceId("")
    setOffset(0)
  }

  return (
    <div className="flex flex-col gap-6 py-6">
      <div className="px-4">
        <h1 className="text-2xl font-semibold tracking-tight">Memories</h1>
        <p className="text-sm text-muted-foreground">
          Every message Memwire has stored across your users and agents.
        </p>
      </div>

      <div className="px-4">
        <Card className="sticky top-2 z-10">
          <CardContent>
            <div className="flex flex-wrap items-center gap-2">
              <InputGroup className="min-w-48 flex-1">
                <InputGroupAddon>
                  <SearchIcon />
                </InputGroupAddon>
                <InputGroupInput
                  placeholder="Search memories"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                />
                {search && (
                  <InputGroupAddon align="inline-end">
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon-xs"
                      onClick={() => setSearch("")}
                      aria-label="Clear search"
                    >
                      <XIcon />
                    </Button>
                  </InputGroupAddon>
                )}
              </InputGroup>
              <div className="relative">
                <Input
                  placeholder="Filter by user_id..."
                  value={userId}
                  onChange={(e) => setUserId(e.target.value)}
                  className="w-48 pr-8"
                />
                {userId && (
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon-xs"
                    onClick={() => setUserId("")}
                    aria-label="Clear user filter"
                    className="absolute right-1 top-1/2 -translate-y-1/2"
                  >
                    <XIcon />
                  </Button>
                )}
              </div>
              <Select
                value={category}
                onValueChange={(v) => setCategory(v)}
              >
                <SelectTrigger className="w-44">
                  <SelectValue placeholder="Category" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All categories</SelectItem>
                  {categoryOptions.map((c) => (
                    <SelectItem key={c} value={c} className="capitalize">
                      {c}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Select value={role} onValueChange={(v) => setRole(v as RoleFilter)}>
                <SelectTrigger className="w-36">
                  <SelectValue placeholder="Role" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All roles</SelectItem>
                  {ROLES.map((r) => (
                    <SelectItem key={r} value={r}>
                      {r}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Button
                variant="ghost"
                size="sm"
                onClick={reset}
                className="ml-auto"
              >
                <RotateCcwIcon />
                Reset
              </Button>
            </div>
            {workspaceId && (
              <div className="mt-2 flex items-center gap-2 text-xs text-muted-foreground">
                Filtered to workspace
                <code className="font-mono text-foreground">{workspaceId}</code>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon-xs"
                  onClick={() => setWorkspaceId("")}
                  aria-label="Clear workspace filter"
                >
                  <XIcon />
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <div className="px-4">
        <StatsStrip />
      </div>

      <div className="px-4">
        {error ? (
          <Alert variant="destructive">
            <AlertTitle>Couldn't load memories</AlertTitle>
            <AlertDescription className="flex items-center justify-between gap-3">
              <span>{error.message}</span>
              <Button variant="outline" size="sm" onClick={refetch}>
                <RotateCcwIcon />
                Retry
              </Button>
            </AlertDescription>
          </Alert>
        ) : !loading && total === 0 ? (
          <EmptyMemories />
        ) : (
          <Card>
            <CardContent className="px-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="pl-4">Memory ID</TableHead>
                    <TableHead>Excerpt</TableHead>
                    <TableHead>Role</TableHead>
                    <TableHead>Category</TableHead>
                    <TableHead className="w-40">Strength</TableHead>
                    <TableHead className="pr-4">Last accessed</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {loading
                    ? Array.from({ length: 8 }).map((_, i) => (
                        <TableRow key={i}>
                          <TableCell className="pl-4">
                            <Skeleton className="h-4 w-24" />
                          </TableCell>
                          <TableCell>
                            <Skeleton className="h-4 w-full max-w-md" />
                          </TableCell>
                          <TableCell>
                            <Skeleton className="h-5 w-12" />
                          </TableCell>
                          <TableCell>
                            <Skeleton className="h-5 w-16" />
                          </TableCell>
                          <TableCell>
                            <Skeleton className="h-2 w-24" />
                          </TableCell>
                          <TableCell className="pr-4">
                            <Skeleton className="h-3 w-20" />
                          </TableCell>
                        </TableRow>
                      ))
                    : items.map((m) => {
                        const tone = m.category ? categoryTone(m.category) : null
                        return (
                          <TableRow
                            key={m.memory_id}
                            className="cursor-pointer"
                            onClick={() => setOpenId(m.memory_id)}
                          >
                            <TableCell className="max-w-32 pl-4 font-mono text-xs">
                              <span className="block truncate">
                                {m.memory_id}
                              </span>
                            </TableCell>
                            <TableCell className="max-w-md">
                              <span className="block truncate text-sm">
                                {m.content}
                              </span>
                            </TableCell>
                            <TableCell>
                              <Badge variant="outline">{m.role}</Badge>
                            </TableCell>
                            <TableCell>
                              {tone && m.category ? (
                                <Badge
                                  variant={tone.variant}
                                  className={tone.cls}
                                >
                                  {m.category}
                                </Badge>
                              ) : (
                                <span className="text-xs text-muted-foreground">
                                  —
                                </span>
                              )}
                            </TableCell>
                            <TableCell>
                              <div className="flex items-center gap-2">
                                <Progress
                                  value={m.strength * 100}
                                  className="w-24"
                                />
                                <span className="text-xs tabular-nums text-muted-foreground">
                                  {m.strength.toFixed(2)}
                                </span>
                              </div>
                            </TableCell>
                            <TableCell className="pr-4 text-xs text-muted-foreground tabular-nums">
                              {formatRelative(m.timestamp)}
                            </TableCell>
                          </TableRow>
                        )
                      })}
                  {!loading && items.length === 0 && total > 0 && (
                    <TableRow>
                      <TableCell
                        colSpan={6}
                        className="py-10 text-center text-sm text-muted-foreground"
                      >
                        No memories on this page.
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        )}
      </div>

      {!error && total > 0 && (
        <div className="flex flex-wrap items-center justify-between gap-3 px-4">
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            Rows per page
            <Select
              value={limit.toString()}
              onValueChange={(v) => setLimit(Number(v))}
            >
              <SelectTrigger size="sm">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {PAGE_SIZES.map((n) => (
                  <SelectItem key={n} value={n.toString()}>
                    {n}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-xs text-muted-foreground tabular-nums">
              {startIdx}-{endIdx} of {total.toLocaleString()}
            </span>
            <div className="flex items-center gap-1">
              <Button
                variant="outline"
                size="icon-sm"
                onClick={() => setOffset((o) => Math.max(0, o - limit))}
                disabled={offset === 0}
                aria-label="Previous page"
              >
                <ChevronLeftIcon />
              </Button>
              <Button
                variant="outline"
                size="icon-sm"
                onClick={() => setOffset((o) => o + limit)}
                disabled={offset + limit >= total}
                aria-label="Next page"
              >
                <ChevronRightIcon />
              </Button>
            </div>
          </div>
        </div>
      )}

      <MemorySheet
        memory={selected}
        open={openId !== null}
        onOpenChange={(v) => !v && setOpenId(null)}
      />
    </div>
  )
}
