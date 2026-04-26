import * as React from "react"
import {
  ExpandIcon,
  PauseIcon,
  PlayIcon,
  WaypointsIcon,
  XIcon,
} from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent } from "@/components/ui/dialog"
import { Skeleton } from "@/components/ui/skeleton"
import { type GraphResponse } from "@/lib/api"
import { cn } from "@/lib/utils"

type Props = {
  data: GraphResponse | null
  loading: boolean
  className?: string
}

// Internal simulation node — extends GraphNode with physics state.
type SimNode = {
  id: string
  label: string
  x: number
  y: number
  vx: number
  vy: number
  radius: number
  fixed: boolean
  connections: number
  tier: 0 | 1 | 2
}

type SimEdge = { source: SimNode; target: SimNode; weight: number }

type Hover = { x: number; y: number; node: SimNode } | null

function truncate(s: string, n: number): string {
  if (!s) return ""
  return s.length > n ? `${s.slice(0, n - 1)}…` : s
}

function buildSim(data: GraphResponse, w: number, h: number): {
  nodes: SimNode[]
  edges: SimEdge[]
} {
  const cx = w / 2
  const cy = h / 2
  const nodes: SimNode[] = data.nodes.map((n, i) => {
    const angle = i * 2.399 + Math.random() * 0.4
    const r = 40 + Math.random() * Math.min(120, Math.min(w, h) * 0.3)
    const radius = Math.min(8 + Math.sqrt(Math.max(1, n.connections)) * 2, 16)
    return {
      id: n.node_id,
      label: n.token,
      x: cx + Math.cos(angle) * r,
      y: cy + Math.sin(angle) * r,
      vx: 0,
      vy: 0,
      radius,
      fixed: false,
      connections: n.connections,
      tier: 0, // assigned below
    }
  })

  // Tier nodes by connection count for color variants.
  const conns = nodes.map((n) => n.connections).sort((a, b) => a - b)
  const p66 = conns[Math.floor(conns.length * 0.66)] ?? 0
  const p33 = conns[Math.floor(conns.length * 0.33)] ?? 0
  for (const n of nodes) {
    n.tier = n.connections >= p66 ? 0 : n.connections >= p33 ? 1 : 2
  }

  const byId = new Map(nodes.map((n) => [n.id, n]))
  const edges: SimEdge[] = []
  for (const e of data.edges) {
    const s = byId.get(e.source_id)
    const t = byId.get(e.target_id)
    if (!s || !t || s === t) continue
    edges.push({ source: s, target: t, weight: e.weight })
  }
  return { nodes, edges }
}

function readThemeColors(): {
  edge: string
  label: string
  border: string
  tierFills: [string, string, string]
  tierBorders: [string, string, string]
} {
  if (typeof window === "undefined") {
    return {
      edge: "rgba(120,120,120,0.4)",
      label: "rgba(120,120,120,0.9)",
      border: "rgba(120,120,120,0.5)",
      tierFills: ["#1f1f1f", "#6b6b6b", "#c8c8c8"],
      tierBorders: ["#000000", "#4a4a4a", "#9a9a9a"],
    }
  }
  const styles = getComputedStyle(document.documentElement)
  const fg = styles.getPropertyValue("--foreground").trim() || "oklch(0.145 0 0)"
  const muted =
    styles.getPropertyValue("--muted-foreground").trim() || "oklch(0.556 0 0)"
  const border = styles.getPropertyValue("--border").trim() || "oklch(0.92 0 0)"
  const isDark = document.documentElement.classList.contains("dark")
  // Three monochrome tiers for nodes — derive from foreground at varying mix.
  const tierFills: [string, string, string] = isDark
    ? [
        "oklch(0.92 0 0)", // bright (high-degree)
        "oklch(0.65 0 0)", // mid
        "oklch(0.42 0 0)", // dim (low-degree)
      ]
    : [
        "oklch(0.18 0 0)", // dark (high-degree)
        "oklch(0.45 0 0)", // mid
        "oklch(0.72 0 0)", // light (low-degree)
      ]
  const tierBorders: [string, string, string] = isDark
    ? ["oklch(1 0 0)", "oklch(0.85 0 0)", "oklch(0.65 0 0)"]
    : ["oklch(0.05 0 0)", "oklch(0.25 0 0)", "oklch(0.55 0 0)"]
  return {
    edge: border,
    label: muted,
    border: fg,
    tierFills,
    tierBorders,
  }
}

