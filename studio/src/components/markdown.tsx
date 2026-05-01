import * as React from "react"
import DOMPurify from "dompurify"
import { marked } from "marked"

import { cn } from "@/lib/utils"

marked.setOptions({ breaks: true, gfm: true })

type MarkdownProps = {
  text: string
  className?: string
}

// Sanitized markdown renderer. Styles applied via descendant selectors so we
// don't depend on the @tailwindcss/typography plugin.
export function Markdown({ text, className }: MarkdownProps) {
  const html = React.useMemo(() => {
    const raw = marked.parse(text, { async: false }) as string
    return DOMPurify.sanitize(raw, { USE_PROFILES: { html: true } })
  }, [text])

  return (
    <div
      className={cn(
        "text-sm leading-relaxed [&>*:first-child]:mt-0 [&>*:last-child]:mb-0",
        "[&_p]:my-2 [&_p]:leading-relaxed",
        "[&_ul]:my-2 [&_ul]:list-disc [&_ul]:pl-5",
        "[&_ol]:my-2 [&_ol]:list-decimal [&_ol]:pl-5",
        "[&_li]:my-0.5",
        "[&_h1]:mt-3 [&_h1]:mb-1.5 [&_h1]:text-base [&_h1]:font-semibold",
        "[&_h2]:mt-3 [&_h2]:mb-1.5 [&_h2]:text-sm [&_h2]:font-semibold",
        "[&_h3]:mt-2 [&_h3]:mb-1 [&_h3]:text-sm [&_h3]:font-semibold",
        "[&_strong]:font-semibold",
        "[&_em]:italic",
        "[&_a]:underline [&_a]:underline-offset-2 hover:[&_a]:text-foreground",
        "[&_code]:rounded-sm [&_code]:border [&_code]:bg-muted [&_code]:px-1 [&_code]:py-0.5 [&_code]:font-mono [&_code]:text-[12px]",
        "[&_pre]:my-2 [&_pre]:overflow-x-auto [&_pre]:rounded-md [&_pre]:border [&_pre]:bg-muted [&_pre]:px-3 [&_pre]:py-2 [&_pre]:text-[12px]",
        "[&_pre>code]:border-0 [&_pre>code]:bg-transparent [&_pre>code]:p-0",
        "[&_blockquote]:my-2 [&_blockquote]:border-l-2 [&_blockquote]:border-border [&_blockquote]:pl-3 [&_blockquote]:text-muted-foreground [&_blockquote]:italic",
        "[&_hr]:my-3 [&_hr]:border-border",
        "[&_table]:my-2 [&_table]:w-full [&_table]:border-collapse [&_table]:text-xs",
        "[&_th]:border [&_th]:border-border [&_th]:bg-muted [&_th]:px-2 [&_th]:py-1 [&_th]:text-left",
        "[&_td]:border [&_td]:border-border [&_td]:px-2 [&_td]:py-1",
        className,
      )}
      dangerouslySetInnerHTML={{ __html: html }}
    />
  )
}
