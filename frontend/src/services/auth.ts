/**
 * Firebase sign-in.
 *
 * The instance tells the client how to authenticate (`GET /api/auth-config`)
 * rather than the project being baked in at build time: one container image
 * serves every environment, and a Vite build cannot know which.
 *
 * The Firebase SDK is imported dynamically so that a development instance,
 * which never signs anyone in, does not pay for it on first paint.
 */

import type { Auth, User as FirebaseUser } from 'firebase/auth'

import type { AuthConfig } from '@/types/api'

let config: AuthConfig | null = null
let authPromise: Promise<Auth> | null = null
let currentUser: FirebaseUser | null = null

/** Ask the instance how it expects callers to authenticate. */
export async function fetchAuthConfig(): Promise<AuthConfig> {
  if (config) return config
  const response = await fetch('/api/auth-config')
  if (!response.ok) {
    throw new Error(`Could not read the authentication configuration (${response.status}).`)
  }
  config = (await response.json()) as AuthConfig
  return config
}

/** The config fetched earlier, for synchronous render decisions. */
export function cachedAuthConfig(): AuthConfig | null {
  return config
}

async function getAuth(): Promise<Auth> {
  if (authPromise) return authPromise
  authPromise = (async () => {
    const settings = await fetchAuthConfig()
    if (!settings.firebase_api_key || !settings.firebase_auth_domain) {
      throw new Error('This instance has no Firebase web configuration.')
    }
    const [{ initializeApp, getApps }, firebaseAuth] = await Promise.all([
      import('firebase/app'),
      import('firebase/auth'),
    ])
    const app = getApps()[0] ??
      initializeApp({
        apiKey: settings.firebase_api_key,
        authDomain: settings.firebase_auth_domain,
        projectId: settings.firebase_project_id ?? undefined,
      })
    const auth = firebaseAuth.getAuth(app)
    // Survives a reload so a refresh does not force another sign-in.
    await firebaseAuth.setPersistence(auth, firebaseAuth.browserLocalPersistence)
    return auth
  })()
  return authPromise
}

/**
 * Observe sign-in state. Resolves once Firebase has restored any persisted
 * session, so the app can tell "signed out" from "not yet known".
 */
export async function watchSignIn(
  onChange: (user: FirebaseUser | null) => void,
): Promise<() => void> {
  const auth = await getAuth()
  const { onIdTokenChanged } = await import('firebase/auth')
  // onIdTokenChanged, not onAuthStateChanged: it also fires on token refresh,
  // which keeps `currentUser` from going stale after the hour-long expiry.
  return onIdTokenChanged(auth, (user) => {
    currentUser = user
    onChange(user)
  })
}

export async function signInWithGoogle(): Promise<void> {
  const auth = await getAuth()
  const { GoogleAuthProvider, signInWithPopup } = await import('firebase/auth')
  const provider = new GoogleAuthProvider()
  // Always show the chooser: demo accounts are rarely the browser's default.
  provider.setCustomParameters({ prompt: 'select_account' })
  await signInWithPopup(auth, provider)
}

export async function signInWithEmail(email: string, password: string): Promise<void> {
  const auth = await getAuth()
  const { signInWithEmailAndPassword } = await import('firebase/auth')
  await signInWithEmailAndPassword(auth, email, password)
}

export async function signOut(): Promise<void> {
  const auth = await getAuth()
  const { signOut: firebaseSignOut } = await import('firebase/auth')
  await firebaseSignOut(auth)
}

/**
 * The current ID token, refreshed by the SDK when it is close to expiring.
 * This is what `setBearerTokenProvider` hands to every API request.
 */
export async function currentIdToken(): Promise<string | null> {
  if (!currentUser) return null
  try {
    return await currentUser.getIdToken()
  } catch {
    // An unreachable token endpoint must not take the whole app down; the
    // request then goes out unauthenticated and the API answers 401.
    return null
  }
}

/** Turn a Firebase error code into something a person can act on. */
export function describeSignInError(error: unknown): string {
  const code = (error as { code?: string } | null)?.code ?? ''
  switch (code) {
    case 'auth/popup-blocked':
      return 'The browser blocked the sign-in window. Allow pop-ups for this site and try again.'
    case 'auth/popup-closed-by-user':
    case 'auth/cancelled-popup-request':
      return 'Sign-in was cancelled.'
    case 'auth/unauthorized-domain':
      return (
        'This domain is not in the Firebase project’s authorised list. ' +
        'Add it under Authentication → Settings → Authorized domains.'
      )
    case 'auth/operation-not-allowed':
      return 'That sign-in method is not enabled on the Firebase project.'
    case 'auth/invalid-credential':
    case 'auth/wrong-password':
    case 'auth/user-not-found':
      return 'That email and password combination was not recognised.'
    case 'auth/invalid-email':
      return 'That is not a valid email address.'
    case 'auth/too-many-requests':
      return 'Too many attempts. Wait a moment and try again.'
    case 'auth/network-request-failed':
      return 'Could not reach Firebase. Check the network connection.'
    default:
      return error instanceof Error ? error.message : 'Sign-in failed.'
  }
}
