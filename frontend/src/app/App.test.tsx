import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createMemoryRouter, RouterProvider } from 'react-router'

import { routes } from '@/app/routes'

function renderApp(path = '/') {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const router = createMemoryRouter(routes, { initialEntries: [path] })
  render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  )
}

/** Answer the health check with `response`; every other endpoint is offline. */
function stubHealth(response: () => Promise<Response>) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (request: Request) =>
      new URL(request.url).pathname === '/api/v1/health'
        ? response()
        : new Response('offline', { status: 503 }),
    ),
  )
}

afterEach(() => {
  vi.unstubAllGlobals()
})

test('shows the app shell and a healthy backend', async () => {
  stubHealth(async () =>
    Response.json({
      status: 'ok',
      version: '0.1.0',
      database: 'ok',
      server_time: '2026-10-24T04:00:00Z',
    }),
  )

  renderApp()

  expect(await screen.findByText('backend: ok')).toBeInTheDocument()
  expect(screen.getByRole('heading', { name: 'Dashboard' })).toBeInTheDocument()
  for (const label of ['Buckets', 'Backtest', 'Holdings', 'Cash', 'Data status']) {
    expect(screen.getByRole('link', { name: label })).toBeInTheDocument()
  }
})

test('says so when the backend is unreachable', async () => {
  stubHealth(() => Promise.reject(new TypeError('Failed to fetch')))

  renderApp()

  expect(await screen.findByText('backend: unreachable')).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Check again' })).toBeInTheDocument()
})

test('navigates between sections', async () => {
  stubHealth(() => Promise.reject(new TypeError('offline')))
  renderApp()

  await userEvent.click(screen.getByRole('link', { name: 'Cash' }))

  expect(screen.getByRole('heading', { name: 'Cash' })).toBeInTheDocument()
  expect(screen.getByText(/where new cash should go/)).toBeInTheDocument()
})

test('unknown paths show a not-found page', () => {
  stubHealth(() => Promise.reject(new TypeError('offline')))

  renderApp('/nope')

  expect(screen.getByRole('heading', { name: 'Page not found' })).toBeInTheDocument()
})