type SimHandle = {
  start: () => void
  stop: () => void
  isRunning: () => boolean
  hover: () => Hover
  setHoverHandler: (cb: (h: Hover) => void) => void
}

function attachSimulation(
  canvas: HTMLCanvasElement,
  nodes: SimNode[],
  edges: SimEdge[],
  getRect: () => { width: number; height: number },
): SimHandle {
  const ctx = canvas.getContext("2d")
  if (!ctx) {
    return {
      start: () => {},
      stop: () => {},
      isRunning: () => false,
      hover: () => null,
      setHoverHandler: () => {},
    }
  }

  let raf = 0
  let running = false
  let hover: Hover = null
  let onHover: (h: Hover) => void = () => {}
  let dragNode: SimNode | null = null
  let isDragging = false
  let colors = readThemeColors()

  function resize() {
    const { width, height } = getRect()
    const dpr = window.devicePixelRatio || 1
    canvas.width = Math.max(1, Math.floor(width * dpr))
    canvas.height = Math.max(1, Math.floor(height * dpr))
    canvas.style.width = `${width}px`
    canvas.style.height = `${height}px`
    ctx!.setTransform(dpr, 0, 0, dpr, 0, 0)
  }

  function step() {
    const { width, height } = getRect()
    const padding = 20
    // Forces
    for (const n of nodes) {
      if (n.fixed) continue
      // gravity toward center
      n.vx += (width / 2 - n.x) * 0.002
      n.vy += (height / 2 - n.y) * 0.002
      // repulsion
      for (const o of nodes) {
        if (o === n) continue
        const dx = n.x - o.x
        const dy = n.y - o.y
        const dist = Math.sqrt(dx * dx + dy * dy) || 0.1
        const minDist = n.radius + o.radius + 25
        let force: number
        if (dist < minDist) {
          force = (minDist - dist) * 0.5
        } else {
          force = 1200 / (dist * dist)
        }
        n.vx += (dx / dist) * force
        n.vy += (dy / dist) * force
      }
    }
    // springs
    for (const e of edges) {
      const dx = e.target.x - e.source.x
      const dy = e.target.y - e.source.y
      const dist = Math.sqrt(dx * dx + dy * dy) || 1
      const ideal = 70 + e.source.radius + e.target.radius
      const force = (dist - ideal) * 0.015
      if (!e.source.fixed) {
        e.source.vx += (dx / dist) * force
        e.source.vy += (dy / dist) * force
      }
      if (!e.target.fixed) {
        e.target.vx -= (dx / dist) * force
        e.target.vy -= (dy / dist) * force
      }
    }
    // integrate + damp + clamp
    for (const n of nodes) {
      if (n.fixed) continue
      n.vx *= 0.8
      n.vy *= 0.8
      n.x += n.vx
      n.y += n.vy
      n.x = Math.max(padding + n.radius, Math.min(width - padding - n.radius, n.x))
      n.y = Math.max(padding + n.radius, Math.min(height - padding - n.radius, n.y))
    }
  }

  function draw() {
    const { width, height } = getRect()
    ctx!.clearRect(0, 0, width, height)
    // edges
    for (const e of edges) {
      const dx = e.target.x - e.source.x
      const dy = e.target.y - e.source.y
      const dist = Math.sqrt(dx * dx + dy * dy)
      if (dist < 1) continue
      const sx = e.source.x + (dx / dist) * e.source.radius
      const sy = e.source.y + (dy / dist) * e.source.radius
      const tx = e.target.x - (dx / dist) * e.target.radius
      const ty = e.target.y - (dy / dist) * e.target.radius
      const lw = Math.min(1 + (e.weight || 1) * 0.4, 3)
      ctx!.strokeStyle = colors.edge
      ctx!.globalAlpha = 0.5
      ctx!.lineWidth = lw
      ctx!.beginPath()
      ctx!.moveTo(sx, sy)
      ctx!.lineTo(tx, ty)
      ctx!.stroke()
    }
    ctx!.globalAlpha = 1
    // nodes
    for (const n of nodes) {
      const fill = colors.tierFills[n.tier]
      const border = colors.tierBorders[n.tier]
      ctx!.beginPath()
      ctx!.arc(n.x, n.y, n.radius, 0, Math.PI * 2)
      ctx!.fillStyle = fill
      ctx!.fill()
      ctx!.lineWidth = 1.5
      ctx!.strokeStyle = border
      ctx!.stroke()
      // label
      ctx!.font =
        '500 9px ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace'
      ctx!.fillStyle = colors.label
      ctx!.textAlign = "center"
      ctx!.textBaseline = "top"
      ctx!.fillText(truncate(n.label, 10), n.x, n.y + n.radius + 4)
    }
  }

  function loop() {
    step()
    draw()
    raf = requestAnimationFrame(loop)
  }

  function start() {
    if (running) return
    running = true
    raf = requestAnimationFrame(loop)
  }

  function stop() {
    running = false
    if (raf) cancelAnimationFrame(raf)
    raf = 0
  }

  function nodeAt(x: number, y: number): SimNode | null {
    for (let i = nodes.length - 1; i >= 0; i--) {
      const n = nodes[i]
      const dx = n.x - x
      const dy = n.y - y
      if (Math.sqrt(dx * dx + dy * dy) < n.radius + 5) return n
    }
    return null
  }

  function onMouseDown(e: MouseEvent) {
    const rect = canvas.getBoundingClientRect()
    const x = e.clientX - rect.left
    const y = e.clientY - rect.top
    const n = nodeAt(x, y)
    if (n) {
      isDragging = true
      dragNode = n
      n.fixed = true
    }
  }

  function onMouseMove(e: MouseEvent) {
    const rect = canvas.getBoundingClientRect()
    const x = e.clientX - rect.left
    const y = e.clientY - rect.top
    if (isDragging && dragNode) {
      dragNode.x = x
      dragNode.y = y
      dragNode.vx = 0
      dragNode.vy = 0
      hover = null
      onHover(null)
      return
    }
    const n = nodeAt(x, y)
    if (n) {
      hover = { x, y, node: n }
      canvas.style.cursor = "pointer"
    } else {
      hover = null
      canvas.style.cursor = "grab"
    }
    onHover(hover)
  }

  function onMouseUp() {
    if (dragNode) dragNode.fixed = false
    dragNode = null
    isDragging = false
  }

  function onMouseLeave() {
    if (dragNode) dragNode.fixed = false
    dragNode = null
    isDragging = false
    hover = null
    onHover(null)
  }

  function onThemeChange() {
    colors = readThemeColors()
  }

  // Observe theme changes via class on <html>
  const mo = new MutationObserver(onThemeChange)
  mo.observe(document.documentElement, { attributes: true, attributeFilter: ["class"] })

  resize()
  const ro = new ResizeObserver(() => resize())
  ro.observe(canvas.parentElement || canvas)

  canvas.addEventListener("mousedown", onMouseDown)
  canvas.addEventListener("mousemove", onMouseMove)
  canvas.addEventListener("mouseup", onMouseUp)
  canvas.addEventListener("mouseleave", onMouseLeave)

  // Cleanup on canvas removal — caller invokes stop() and we extend it.
  const origStop = stop
  return {
    start,
    stop: () => {
      origStop()
      mo.disconnect()
      ro.disconnect()
      canvas.removeEventListener("mousedown", onMouseDown)
      canvas.removeEventListener("mousemove", onMouseMove)
      canvas.removeEventListener("mouseup", onMouseUp)
      canvas.removeEventListener("mouseleave", onMouseLeave)
    },
    isRunning: () => running,
    hover: () => hover,
    setHoverHandler: (cb) => {
      onHover = cb
    },
  }
}

