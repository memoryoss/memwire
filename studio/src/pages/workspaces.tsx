import * as React from "react"
import { Link } from "react-router-dom"
import {
  ActivityIcon,
  ArrowRightIcon,
  BookOpenCheckIcon,
  LayersIcon,
  MoreHorizontalIcon,
  NetworkIcon,
  RotateCcwIcon,
  UsersIcon,
} from "lucide-react"

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardAction,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Skeleton } from "@/components/ui/skeleton"
import { api, type Workspace } from "@/lib/api"
import { formatRelative } from "@/lib/format"
import { useApi } from "@/lib/use-api"

function workspaceLabel(ws: Workspace): string {
  return ws.workspace_id ?? "Default workspace"
}

function workspaceQuery(ws: Workspace): string {
  return ws.workspace_id ? `?workspace_id=${encodeURIComponent(ws.workspace_id)}` : ""
}

function MiniStat({
  icon: Icon,
  value,
  label,
}: {
  icon: React.ComponentType<{ className?: string }>
  value: string
  label: string
}) {
  return (
    <div className="flex flex-col gap-0.5">
      <div className="flex items-center gap-1 text-muted-foreground">
        <Icon className="size-3.5" />
      </div>
      <div className="text-base font-semibold tabular-nums">{value}</div>
      <div className="text-[11px] text-muted-foreground">{label}</div>
    </div>
  )
}

function WorkspaceCard({ workspace }: { workspace: Workspace }) {
  const isDefault = workspace.workspace_id === null
  const label = workspaceLabel(workspace)
  return (
    <Card className="group/workspace transition-shadow hover:ring-foreground/20">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <span
            className={
              isDefault
                ? "truncate"
                : "truncate font-mono text-sm"
            }
            title={label}
          >
            {label}
          </span>
          {isDefault && (
            <Badge variant="outline" className="text-muted-foreground">
              null
            </Badge>
          )}
        </CardTitle>
        <CardAction>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon-sm" aria-label="Workspace actions">
                <MoreHorizontalIcon />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem asChild>
                <Link to={`/memories${workspaceQuery(workspace)}`}>
                  <BookOpenCheckIcon />
                  View memories
                </Link>
              </DropdownMenuItem>
              <DropdownMenuItem asChild>
                <Link to={`/knowledge-graph${workspaceQuery(workspace)}`}>
                  <NetworkIcon />
                  View knowledge
                </Link>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </CardAction>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-3 gap-3">
          <MiniStat
            icon={BookOpenCheckIcon}
            value={workspace.memory_count.toLocaleString()}
            label="Memories"
          />
          <MiniStat
            icon={UsersIcon}
            value={workspace.user_count.toLocaleString()}
            label="Users"
          />
          <MiniStat
            icon={ActivityIcon}
            value={
              workspace.last_active
                ? formatRelative(workspace.last_active)
                : "—"
            }
            label="Last active"
          />
        </div>
      </CardContent>
      <CardFooter>
        <Button variant="ghost" size="sm" asChild className="ml-auto">
          <Link to={`/memories${workspaceQuery(workspace)}`}>
            View memories
            <ArrowRightIcon />
          </Link>
        </Button>
      </CardFooter>
    </Card>
  )
}

function CardSkeleton() {
  return (
    <Card>
      <CardHeader>
        <Skeleton className="h-5 w-40" />
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-3 gap-3">
          {[0, 1, 2].map((i) => (
            <div key={i} className="flex flex-col gap-1.5">
              <Skeleton className="h-3.5 w-3.5" />
              <Skeleton className="h-5 w-16" />
              <Skeleton className="h-3 w-12" />
            </div>
          ))}
        </div>
      </CardContent>
      <CardFooter>
        <Skeleton className="ml-auto h-8 w-32" />
      </CardFooter>
    </Card>
  )
}

function EmptyState() {
  return (
    <div className="mx-4 flex flex-col items-center justify-center gap-3 rounded-xl border border-dashed bg-card py-16 text-center">
      <div className="rounded-full bg-muted p-3 text-muted-foreground">
        <LayersIcon className="size-6" />
      </div>
      <h3 className="text-base font-semibold">No workspaces yet</h3>
      <p className="max-w-sm text-sm text-muted-foreground">
        Memories tagged with a workspace_id will appear here.
      </p>
    </div>
  )
}

export default function WorkspacesPage() {
  const { data, loading, error, refetch } = useApi(() => api.workspaces(), [])

  return (
    <div className="flex flex-col gap-6 py-6">
      <div className="px-4">
        <h1 className="text-2xl font-semibold tracking-tight">Workspaces</h1>
        <p className="text-sm text-muted-foreground">
          Distinct workspace scopes observed in your data.
        </p>
      </div>

      {error ? (
        <div className="px-4">
          <Alert variant="destructive">
            <AlertTitle>Couldn't load workspaces</AlertTitle>
            <AlertDescription className="flex items-center justify-between gap-3">
              <span>{error.message}</span>
              <Button variant="outline" size="sm" onClick={refetch}>
                <RotateCcwIcon />
                Retry
              </Button>
            </AlertDescription>
          </Alert>
        </div>
      ) : loading ? (
        <div className="grid gap-4 px-4 sm:grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
          {[0, 1, 2, 3, 4, 5].map((i) => (
            <CardSkeleton key={i} />
          ))}
        </div>
      ) : !data || data.items.length === 0 ? (
        <EmptyState />
      ) : (
        <div className="grid gap-4 px-4 sm:grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
          {data.items.map((ws) => (
            <WorkspaceCard
              key={ws.workspace_id ?? "__default__"}
              workspace={ws}
            />
          ))}
        </div>
      )}

    </div>
  )
}
