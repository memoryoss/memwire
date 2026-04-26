import * as React from "react"

type Theme = "light" | "dark" | "system"

type ThemeProviderState = {
  theme: Theme
  setTheme: (theme: Theme) => void
  resolvedTheme: "light" | "dark"
}

const ThemeProviderContext = React.createContext<ThemeProviderState | undefined>(
  undefined,
)

const STORAGE_KEY = "memwire-ui-theme"

function getSystemTheme(): "light" | "dark" {
  if (typeof window === "undefined") return "light"
  return window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light"
}

export function ThemeProvider({
  children,
  defaultTheme = "system",
}: {
  children: React.ReactNode
  defaultTheme?: Theme
}) {
  const [theme, setThemeState] = React.useState<Theme>(() => {
    if (typeof window === "undefined") return defaultTheme
    return (localStorage.getItem(STORAGE_KEY) as Theme) || defaultTheme
  })

  const [resolvedTheme, setResolvedTheme] = React.useState<"light" | "dark">(
    () => (theme === "system" ? getSystemTheme() : theme),
  )

  React.useEffect(() => {
    const root = window.document.documentElement
    const next = theme === "system" ? getSystemTheme() : theme
    root.classList.remove("light", "dark")
    root.classList.add(next)
    setResolvedTheme(next)
  }, [theme])

  React.useEffect(() => {
    if (theme !== "system") return
    const media = window.matchMedia("(prefers-color-scheme: dark)")
    const handler = () => {
      const next = media.matches ? "dark" : "light"
      const root = window.document.documentElement
      root.classList.remove("light", "dark")
      root.classList.add(next)
      setResolvedTheme(next)
    }
    media.addEventListener("change", handler)
    return () => media.removeEventListener("change", handler)
  }, [theme])

  const setTheme = React.useCallback((value: Theme) => {
    localStorage.setItem(STORAGE_KEY, value)
    setThemeState(value)
  }, [])

  const value = React.useMemo(
    () => ({ theme, setTheme, resolvedTheme }),
    [theme, setTheme, resolvedTheme],
  )

  return (
    <ThemeProviderContext.Provider value={value}>
      {children}
    </ThemeProviderContext.Provider>
  )
}

export function useTheme() {
  const ctx = React.useContext(ThemeProviderContext)
  if (!ctx) throw new Error("useTheme must be used within ThemeProvider")
  return ctx
}
