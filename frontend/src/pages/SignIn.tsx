/**
 * Sign-in, shown only when the instance runs in Firebase auth mode.
 *
 * Production force-disables the development persona switcher, so this is the
 * only way into a deployed instance.
 */

import { useState, type FormEvent } from 'react'

import { Button, Card, CardBody, Field, InlineError, inputClasses } from '@/components/ui/primitives'
import {
  describeSignInError,
  signInWithEmail,
  signInWithGoogle,
} from '@/services/auth'
import type { AuthConfig } from '@/types/api'

export function SignIn({ config }: { config: AuthConfig }) {
  const [busy, setBusy] = useState<'google' | 'email' | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')

  async function run(kind: 'google' | 'email', action: () => Promise<void>) {
    setBusy(kind)
    setError(null)
    try {
      await action()
      // No navigation here: the session provider is watching sign-in state and
      // re-renders the app once a token exists.
    } catch (caught) {
      setError(describeSignInError(caught))
    } finally {
      setBusy(null)
    }
  }

  if (!config.sign_in_configured) {
    return (
      <Shell>
        <h1 className="text-lg font-semibold text-navy-900">Sign-in is not configured</h1>
        <p className="mt-2 text-sm text-slate-600">
          This instance requires Firebase authentication, but it was deployed without the
          Firebase web configuration, so no one can sign in.
        </p>
        <p className="mt-3 text-sm text-slate-500">
          Set <code className="rounded bg-slate-100 px-1">FIREBASE_WEB_API_KEY</code> and{' '}
          <code className="rounded bg-slate-100 px-1">FIREBASE_PROJECT_ID</code> on the service
          and redeploy.
        </p>
      </Shell>
    )
  }

  return (
    <Shell>
      <h1 className="text-lg font-semibold text-navy-900">Sign in to TeamPulse AI</h1>
      <p className="mt-1 text-sm text-slate-600">
        Use an account whose email matches a TeamPulse user.
      </p>

      <Button
        variant="primary"
        className="mt-5 w-full justify-center"
        disabled={busy !== null}
        onClick={() => void run('google', signInWithGoogle)}
      >
        {busy === 'google' ? 'Opening Google…' : 'Continue with Google'}
      </Button>

      <div className="my-5 flex items-center gap-3">
        <span className="h-px flex-1 bg-slate-200" />
        <span className="text-xs uppercase tracking-wide text-slate-400">or</span>
        <span className="h-px flex-1 bg-slate-200" />
      </div>

      <form
        onSubmit={(event: FormEvent) => {
          event.preventDefault()
          void run('email', () => signInWithEmail(email, password))
        }}
      >
        <Field label="Email">
          <input
            type="email"
            autoComplete="username"
            className={inputClasses}
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
          />
        </Field>
        <div className="mt-3">
          <Field label="Password">
            <input
              type="password"
              autoComplete="current-password"
              className={inputClasses}
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
            />
          </Field>
        </div>
        <Button
          type="submit"
          variant="secondary"
          className="mt-4 w-full justify-center"
          disabled={busy !== null}
        >
          {busy === 'email' ? 'Signing in…' : 'Sign in with email'}
        </Button>
      </form>

      {error ? (
        <div className="mt-4">
          <InlineError message={error} />
        </div>
      ) : null}

      <p className="mt-5 text-xs text-slate-500">
        Signing in only establishes who you are. What you can see is decided separately, on the
        server, for every request.
      </p>
    </Shell>
  )
}

function Shell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-100 p-6">
      <Card className="w-full max-w-sm">
        <CardBody>{children}</CardBody>
      </Card>
    </div>
  )
}
