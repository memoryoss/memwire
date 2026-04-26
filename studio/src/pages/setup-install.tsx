import * as React from "react"
import { Link } from "react-router-dom"
import {
  ArrowRightIcon,
  ArrowUpRightIcon,
  BookOpenIcon,
  CheckIcon,
  CircleCheckIcon,
  KeyRoundIcon,
  PackageIcon,
  PlayIcon,
  ShieldCheckIcon,
  SparklesIcon,
  TerminalSquareIcon,
} from "lucide-react"

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs"
import { CodeBlock } from "@/components/code-block"
import { cn } from "@/lib/utils"

const installTabs = [
  {
    value: "pip",
    label: "pip",
    filename: "shell",
    code: `pip install "memwire[server]"
uvicorn memwire.server.app:create_app --factory --host 0.0.0.0 --port 8000`,
  },
  {
    value: "docker",
    label: "Docker",
    filename: "shell",
    code: `docker run -p 8000:8000 \\
  -e MEMWIRE_API_KEY=mw_live_changeme \\
  -v memwire-data:/var/lib/memwire \\
  ghcr.io/memwire/memwire:latest`,
  },
  {
    value: "compose",
    label: "docker-compose",
    filename: "docker-compose.yml",
    code: `services:
  memwire:
    image: ghcr.io/memwire/memwire:latest
    ports: ["8000:8000"]
    environment:
      MEMWIRE_API_KEY: mw_live_changeme
      QDRANT_URL: http://qdrant:6333
    depends_on: [qdrant]
    volumes: ["memwire-data:/var/lib/memwire"]
  qdrant:
    image: qdrant/qdrant:v1.12.4
    ports: ["6333:6333"]
    volumes: ["qdrant-data:/qdrant/storage"]

volumes:
  memwire-data:
  qdrant-data:`,
  },
] as const

const clientSnippets = [
  {
    title: "Python SDK",
    description: "Async client with typed responses.",
    icon: TerminalSquareIcon,
    filename: "client.py",
    code: `from memwire import Memwire

mw = Memwire(
    base_url="http://localhost:8000",
    api_key="mw_live_changeme",
    user_id="alice",
)

mw.add([{"role": "user", "content": "I prefer dark mode at night."}])

paths = mw.recall("what does alice prefer at night?")
for path in paths.supporting:
    print(path.tokens, path.score)`,
  },
  {
    title: "cURL",
    description: "Hit the REST surface directly.",
    icon: ArrowRightIcon,
    filename: "shell",
    code: `curl -X POST http://localhost:8000/v1/memories/recall \\
  -H "Content-Type: application/json" \\
  -H "X-API-Key: mw_live_changeme" \\
  -d '{
    "user_id": "alice",
    "query": "what does alice prefer at night?",
    "k": 8
  }'`,
  },
] as const

const requirements = [
  { label: "Python 3.10 or newer", hint: "CPython, free-threaded build supported" },
  { label: "Qdrant 1.12+", hint: "Local binary or container" },
  { label: "4 GB RAM recommended", hint: "Per worker, scales horizontally" },
  { label: "OpenSSL 1.1.1+", hint: "For TLS-bound deployments" },
] as const

const verifySteps = [
  {
    id: "v1",
    title: "Server boots",
    body: "Confirm GET /healthz returns 200 with {\"status\":\"ok\"}.",
  },
  {
    id: "v2",
    title: "API key works",
    body: "Send X-API-Key on POST /v1/memories/add and receive 201.",
  },
  {
    id: "v3",
    title: "Qdrant reachable",
    body: "Logs show \"qdrant: connected, 1 collection ready\" on first add.",
  },
  {
    id: "v4",
    title: "Recall round-trip",
    body: "POST /v1/memories/recall returns supporting paths within 250 ms.",
  },
] as const

const footerLinks = [
  {
    title: "Open Playground",
    description: "Try add, recall and search with mock data.",
    icon: PlayIcon,
    to: "/playground",
    external: false,
  },
  {
    title: "Generate API key",
    description: "Mint a scoped key for this deployment.",
    icon: KeyRoundIcon,
    to: "/api-keys",
    external: false,
  },
  {
    title: "Read the docs",
    description: "Architecture, endpoints, and SDK reference.",
    icon: BookOpenIcon,
    to: "https://github.com/memoryoss/memwire",
    external: true,
  },
] as const

