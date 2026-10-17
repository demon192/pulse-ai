import { useCallback, useEffect, useRef, useState } from 'react'

import { ApiError } from '@/services/api'

export interface AsyncState<T> {
  data: T | null
  error: string | null
  status: number | null
  loading: boolean
  /** True only on the first load, so refreshes do not blank the screen. */
  initialLoading: boolean
  reload: () => Promise<void>
  setData: (value: T) => void
}

/**
 * Fetches once on mount (and whenever a dependency changes) with optional
 * polling. Keeps the previous data visible while refreshing.
 */
export function useAsync<T>(
  loader: () => Promise<T>,
  deps: ReadonlyArray<unknown> = [],
  options: { pollMs?: number; enabled?: boolean } = {},
): AsyncState<T> {
  const { pollMs, enabled = true } = options
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [status, setStatus] = useState<number | null>(null)
  const [loading, setLoading] = useState(enabled)
  const [loadedOnce, setLoadedOnce] = useState(false)
  const loaderRef = useRef(loader)
  loaderRef.current = loader
  const mounted = useRef(true)

  useEffect(() => {
    mounted.current = true
    return () => {
      mounted.current = false
    }
  }, [])

  const run = useCallback(async () => {
    if (!enabled) return
    setLoading(true)
    try {
      const result = await loaderRef.current()
      if (!mounted.current) return
      setData(result)
      setError(null)
      setStatus(null)
    } catch (caught) {
      if (!mounted.current) return
      const apiError = caught instanceof ApiError ? caught : null
      setError(apiError?.message ?? 'Something went wrong.')
      setStatus(apiError?.status ?? null)
    } finally {
      if (mounted.current) {
        setLoading(false)
        setLoadedOnce(true)
      }
    }
  }, [enabled])

  useEffect(() => {
    void run()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [run, ...deps])

  useEffect(() => {
    if (!pollMs || !enabled) return
    const timer = window.setInterval(() => void run(), pollMs)
    return () => window.clearInterval(timer)
  }, [pollMs, enabled, run])

  return {
    data,
    error,
    status,
    loading,
    initialLoading: loading && !loadedOnce,
    reload: run,
    setData,
  }
}
