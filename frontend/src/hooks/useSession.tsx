import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'

import { api, getPersonaId, setPersonaId } from '@/services/api'
import type { SessionInfo } from '@/types/api'

interface SessionContextValue {
  session: SessionInfo | null
  loading: boolean
  error: string | null
  switchPersona: (userId: string) => Promise<void>
  reload: () => Promise<void>
}

const SessionContext = createContext<SessionContextValue | null>(null)

/** The persona the demo opens on when nothing is stored yet. */
const DEFAULT_PERSONA = 'mgr-001'

export function SessionProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<SessionInfo | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      if (!getPersonaId()) setPersonaId(DEFAULT_PERSONA)
      setSession(await api.session())
      setError(null)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not start a session.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  const switchPersona = useCallback(
    async (userId: string) => {
      setPersonaId(userId)
      await load()
    },
    [load],
  )

  const value = useMemo(
    () => ({ session, loading, error, switchPersona, reload: load }),
    [session, loading, error, switchPersona, load],
  )

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>
}

export function useSession(): SessionContextValue {
  const context = useContext(SessionContext)
  if (!context) throw new Error('useSession must be used inside a SessionProvider')
  return context
}

/** The signed-in user, for pages that only render once a session exists. */
export function useCurrentUser() {
  const { session } = useSession()
  if (!session) throw new Error('No active session')
  return session.user
}
