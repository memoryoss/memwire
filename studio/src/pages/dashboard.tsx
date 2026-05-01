import * as React from "react"
import { Link } from "react-router-dom"
import {
  ActivityIcon,
  BookOpenCheckIcon,
  DatabaseIcon,
  FileTextIcon,
  NetworkIcon,
  PlayIcon,
  RotateCcwIcon,
  SparklesIcon,
  TrendingDownIcon,
  TrendingUpIcon,
  UsersIcon,
} from "lucide-react"
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  XAxis,
  YAxis,
} from "recharts"

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart"
import { Skeleton } from "@/components/ui/skeleton"
import {
  type ActivityItem,
  type DashboardStats,
  api,
} from "@/lib/api"
import { categoryTone, formatRelative, formatShortDate } from "@/lib/format"
import { useApi } from "@/lib/use-api"

const memoryConfig = {
  count: { label: "Memories", color: "var(--chart-1)" },
} satisfies ChartConfig

const categoryConfig = {
  count: { label: "Memories", color: "var(--chart-2)" },
} satisfies ChartConfig

type SectionCardProps = {
  label: string
  value: number
  hint: string
  delta: number | null
  icon: React.ComponentType<{ className?: string }>
}

function deriveDelta(timeseries: { ts: number; count: number }[]): number | null {
  if (!timeseries || timeseries.length < 2) return null
  const last = timeseries[timeseries.length - 1]
  const prev = timeseries[timeseries.length - 2]
  if (!last || !prev || prev.count === 0) return null
  return ((last.count - prev.count) / prev.count) * 100
}

function SectionCard({ label, value, hint, delta, icon: Icon }: SectionCardProps) {
  const showTrend = delta !== null && Number.isFinite(delta)
  const TrendIcon =
    showTrend && (delta as number) >= 0 ? TrendingUpIcon : TrendingDownIcon
  return (
    <Card className="@container/card">
      <CardHeader>
        <CardDescription className="flex items-center gap-2">
          <Icon className="size-4" />
          {label}
        </CardDescription>
        <CardTitle className="text-2xl font-semibold tabular-nums @[200px]/card:text-3xl">
          {value.toLocaleString()}
        </CardTitle>
        <CardAction>
          {showTrend ? (
            <Badge variant="outline" className="gap-1 tabular-nums">
              <TrendIcon className="size-3" />
              {(delta as number) >= 0 ? "+" : ""}
              {(delta as number).toFixed(1)}%
            </Badge>
          ) : (
            <Badge variant="outline" className="text-muted-foreground">
              Last 14 days
            </Badge>
          )}
        </CardAction>
      </CardHeader>
      <CardFooter className="flex-col items-start gap-1 text-sm">
        <div className="text-xs text-muted-foreground">{hint}</div>
      </CardFooter>
    </Card>
  )
}

function SectionCardSkeleton() {
  return (
    <Card>
      <CardHeader>
        <Skeleton className="h-4 w-32" />
        <Skeleton className="mt-2 h-8 w-24" />
      </CardHeader>
      <CardFooter>
        <Skeleton className="h-3 w-48" />
      </CardFooter>
    </Card>
  )
}

function MemoryAreaChart({ stats }: { stats: DashboardStats }) {
  const data = (stats.timeseries ?? []).map((p) => ({
    date: formatShortDate(p.ts),
    count: p.count,
  }))
  return (
    <Card className="@container/card">
      <CardHeader>
        <CardTitle>Memories added</CardTitle>
        <CardDescription>Last 14 days</CardDescription>
      </CardHeader>
      <CardContent>
        {data.length === 0 ? (
          <div className="flex h-[260px] items-center justify-center text-sm text-muted-foreground">
            No timeseries data yet.
          </div>
        ) : (
          <ChartContainer config={memoryConfig} className="aspect-auto h-[260px] w-full">
            <AreaChart data={data} margin={{ left: 8, right: 8, top: 8 }}>
              <defs>
                <linearGradient id="fillMemoryCount" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="var(--color-count)" stopOpacity={0.8} />
                  <stop offset="95%" stopColor="var(--color-count)" stopOpacity={0.05} />
                </linearGradient>
              </defs>
              <CartesianGrid vertical={false} strokeDasharray="3 3" />
              <XAxis dataKey="date" tickLine={false} axisLine={false} tickMargin={8} />
              <YAxis tickLine={false} axisLine={false} tickMargin={8} width={40} allowDecimals={false} />
              <ChartTooltip cursor={false} content={<ChartTooltipContent />} />
              <Area
                dataKey="count"
                type="monotone"
                stroke="var(--color-count)"
                fill="url(#fillMemoryCount)"
                strokeWidth={2}
              />
            </AreaChart>
          </ChartContainer>
        )}
      </CardContent>
    </Card>
  )
}

