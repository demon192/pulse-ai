/**
 * The API client is the single place that knows how a request is authenticated
 * and how a failure is surfaced, so these tests pin both.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ApiError, api, setPersonaId } from '@/services/api'

function jsonResponse(body: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as Response
}

describe('api client', () => {
  beforeEach(() => {
    window.localStorage.clear()
    vi.stubGlobal('fetch', vi.fn())
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('attaches the development persona header', async () => {
    setPersonaId('mgr-001')
    vi.mocked(fetch).mockResolvedValue(jsonResponse({ status: 'ok' }))

    await api.session()

    const [, init] = vi.mocked(fetch).mock.calls[0]
    expect((init?.headers as Record<string, string>)['X-Dev-User-Id']).toBe('mgr-001')
  })

  it('sends no persona header when none is stored', async () => {
    vi.mocked(fetch).mockResolvedValue(jsonResponse({}))

    await api.session()

    const [, init] = vi.mocked(fetch).mock.calls[0]
    expect((init?.headers as Record<string, string>)['X-Dev-User-Id']).toBeUndefined()
  })

  it('serialises query parameters and omits undefined ones', async () => {
    vi.mocked(fetch).mockResolvedValue(jsonResponse([]))

    await api.requests({ status: 'open', project_id: undefined, include_closed: false })

    const [url] = vi.mocked(fetch).mock.calls[0]
    const parsed = new URL(url as string)
    expect(parsed.pathname).toBe('/api/requests')
    expect(parsed.searchParams.get('status')).toBe('open')
    expect(parsed.searchParams.get('include_closed')).toBe('false')
    expect(parsed.searchParams.has('project_id')).toBe(false)
  })

  it('raises the server detail message on an error response', async () => {
    vi.mocked(fetch).mockResolvedValue(
      jsonResponse({ detail: 'You are not authorized to access this request.' }, 403),
    )

    await expect(api.requestDetail('req-001')).rejects.toMatchObject({
      name: 'ApiError',
      status: 403,
      message: 'You are not authorized to access this request.',
    })
  })

  it('exposes field errors from a validation failure', async () => {
    vi.mocked(fetch).mockResolvedValue(
      jsonResponse(
        {
          detail: 'The request payload failed validation.',
          errors: [{ field: 'title', message: 'String should have at least 3 characters' }],
        },
        422,
      ),
    )

    try {
      await api.createRequest({
        project_id: 'proj-payments',
        category: 'approval',
        title: 'x',
        description: 'y',
        priority: 'medium',
      })
      expect.unreachable('the call should have thrown')
    } catch (error) {
      expect(error).toBeInstanceOf(ApiError)
      expect((error as ApiError).fieldErrors).toEqual([
        { field: 'title', message: 'String should have at least 3 characters' },
      ])
    }
  })

  it('reports an unreachable backend in terms a user can act on', async () => {
    vi.mocked(fetch).mockRejectedValue(new TypeError('Failed to fetch'))

    await expect(api.session()).rejects.toMatchObject({
      status: 0,
      message: 'Could not reach the TeamPulse API. Is the backend running?',
    })
  })

  it('falls back to a status message when the body carries no detail', async () => {
    vi.mocked(fetch).mockResolvedValue(jsonResponse({}, 500))

    await expect(api.session()).rejects.toMatchObject({
      status: 500,
      message: 'Request failed with status 500.',
    })
  })
})
