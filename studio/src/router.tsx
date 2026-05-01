import { createBrowserRouter, Navigate } from "react-router-dom"
import { AppShell } from "@/components/layout/app-shell"
import DashboardPage from "@/pages/dashboard"
import WorkspacesPage from "@/pages/workspaces"
import KnowledgeGraphPage from "@/pages/knowledge-graph"
import MemoriesPage from "@/pages/memories"
import SetupInstallPage from "@/pages/setup-install"
import LlmProviderPage from "@/pages/setup-llm"
import PlaygroundPage from "@/pages/playground"
import ApiKeysPage from "@/pages/api-keys"
import { Placeholder } from "@/pages/placeholder"
import SettingsPage from "@/pages/settings"

export const router = createBrowserRouter(
  [
    {
      path: "/",
      element: <AppShell />,
      children: [
        { index: true, element: <Navigate to="/dashboard" replace /> },
        { path: "dashboard", element: <DashboardPage /> },
        { path: "workspaces", element: <WorkspacesPage /> },
        { path: "knowledge-graph", element: <KnowledgeGraphPage /> },
        { path: "memories", element: <MemoriesPage /> },
        { path: "setup/install", element: <SetupInstallPage /> },
        { path: "setup/llm", element: <LlmProviderPage /> },
        { path: "playground", element: <PlaygroundPage /> },
        { path: "api-keys", element: <ApiKeysPage /> },
        { path: "settings", element: <SettingsPage /> },
        { path: "*", element: <Placeholder title="Not found" /> },
      ],
    },
  ],
  { basename: "/studio" },
)
