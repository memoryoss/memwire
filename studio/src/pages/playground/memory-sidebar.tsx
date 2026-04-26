import { DatabaseIcon, NotebookTextIcon, WaypointsIcon } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Skeleton } from "@/components/ui/skeleton"
import {
  type GraphResponse,
  type MemoryListResponse,
  api,
} from "@/lib/api"
import { categoryTone, formatRelative } from "@/lib/format"
import { useApi } from "@/lib/use-api"
import { cn } from "@/lib/utils"

import { GraphCanvas } from "./graph-canvas"

type Props = {
  userId: string
  refreshTick: number
}

// Logarithmic gauge — 0 mem -> 0%, 100 mem ~ 70%, 1000 ~ 100%.
function memorySaturation(total: number): number {
  if (total <= 0) return 0
  const v = Math.log10(total + 1) * 33.3
  return Math.max(4, Math.min(100, v))
}

export function MemorySidebar({ userId, refreshTick }: Props) {
  const memQuery = useApi<MemoryListResponse>(
    () => api.listMemories({ user_id: userId, limit: 20 }),
    [userId, refreshTick],
  )
  const graphQuery = useApi<GraphResponse>(
    () => api.graph(userId, 200),
    [userId, refreshTick],
  )

  const total = memQuery.data?.total ?? 0
  const items = memQuery.data?.items ?? []

  return (
    <div className="flex h-full min-h-0 flex-col gap-4">
      <Card size="sm">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-sm">
            <DatabaseIcon className="size-3.5" />
            Memory usage
          </CardTitle>
          <CardDescription className="text-xs">
            Indexed for{" "}
            <code className="font-mono text-foreground">{userId}</code>
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-2.5">
          {memQuery.loading && !memQuery.data ? (
            <>
              <Skeleton className="h-7 w-24" />
              <Skeleton className="h-1.5 w-full" />
            </>
          ) : (
            <>
              <div className="flex items-baseline gap-1.5">
                <span className="text-2xl font-semibold tabular-nums">
                  {total.toLocaleString()}
                </span>
                <span className="text-xs text-muted-foreground">
                  {total === 1 ? "memory" : "memories"}
                </span>
              </div>
              <Progress value={memorySaturation(total)} className="h-1" />
              <p className="text-[11px] text-muted-foreground">
                Indexed live in the displacement graph below.
              </p>
            </>
          )}
        </CardContent>
      </Card>

      <Card className="flex min-h-0 flex-1 flex-col">
        <CardHeader>
          <CardTitle className="flex items-center justify-between text-sm">
            <span className="flex items-center gap-2">
              <NotebookTextIcon className="size-3.5" />
              Extracted memories
            </span>
            <Badge variant="secondary" className="font-mono tabular-nums">
              {items.length}
            </Badge>
          </CardTitle>
          <CardDescription className="text-xs">
            Most recent first
          </CardDescription>
        </CardHeader>
        <CardContent className="flex min-h-0 flex-1 flex-col p-0">
          <ScrollArea className="h-[260px] px-4 pb-4">
            {memQuery.loading && !memQuery.data ? (
              <div className="space-y-2">
                <Skeleton className="h-14 w-full" />
                <Skeleton className="h-14 w-full" />
                <Skeleton className="h-14 w-full" />
              </div>
            ) : items.length === 0 ? (
              <div className="flex h-[220px] flex-col items-center justify-center gap-1.5 px-4 text-center">
                <span className="inline-flex size-9 items-center justify-center rounded-full bg-muted text-muted-foreground">
                  <NotebookTextIcon className="size-4" />
                </span>
                <p className="text-xs font-medium">No memories yet</p>
                <p className="max-w-[220px] text-[11px] text-muted-foreground">
                  Send a message to start indexing.
                </p>
              </div>
            ) : (
              <ul className="space-y-2">
                {items.map((m) => {
                  const tone = m.category ? categoryTone(m.category) : null
                  return (
                    <li
                      key={m.memory_id}
                      className="rounded-md border bg-card px-2.5 py-2"
                    >
                      <p
                        className="text-xs leading-snug text-foreground"
                        style={{
                          display: "-webkit-box",
                          WebkitLineClamp: 2,
                          WebkitBoxOrient: "vertical",
                          overflow: "hidden",
                        }}
                      >
                        {m.content}
                      </p>
                      <div className="mt-1.5 flex flex-wrap items-center gap-1.5 text-[10px] text-muted-foreground">
                        <Badge
                          variant="outline"
                          className="font-mono text-[10px]"
                        >
                          {m.role}
                        </Badge>
                        {tone && m.category && (
                          <Badge
                            variant={tone.variant}
                            className={cn("text-[10px]", tone.cls)}
                          >
                            {m.category}
                          </Badge>
                        )}
                        <span className="ml-auto tabular-nums">
                          {formatRelative(m.timestamp)}
                        </span>
                      </div>
                    </li>
                  )
                })}
              </ul>
            )}
          </ScrollArea>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between text-sm">
            <span className="flex items-center gap-2">
              <WaypointsIcon className="size-3.5" />
              Displacement graph
            </span>
            {graphQuery.data && (
              <Badge
                variant="secondary"
                className="font-mono text-[10px] tabular-nums"
              >
                {graphQuery.data.nodes.length}n / {graphQuery.data.edges.length}e
              </Badge>
            )}
          </CardTitle>
          <CardDescription className="text-xs">
            Tokens connected by co-occurrence
          </CardDescription>
        </CardHeader>
        <CardContent>
          <GraphCanvas
            data={graphQuery.data}
            loading={graphQuery.loading && !graphQuery.data}
          />
        </CardContent>
      </Card>
    </div>
  )
}
