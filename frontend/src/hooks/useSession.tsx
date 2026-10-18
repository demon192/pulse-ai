import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react'

import { api, getPersonaId, setBearerTokenProvider, setPersonaId } from '@/services/api'
import { currentIdToken, fetchAuthConfig, signOut, watchSignIn } from '@/services/auth'
import type { AuthConfig, SessionInfo } from '@/types/api'

interface SessionContextValue {
  session: SessionInfo | null
  authConfig: AuthConfig | null
  loading: boolean
  error: string | null
  /** True in Firebase mode when nobody is signed in yet. */
  needsSignIn: boolean
  switchPersona: (userId: string) => Promise<void>
  signOut: () => Promise<void>
  reload: () => Promise<void>
}

const SessionContext = createContext<SessionContextValue | null>(null)

/** The persona the demo opens on when nothing is stored yet. */
const DEFAULT_PERSONA = 'mgr-001'

export function SessionProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<SessionInfo | null>(null)
  const [authConfig, setAuthConfig] = useState<AuthConfig | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [signedIn, setSignedIn] = useState<boolean | null>(null)
  // Avoids a redundant /api/session on the token-refresh events that
  // onIdTokenChanged also delivers.
  const lastSignedIn = useRef<boolean | null>(null)

  const loadSession = useCallback(async () => {
    setLoading(true)
    try {
      setSession(await api.session())
      setError(null)
    } catch (caught) {
      setSession(null)
      setError(caught instanceof Error ? caught.message : 'Could not start a session.')
    } finally {
      setLoading(false)
    }
  }, [])

  // Step 1: ask the instance how to authenticate, before anything else.
  useEffect(() => {
    let cancelled = false
    let unsubscribe: (() => void) | undefined

    void (async () => {
      let config: AuthConfig
      try {
        config = await fetchAuthConfig()
      } catch (caught) {
        if (cancelled) return
        setError(caught instanceof Error ? caught.message : 'Could not reach TeamPulse.')
        setLoading(false)
        return
      }
      if (cancelled) return
      setAuthConfig(config)

      if (config.auth_mode !== 'firebase') {
        // Development: the persona header identifies the caller.
        if (!getPersonaId()) setPersonaId(DEFAULT_PERSONA)
        await loadSession()
        return
      }

      // Firebase: every request carries the current ID token.
      setBearerTokenProvider(currentIdToken)
      try {
        unsubscribe = await watchSignIn((user) => {
          if (cancelled) return
          setSignedIn(user !== null)
          if (user === null) {
            // Cleared here, in the event that caused it, rather than in an
            // effect reacting to it. Resetting the guard lets a later sign-in
            // load a session again.
            lastSignedIn.current = null
            setSession(null)
            setError(null)
            setLoading(false)
          }
        })
      } catch (caught) {
        if (cancelled) return
        setError(caught instanceof Error ? caught.message : 'Sign-in is unavailable.')
        setLoading(false)
      }
    })()

    return () => {
      cancelled = true
      unsubscribe?.()
    }
  }, [loadSession])

  // Step 2 (Firebase only): load the session once somebody is signed in.
  // Signing out is handled by the listener itself, so there is nothing to do
  // here for the false case.
  useEffect(() => {
    if (authConfig?.auth_mode !== 'firebase' || signedIn !== true) return
    if (lastSignedIn.current === true) return
    lastSignedIn.current = true
    void loadSession()
  }, [authConfig, signedIn, loadSession])

  const switchPersona = useCallback(
    async (userId: string) => {
      setPersonaId(userId)
      await loadSession()
    },
    [loadSession],
  )

  const handleSignOut = useCallback(async () => {
    await signOut()
    setSession(null)
  }, [])

  const value = useMemo(
    () => ({
      session,
      authConfig,
      loading,
      error,
      needsSignIn: authConfig?.auth_mode === 'firebase' && signedIn === false,
      switchPersona,
      signOut: handleSignOut,
      reload: loadSession,
    }),
    [session, authConfig, loading, error, signedIn, switchPersona, handleSignOut, loadSession],
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
