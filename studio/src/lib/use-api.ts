import * as React from "react"
import { ApiError } from "@/lib/api"

type State<T> = {
  data: T | null
  loading: boolean
  error: ApiError | null
}

export function useApi<T>(
  fn: () => Promise<T>,
  deps: React.DependencyList = [],
) {
  const [state, setState] = React.useState<State<T>>({
    data: null,
    loading: true,
    error: null,
  })
  const [reload, setReload] = React.useState(0)

  // store fn in a ref so callers don't need to memoize it
  const fnRef = React.useRef(fn)
  fnRef.current = fn

  React.useEffect(() => {
    let cancelled = false
    setState((s) => ({ ...s, loading: true, error: null }))
    fnRef
      .current()
      .then((data) => {
        if (!cancelled) setState({ data, loading: false, error: null })
      })
      .catch((err) => {
        if (cancelled) return
        const apiErr =
          err instanceof ApiError
            ? err
            : new ApiError(err?.message ?? "Unknown error", 0)
        setState({ data: null, loading: false, error: apiErr })
      })
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, reload])

  const refetch = React.useCallback(() => setReload((n) => n + 1), [])
  return { ...state, refetch }
}
