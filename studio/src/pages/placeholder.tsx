import { ConstructionIcon } from "lucide-react"

export function Placeholder({ title }: { title: string }) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-3 p-12 text-center">
      <div className="rounded-full bg-muted p-3 text-muted-foreground">
        <ConstructionIcon className="size-6" />
      </div>
      <h1 className="text-xl font-semibold tracking-tight">{title}</h1>
      <p className="max-w-md text-sm text-muted-foreground">
        This page is being designed. The Studio dashboard, sidebar, and theme
        toggle are wired and ready for content.
      </p>
    </div>
  )
}