function CategoryBarChart({ stats }: { stats: DashboardStats }) {
  const entries = Object.entries(stats.by_category ?? {})
    .sort((a, b) => b[1] - a[1])
    .slice(0, 6)
    .map(([category, count]) => ({ category, count }))
  return (
    <Card className="@container/card">
      <CardHeader>
        <CardTitle>By category</CardTitle>
        <CardDescription>Top categories across all memories</CardDescription>
      </CardHeader>
      <CardContent>
        {entries.length === 0 ? (
          <div className="flex h-[260px] items-center justify-center text-sm text-muted-foreground">
            No categorized memories yet.
          </div>
        ) : (
          <ChartContainer config={categoryConfig} className="aspect-auto h-[260px] w-full">
            <BarChart
              data={entries}
              layout="vertical"
              margin={{ left: 8, right: 16, top: 8, bottom: 8 }}
            >
              <CartesianGrid horizontal={false} strokeDasharray="3 3" />
              <XAxis type="number" tickLine={false} axisLine={false} allowDecimals={false} />
              <YAxis
                type="category"
                dataKey="category"
                tickLine={false}
                axisLine={false}
                width={100}
                tickFormatter={(v: string) => v}
              />
              <ChartTooltip cursor={false} content={<ChartTooltipContent />} />
              <Bar
                dataKey="count"
                fill="var(--color-count)"
                radius={[0, 4, 4, 0]}
              />
            </BarChart>
          </ChartContainer>
        )}
      </CardContent>
    </Card>
  )
}

function ChartSkeleton() {
  return (
    <Card>
      <CardHeader>
        <Skeleton className="h-5 w-40" />
        <Skeleton className="mt-1.5 h-3 w-28" />
      </CardHeader>
      <CardContent>
        <Skeleton className="h-[260px] w-full" />
      </CardContent>
    </Card>
  )
}

function ActivityIconFor({ type }: { type: string }) {
  if (type === "knowledge_ingested") {
    return (
      <span className="inline-flex size-7 shrink-0 items-center justify-center rounded-md bg-muted text-muted-foreground">
        <FileTextIcon className="size-3.5" />
      </span>
    )
  }
  return (
    <span className="inline-flex size-7 shrink-0 items-center justify-center rounded-md bg-muted text-muted-foreground">
      <BookOpenCheckIcon className="size-3.5" />
    </span>
  )
}

function ActivityRow({ item }: { item: ActivityItem }) {
  const tone = item.category ? categoryTone(item.category) : null
  return (
    <li className="flex items-start gap-3 py-3">
      <ActivityIconFor type={item.type} />
      <div className="flex flex-1 flex-col gap-1">
        <p className="text-sm leading-snug">{item.summary}</p>
        <div className="flex flex-wrap items-center gap-1.5 text-[11px] text-muted-foreground">
          <code className="font-mono">{item.user_id}</code>
          {tone && item.category && (
            <Badge variant={tone.variant} className={tone.cls}>
              {item.category}
            </Badge>
          )}
          {item.role && (
            <Badge variant="outline" className="text-muted-foreground">
              {item.role}
            </Badge>
          )}
          <span className="ml-auto tabular-nums">
            {formatRelative(item.timestamp)}
          </span>
        </div>
      </div>
    </li>
  )
}