type SurfaceProps = {
  data: GraphResponse
  className?: string
  showOverlay?: boolean
  onExpand?: () => void
  showExpand?: boolean
  height?: number | string
}

function GraphSurface({
  data,
  className,
  onExpand,
  showExpand = true,
}: SurfaceProps) {
  const wrapRef = React.useRef<HTMLDivElement>(null)
  const canvasRef = React.useRef<HTMLCanvasElement>(null)
  const handleRef = React.useRef<SimHandle | null>(null)
  const [running, setRunning] = React.useState(true)
  const [tip, setTip] = React.useState<Hover>(null)

  React.useEffect(() => {
    const wrap = wrapRef.current
    const canvas = canvasRef.current
    if (!wrap || !canvas) return
    const { nodes, edges } = buildSim(
      data,
      wrap.clientWidth || 400,
      wrap.clientHeight || 300,
    )
    const handle = attachSimulation(canvas, nodes, edges, () => ({
      width: wrap.clientWidth,
      height: wrap.clientHeight,
    }))
    handle.setHoverHandler((h) => setTip(h))
    handle.start()
    handleRef.current = handle
    setRunning(true)
    return () => {
      handle.stop()
      handleRef.current = null
    }
  }, [data])

  function toggle() {
    const h = handleRef.current
    if (!h) return
    if (h.isRunning()) {
      h.stop()
      setRunning(false)
    } else {
      h.start()
      setRunning(true)
    }
  }

  return (
    <div
      ref={wrapRef}
      className={cn(
        "relative h-full w-full overflow-hidden rounded-md border bg-card",
        className,
      )}
    >
      <canvas ref={canvasRef} className="block h-full w-full" />

      {data.truncated && (
        <Badge
          variant="secondary"
          className="absolute right-2 bottom-2 font-mono text-[10px] tabular-nums"
        >
          {data.nodes.length} of {data.total_nodes}
        </Badge>
      )}

      <div className="absolute top-2 left-2 flex items-center gap-1.5">
        {showExpand && onExpand && (
          <Button
            variant="outline"
            size="icon-xs"
            onClick={onExpand}
            aria-label="Expand graph"
            className="bg-background/80 backdrop-blur-sm"
          >
            <ExpandIcon />
          </Button>
        )}
      </div>

      <div className="absolute top-2 right-2 flex items-center gap-1.5">
        <Button
          variant="outline"
          size="icon-xs"
          onClick={toggle}
          aria-label={running ? "Pause animation" : "Resume animation"}
          className="bg-background/80 backdrop-blur-sm"
        >
          {running ? <PauseIcon /> : <PlayIcon />}
        </Button>
      </div>

      {tip && (
        <div
          className="pointer-events-none absolute z-10 max-w-[180px] rounded-md border bg-popover px-2 py-1.5 text-[11px] text-popover-foreground shadow-sm"
          style={{
            left: Math.min(tip.x + 12, (wrapRef.current?.clientWidth ?? 0) - 190),
            top: Math.max(tip.y - 36, 4),
          }}
        >
          <div className="truncate font-mono font-medium">{tip.node.label}</div>
          <div className="text-[10px] text-muted-foreground tabular-nums">
            {tip.node.connections} connection
            {tip.node.connections === 1 ? "" : "s"}
          </div>
        </div>
      )}
    </div>
  )
}

