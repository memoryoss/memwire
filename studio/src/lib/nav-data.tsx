import {
  BookOpenIcon,
  CpuIcon,
  DownloadIcon,
  GaugeIcon,
  KeyRoundIcon,
  LayersIcon,
  LayoutDashboardIcon,
  NetworkIcon,
  TerminalSquareIcon,
} from "lucide-react"
import type { ReactNode } from "react"

export type NavItem = {
  title: string
  url: string
  icon: ReactNode
}

export type NavGroup = {
  label: string
  items: NavItem[]
}

export const navGroups: NavGroup[] = [
  {
    label: "Setup",
    items: [
      {
        title: "Install Memwire",
        url: "/setup/install",
        icon: <DownloadIcon />,
      },
      {
        title: "LLM Provider",
        url: "/setup/llm",
        icon: <CpuIcon />,
      },
      {
        title: "Playground",
        url: "/playground",
        icon: <TerminalSquareIcon />,
      },
      {
        title: "API Keys",
        url: "/api-keys",
        icon: <KeyRoundIcon />,
      },
    ],
  },
  {
    label: "Studio",
    items: [
      {
        title: "Dashboard",
        url: "/dashboard",
        icon: <LayoutDashboardIcon />,
      },
      {
        title: "Workspaces",
        url: "/workspaces",
        icon: <LayersIcon />,
      },
      {
        title: "Knowledge Graph",
        url: "/knowledge-graph",
        icon: <NetworkIcon />,
      },
      {
        title: "Memories",
        url: "/memories",
        icon: <BookOpenIcon />,
      },
    ],
  },
]

export const allNavItems: NavItem[] = navGroups.flatMap((g) => g.items)

export const settingsNav: NavItem = {
  title: "Settings",
  url: "/settings",
  icon: <GaugeIcon />,
}