function RecentActivityCard() {
  const { data, loading, error, refetch } = useApi(() => api.activity(10), [])
  return (
    <Card>
      <CardHeader>
        <CardTitle>Recent activity</CardTitle>
        <CardDescription>The latest events across your deployment</CardDescription>
        <CardAction>
          <Button variant="ghost" size="icon-sm" onClick={refetch} aria-label="Refresh activity">
            <RotateCcwIcon />
          </Button>
        </CardAction>
      </CardHeader>
      <CardContent>
        {error ? (
          <Alert variant="destructive">
            <AlertTitle>Couldn't load activity</AlertTitle>
            <AlertDescription>{error.message}</AlertDescription>
          </Alert>
        ) : loading ? (
          <ul className="divide-y divide-border">
            {[0, 1, 2, 3, 4].map((i) => (
              <li key={i} className="flex items-start gap-3 py-3">
                <Skeleton className="size-7 rounded-md" />
                <div className="flex flex-1 flex-col gap-1.5">
                  <Skeleton className="h-4 w-3/4" />
                  <Skeleton className="h-3 w-1/3" />
                </div>
              </li>
            ))}
          </ul>
        ) : !data || data.items.length === 0 ? (
          <div className="flex flex-col items-center justify-center gap-2 py-8 text-center">
            <span className="inline-flex size-9 items-center justify-center rounded-full bg-muted text-muted-foreground">
              <ActivityIcon className="size-4" />
            </span>
            <p className="text-sm font-medium">No activity yet</p>
            <p className="text-xs text-muted-foreground">
              Once users add memories or ingest knowledge, you'll see it here.
            </p>
          </div>
        ) : (
          <ul className="divide-y divide-border">
            {data.items.map((item, i) => (
              <ActivityRow key={`${item.related_id}-${i}`} item={item} />
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  )
}

function EmptyDeploymentState() {
  return (
    <div className="mx-4 flex flex-col items-center justify-center gap-3 rounded-xl border border-dashed bg-card py-20 text-center">
      <div className="rounded-full bg-muted p-3 text-muted-foreground">
        <DatabaseIcon className="size-6" />
      </div>
      <h3 className="text-base font-semibold">No data yet</h3>
      <p className="max-w-sm text-sm text-muted-foreground">
        Add a memory or ingest a document to see your deployment come to life.
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

export default function DashboardPage() {
  const { data, loading, error, refetch } = useApi(() => api.stats(), [])

  const delta = data ? deriveDelta(data.timeseries) : null

  const cards: SectionCardProps[] = data
    ? [
        {
          label: "Total memories",
          value: data.total_memories,
          hint: "User + agent messages stored across all workspaces",
          delta,
          icon: BookOpenCheckIcon,
        },
        {
          label: "Distinct users",
          value: data.distinct_users,
          hint: "Unique user_ids observed in your data",
          delta: null,
          icon: UsersIcon,
        },
        {
          label: "Graph nodes",
          value: data.total_nodes,
          hint: `${data.total_edges.toLocaleString()} edges · ${data.total_anchors.toLocaleString()} anchors`,
          delta: null,
          icon: NetworkIcon,
        },
        {
          label: "Knowledge bases",
          value: data.total_knowledge_bases,
          hint: "Documents ingested into hybrid retrieval",
          delta: null,
          icon: SparklesIcon,
        },
      ]
    : []

  return (
    <div className="flex flex-col gap-6 py-6">
      <div className="flex items-start justify-between gap-3 px-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
          <p className="text-sm text-muted-foreground">
            Live overview of your Memwire deployment.
          </p>
        </div>
        {data && (
          <Button variant="ghost" size="sm" onClick={refetch}>
            <RotateCcwIcon />
            Refresh
          </Button>
        )}
      </div>

      {error ? (
        <div className="px-4">
          <Alert variant="destructive">
            <AlertTitle>Couldn't load dashboard</AlertTitle>
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
        <>
          <div className="grid gap-4 px-4 lg:grid-cols-2 xl:grid-cols-4">
            {[0, 1, 2, 3].map((i) => (
              <SectionCardSkeleton key={i} />
            ))}
          </div>
          <div className="grid gap-4 px-4 lg:grid-cols-2">
            <ChartSkeleton />
            <ChartSkeleton />
          </div>
        </>
      ) : data && data.total_memories === 0 ? (
        <EmptyDeploymentState />
      ) : data ? (
        <>
          <div className="grid gap-4 px-4 lg:grid-cols-2 xl:grid-cols-4">
            {cards.map((c) => (
              <SectionCard key={c.label} {...c} />
            ))}
          </div>
          <div className="grid gap-4 px-4 lg:grid-cols-2">
            <MemoryAreaChart stats={data} />
            <CategoryBarChart stats={data} />
          </div>
          <div className="px-4">
            <RecentActivityCard />
          </div>
        </>
      ) : null}
    </div>
  )
}
