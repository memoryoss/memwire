import { StrictMode } from "react"
import { createRoot } from "react-dom/client"
import { RouterProvider } from "react-router-dom"
import { ThemeProvider } from "@/components/theme-provider"
import { TooltipProvider } from "@/components/ui/tooltip"
import { Toaster } from "@/components/ui/sonner"
import { AuthProvider } from "@/components/auth-provider"
import { AuthGate } from "@/components/auth-gate"
import { router } from "@/router"
import "./index.css"

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ThemeProvider defaultTheme="system">
      <TooltipProvider delayDuration={120}>
        <AuthProvider>
          <AuthGate>
            <RouterProvider router={router} />
          </AuthGate>
          <Toaster richColors closeButton />
        </AuthProvider>
      </TooltipProvider>
    </ThemeProvider>
  </StrictMode>,
)
