import { Navigate, Route, Routes } from 'react-router-dom'

import { AppShell } from '@/layouts/AppShell'
import { ActionInbox } from '@/pages/ActionInbox'
import { EngineerOverview } from '@/pages/EngineerOverview'
import { Handovers } from '@/pages/Handovers'
import { ManagerOverview } from '@/pages/ManagerOverview'
import { MyWork } from '@/pages/MyWork'
import { Notifications } from '@/pages/Notifications'
import { ProjectDetail } from '@/pages/ProjectDetail'
import { Projects } from '@/pages/Projects'
import { Requests } from '@/pages/Requests'
import { SignIn } from '@/pages/SignIn'
import { Button, Card, CardBody, LoadingBlock } from '@/components/ui/primitives'
import { useSession } from '@/hooks/useSession'

export default function App() {
  const { session, authConfig, loading, error, needsSignIn, reload } = useSession()

  // Nobody is signed in and this instance has no other way in.
  if (needsSignIn && authConfig) {
    return <SignIn config={authConfig} />
  }

  if (loading && !session) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-100 p-6">
        <Card className="w-full max-w-sm">
          <LoadingBlock label="Starting TeamPulse" rows={3} />
        </Card>
      </div>
    )
  }

  if (error || !session) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-100 p-6">
        <Card className="w-full max-w-md">
          <CardBody>
            <h1 className="text-lg font-semibold text-navy-900">TeamPulse AI could not start</h1>
            <p className="mt-2 text-sm text-slate-600">
              {error ?? 'No session could be established.'}
            </p>
            <p className="mt-2 text-sm text-slate-500">
              {authConfig?.auth_mode === 'firebase'
                ? 'You are signed in, but no TeamPulse user has that email address. Ask an administrator to add it, or seed the demo organisation with --manager-email.'
                : 'Check that the backend is running on port 8000 and that the development persona header is permitted by the current configuration.'}
            </p>
            <Button variant="primary" className="mt-4" onClick={() => void reload()}>
              Try again
            </Button>
          </CardBody>
        </Card>
      </div>
    )
  }

  const isManager = session.user.role === 'manager'

  return (
    <AppShell>
      <Routes>
        <Route path="/" element={isManager ? <ManagerOverview /> : <EngineerOverview />} />
        <Route path="/projects" element={<Projects />} />
        <Route path="/projects/:projectId" element={<ProjectDetail />} />
        <Route
          path="/my-work"
          element={isManager ? <Navigate to="/projects" replace /> : <MyWork />}
        />
        <Route path="/requests" element={<Requests />} />
        <Route
          path="/inbox"
          element={isManager ? <ActionInbox /> : <Navigate to="/requests" replace />}
        />
        <Route path="/handovers" element={<Handovers />} />
        <Route path="/notifications" element={<Notifications />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AppShell>
  )
}
