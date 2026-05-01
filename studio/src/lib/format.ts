// Date and tone formatting helpers used across pages.

const MONTHS = [
  "Jan",
  "Feb",
  "Mar",
  "Apr",
  "May",
  "Jun",
  "Jul",
  "Aug",
  "Sep",
  "Oct",
  "Nov",
  "Dec",
]

// Server timestamps are seconds-since-epoch (floats). Accept ms too.
function toDate(ts: number): Date {
  if (!Number.isFinite(ts)) return new Date(0)
  // Heuristic: anything below year 3000 in seconds (< 3.2e10) treated as seconds
  return new Date(ts < 1e12 ? ts * 1000 : ts)
}

export function formatRelative(ts: number, now: Date = new Date()): string {
  const d = toDate(ts)
  const diffMs = now.getTime() - d.getTime()
  if (!Number.isFinite(diffMs)) return ""
  const future = diffMs < 0
  const abs = Math.abs(diffMs)
  const sec = Math.round(abs / 1000)
  const min = Math.round(sec / 60)
  const hr = Math.round(min / 60)
  const day = Math.round(hr / 24)

  if (sec < 45) return future ? "in a moment" : "just now"
  if (min < 2) return future ? "in a minute" : "a minute ago"
  if (min < 60) return future ? `in ${min} minutes` : `${min} minutes ago`
  if (hr < 2) return future ? "in an hour" : "an hour ago"
  if (hr < 24) return future ? `in ${hr} hours` : `${hr} hours ago`
  if (day === 1) return future ? "tomorrow" : "yesterday"
  if (day < 7) return future ? `in ${day} days` : `${day} days ago`
  // Fall back to short date label, e.g. "Apr 14"
  return formatShortDate(ts)
}

export function formatShortDate(ts: number): string {
  const d = toDate(ts)
  return `${MONTHS[d.getMonth()]} ${d.getDate()}`
}

export function formatDateTime(ts: number): string {
  const d = toDate(ts)
  const hh = d.getHours().toString().padStart(2, "0")
  const mm = d.getMinutes().toString().padStart(2, "0")
  return `${formatShortDate(ts)}, ${hh}:${mm}`
}

// Deterministic hash of a string into a small integer.
function hashString(s: string): number {
  let h = 0
  for (let i = 0; i < s.length; i++) {
    h = (h * 31 + s.charCodeAt(i)) | 0
  }
  return Math.abs(h)
}

// Six token-based tones for category badges. Variant + foreground opacity tier.
const CATEGORY_TONES: Array<{ variant: "secondary" | "outline"; cls: string }> =
  [
    { variant: "outline", cls: "text-foreground" },
    { variant: "outline", cls: "text-foreground/80" },
    { variant: "outline", cls: "text-foreground/70" },
    { variant: "secondary", cls: "text-foreground" },
    { variant: "secondary", cls: "text-foreground/80" },
    { variant: "secondary", cls: "text-foreground/70" },
  ]

export function categoryTone(input: string | null | undefined) {
  const key = (input ?? "uncategorized").toLowerCase()
  const idx = hashString(key) % CATEGORY_TONES.length
  return CATEGORY_TONES[idx]
}
