import * as React from "react"
import { getApiKey, setApiKey as persistApiKey } from "@/lib/api"

type AuthContextValue = {
  apiKey: string | null
  hasKey: boolean
  setApiKey: (key: string | null) => void
}

const AuthContext = React.createContext<AuthContextValue | undefined>(undefined)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [apiKey, setKeyState] = React.useState<string | null>(() => getApiKey())

  React.useEffect(() => {
    const handler = () => setKeyState(getApiKey())
    window.addEventListener("mw:auth-changed", handler)
    window.addEventListener("storage", handler)
    return () => {
      window.removeEventListener("mw:auth-changed", handler)
      window.removeEventListener("storage", handler)
    }
  }, [])

  const setApiKey = React.useCallback((key: string | null) => {
    persistApiKey(key)
    setKeyState(key)
  }, [])

  const value = React.useMemo(
    () => ({ apiKey, hasKey: !!apiKey, setApiKey }),
    [apiKey, setApiKey],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = React.useContext(AuthContext)
  if (!ctx) throw new Error("useAuth must be used within AuthProvider")
  return ctx
}
