import * as React from "react"
import { CheckIcon, CopyIcon } from "lucide-react"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

type CodeBlockProps = {
  code: string
  language?: string
  className?: string
  filename?: string
}

export function CodeBlock({
  code,
  language = "bash",
  className,
  filename,
}: CodeBlockProps) {
  const [copied, setCopied] = React.useState(false)

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(code)
      setCopied(true)
      toast.success("Copied", {
        description: filename ?? `${language} snippet copied to clipboard`,
      })
      window.setTimeout(() => setCopied(false), 1400)
    } catch {
      toast.error("Copy failed")
    }
  }

  return (
    <div
      className={cn(
        "group/code relative overflow-hidden rounded-lg border bg-muted/40",
        className
      )}
    >
      <div className="flex items-center justify-between border-b bg-muted/60 px-3 py-1.5">
        <div className="flex items-center gap-2 text-[11px] font-medium tracking-wide text-muted-foreground uppercase">
          <span className="inline-flex size-1.5 rounded-full bg-muted-foreground/60" />
          {filename ?? language}
        </div>
        <Button
          type="button"
          variant="ghost"
          size="icon-xs"
          onClick={handleCopy}
          aria-label="Copy code"
        >
          {copied ? <CheckIcon /> : <CopyIcon />}
        </Button>
      </div>
      <pre className="overflow-x-auto px-3 py-3 font-mono text-[12.5px] leading-relaxed text-foreground">
        <code>{code}</code>
      </pre>
    </div>
  )
}