export function GraphCanvas({ data, loading, className }: Props) {
  const [open, setOpen] = React.useState(false)

  if (loading) {
    return <Skeleton className={cn("h-[260px] w-full rounded-md", className)} />
  }

  if (!data || data.nodes.length === 0) {
    return (
      <div
        className={cn(
          "flex h-[260px] w-full flex-col items-center justify-center gap-2 rounded-md border border-dashed bg-muted/30 px-4 text-center",
          className,
        )}
      >
        <span className="inline-flex size-9 items-center justify-center rounded-full bg-muted text-muted-foreground">
          <WaypointsIcon className="size-4" />
        </span>
        <p className="text-xs font-medium">Graph builds as messages flow</p>
        <p className="max-w-[220px] text-[11px] leading-relaxed text-muted-foreground">
          Send a message to extract memories — tokens become nodes, displacement
          becomes edges.
        </p>
      </div>
    )
  }

  return (
    <>
      <div className={cn("h-[260px]", className)}>
        <GraphSurface data={data} onExpand={() => setOpen(true)} />
      </div>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent
          showCloseButton={false}
          className="max-w-[90vw] overflow-hidden p-0 sm:max-w-[90vw]"
        >
          <div className="relative h-[80vh] w-[90vw]">
            <div className="absolute top-3 left-3 z-20 flex items-center gap-2">
              <Badge variant="outline" className="gap-1.5 bg-background/80">
                <WaypointsIcon className="size-3" />
                <span className="font-medium">Displacement graph</span>
              </Badge>
              <Badge variant="secondary" className="font-mono text-[10px] tabular-nums">
                {data.nodes.length} nodes / {data.edges.length} edges
              </Badge>
            </div>
            <Button
              variant="outline"
              size="icon-sm"
              className="absolute top-3 right-3 z-20 bg-background/80 backdrop-blur-sm"
              onClick={() => setOpen(false)}
              aria-label="Close"
            >
              <XIcon />
            </Button>
            <GraphSurface data={data} showExpand={false} />
          </div>
        </DialogContent>
      </Dialog>
    </>
  )
}