function HeroCard() {
  return (
    <Card className="relative overflow-hidden">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 opacity-[0.35] [background-image:linear-gradient(to_right,var(--border)_1px,transparent_1px),linear-gradient(to_bottom,var(--border)_1px,transparent_1px)] [background-size:28px_28px] [mask-image:radial-gradient(ellipse_at_top_left,black,transparent_70%)]"
      />
      <div className="relative grid gap-6 px-6 py-6 lg:grid-cols-[1.4fr_1fr] lg:items-center">
        <div className="flex flex-col gap-4">
          <Badge variant="outline" className="gap-1.5 self-start">
            <SparklesIcon className="size-3" />
            v0.1.2 · self-hosted
          </Badge>
          <div className="space-y-2">
            <h2 className="font-heading text-2xl font-semibold tracking-tight text-balance">
              Self-hosted, graph-based memory for AI agents.
            </h2>
            <p className="max-w-xl text-sm text-muted-foreground">
              Token-level displacement vectors form a recall graph. No LLM
              calls in the hot path, just SQLite and Qdrant doing what they do
              best.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Button asChild size="lg">
              <Link to="/playground">
                <PlayIcon />
                Open Playground
              </Link>
            </Button>
            <Button asChild size="lg" variant="outline">
              <Link to="/api-keys">
                <KeyRoundIcon />
                Generate API Key
              </Link>
            </Button>
          </div>
        </div>
        <div className="hidden lg:block">
          <div className="rounded-lg border bg-background/80 p-4 shadow-sm backdrop-blur-sm">
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <span className="inline-flex size-2 rounded-full bg-foreground/70" />
              recall trace
              <span className="ml-auto font-mono tabular-nums">184ms · 7 hops</span>
            </div>
            <div className="mt-3 space-y-2">
              {[
                ["alice", "prefers", "dark mode"],
                ["alice", "works at", "night"],
                ["alice", "dislikes", "bright UI"],
              ].map((chain, i) => (
                <div
                  key={i}
                  className="flex items-center gap-1.5 overflow-x-auto"
                >
                  {chain.map((tok, j) => (
                    <React.Fragment key={tok}>
                      <Badge
                        variant="secondary"
                        className="font-mono text-[10.5px]"
                      >
                        {tok}
                      </Badge>
                      {j < chain.length - 1 && (
                        <ArrowRightIcon className="size-3 text-muted-foreground" />
                      )}
                    </React.Fragment>
                  ))}
                  <span className="ml-auto font-mono text-[10.5px] tabular-nums text-muted-foreground">
                    0.{93 - i * 7}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </Card>
  )
}

function InstallTabs() {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <PackageIcon className="size-4" />
          Install the server
        </CardTitle>
        <CardDescription>
          Pick the install path that fits your environment. All three serve the
          same REST surface on port 8000.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Tabs defaultValue="pip">
          <TabsList>
            {installTabs.map((t) => (
              <TabsTrigger key={t.value} value={t.value}>
                {t.label}
              </TabsTrigger>
            ))}
          </TabsList>
          {installTabs.map((t) => (
            <TabsContent key={t.value} value={t.value} className="mt-3">
              <CodeBlock
                code={t.code}
                language="bash"
                filename={t.filename}
              />
            </TabsContent>
          ))}
        </Tabs>
      </CardContent>
    </Card>
  )
}

function ConnectClient() {
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      {clientSnippets.map((c) => {
        const Icon = c.icon
        return (
          <Card key={c.title}>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Icon className="size-4" />
                {c.title}
              </CardTitle>
              <CardDescription>{c.description}</CardDescription>
            </CardHeader>
            <CardContent>
              <CodeBlock
                code={c.code}
                language={c.title === "cURL" ? "bash" : "python"}
                filename={c.filename}
              />
            </CardContent>
          </Card>
        )
      })}
    </div>
  )
}

function Requirements() {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <ShieldCheckIcon className="size-4" />
          Requirements
        </CardTitle>
        <CardDescription>
          Memwire is built to run on commodity infrastructure.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <ul className="grid gap-2 sm:grid-cols-2">
          {requirements.map((r) => (
            <li
              key={r.label}
              className="flex items-start gap-2.5 rounded-lg border bg-muted/30 px-3 py-2.5"
            >
              <span className="mt-0.5 inline-flex size-5 shrink-0 items-center justify-center rounded-md bg-foreground/10 text-foreground">
                <CheckIcon className="size-3" />
              </span>
              <div className="flex flex-col">
                <span className="text-sm font-medium">{r.label}</span>
                <span className="text-xs text-muted-foreground">{r.hint}</span>
              </div>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  )
}

function VerifyChecklist() {
  const [checked, setChecked] = React.useState<Record<string, boolean>>({})
  const completed = Object.values(checked).filter(Boolean).length
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <CircleCheckIcon className="size-4" />
          Verify your install
        </CardTitle>
        <CardDescription className="flex items-center justify-between gap-2">
          <span>Walk the smoke test before pointing real traffic at it.</span>
          <span className="font-mono text-xs tabular-nums text-muted-foreground">
            {completed}/{verifySteps.length}
          </span>
        </CardDescription>
      </CardHeader>
      <CardContent>
        <ol className="flex flex-col gap-2">
          {verifySteps.map((step, idx) => {
            const isOn = !!checked[step.id]
            return (
              <li
                key={step.id}
                className={cn(
                  "flex items-start gap-3 rounded-lg border bg-card px-3 py-2.5 transition-colors",
                  isOn && "bg-muted/50"
                )}
              >
                <Checkbox
                  id={step.id}
                  checked={isOn}
                  onCheckedChange={(v) =>
                    setChecked((prev) => ({ ...prev, [step.id]: v === true }))
                  }
                  className="mt-0.5"
                />
                <div className="flex flex-1 flex-col">
                  <label
                    htmlFor={step.id}
                    className={cn(
                      "flex items-center gap-2 text-sm font-medium",
                      isOn && "text-muted-foreground line-through"
                    )}
                  >
                    <span className="font-mono text-[11px] tabular-nums text-muted-foreground">
                      0{idx + 1}
                    </span>
                    {step.title}
                  </label>
                  <span className="text-xs text-muted-foreground">
                    {step.body}
                  </span>
                </div>
              </li>
            )
          })}
        </ol>
      </CardContent>
    </Card>
  )
}

function FooterLinks() {
  return (
    <div className="grid gap-4 lg:grid-cols-3">
      {footerLinks.map((link) => {
        const Icon = link.icon
        const inner = (
          <Card className="group/footer-link h-full transition-colors hover:bg-muted/40">
            <CardHeader>
              <div className="flex items-start justify-between gap-2">
                <div className="inline-flex size-8 items-center justify-center rounded-lg bg-muted text-foreground">
                  <Icon className="size-4" />
                </div>
                <ArrowUpRightIcon className="size-4 text-muted-foreground transition-transform group-hover/footer-link:-translate-y-0.5 group-hover/footer-link:translate-x-0.5" />
              </div>
              <CardTitle className="mt-2">{link.title}</CardTitle>
              <CardDescription>{link.description}</CardDescription>
            </CardHeader>
          </Card>
        )
        return link.external ? (
          <a
            key={link.title}
            href={link.to}
            target="_blank"
            rel="noreferrer noopener"
            className="block focus:outline-none focus-visible:ring-3 focus-visible:ring-ring/50 rounded-xl"
          >
            {inner}
          </a>
        ) : (
          <Link
            key={link.title}
            to={link.to}
            className="block focus:outline-none focus-visible:ring-3 focus-visible:ring-ring/50 rounded-xl"
          >
            {inner}
          </Link>
        )
      })}
    </div>
  )
}

export default function SetupInstallPage() {
  return (
    <div className="flex flex-col gap-6 py-6">
      <div className="px-4">
        <h1 className="text-2xl font-semibold tracking-tight">
          Install Memwire
        </h1>
        <p className="text-sm text-muted-foreground">
          Get a self-hosted memory layer running in under five minutes.
        </p>
      </div>
      <div className="px-4">
        <HeroCard />
      </div>
      <div className="px-4">
        <InstallTabs />
      </div>
      <div className="px-4">
        <ConnectClient />
      </div>
      <div className="grid gap-4 px-4 lg:grid-cols-2">
        <Requirements />
        <VerifyChecklist />
      </div>
      <div className="px-4">
        <FooterLinks />
      </div>
    </div>
  )
}
