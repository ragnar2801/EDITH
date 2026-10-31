import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createMemoryRouter, RouterProvider } from 'react-router'

import type { Schemas } from '@/api/client'
import { routes } from '@/app/routes'
import { fakeApi, fundRef, parag, syncRun } from '@/test/fake-api'

function renderApp(path = '/') {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const router = createMemoryRouter(routes, { initialEntries: [path] })
  render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  )
  return router
}

const health = {
  status: 'ok',
  version: '0.1.0',
  database: 'ok',
  server_time: '2026-10-24T04:00:00Z',
}

function navStatus(last: string): Schemas['NavStatusOut'] {
  return {
    last_run: syncRun(),
    funds: [
      {
        fund: fundRef(parag),
        tracked_by_me: false,
        used_by: ['holding'],
        coverage: { first: '2013-05-28', last, count: 3298 },
        last_result: null,
      },
    ],
  }
}

afterEach(() => {
  vi.useRealTimers()
  vi.unstubAllGlobals()
})

test('the top bar has the four jobs, Add and Settings', async () => {
  fakeApi({ 'GET /api/v1/health': () => health })
  renderApp()

  const nav = screen.getByRole('navigation', { name: 'Main' })
  expect(
    within(nav)
      .getAllByRole('link')
      .map((link) => link.textContent),
  ).toEqual(['Portfolio', 'Invest', 'Models', 'Funds'])
  expect(within(nav).getByRole('link', { name: 'Portfolio' })).toHaveClass('font-medium')
  expect(screen.getByRole('button', { name: 'Add' })).toBeInTheDocument()
  expect(screen.getByRole('link', { name: 'Settings' })).toHaveAttribute('href', '/settings')
  expect(screen.getByRole('heading', { name: 'Portfolio' })).toBeInTheDocument()
})

test('the header shows how fresh the NAVs are, and syncs on click', async () => {
  vi.useFakeTimers({ toFake: ['Date'], now: new Date('2026-10-26T06:00:00Z') }) // a Monday
  const calls = fakeApi({
    'GET /api/v1/health': () => health,
    'GET /api/v1/navs/status': () => navStatus('2026-10-23'), // Friday's: up to date
    'POST /api/v1/navs/sync': () => syncRun(),
  })
  renderApp()

  const button = await screen.findByRole('button', { name: /NAVs as of 23 Oct 2026/ })
  expect(button).toHaveTextContent('NAVs 23 Oct')
  expect(button.querySelector('.bg-positive')).not.toBeNull()
  await userEvent.click(button)

  expect(await screen.findByText('26 NAVs added for 2 funds')).toBeInTheDocument()
  expect(calls.some((call) => call.url.endsWith('/navs/sync'))).toBe(true)
})

test('stale NAVs show amber', async () => {
  vi.useFakeTimers({ toFake: ['Date'], now: new Date('2026-10-28T06:00:00Z') }) // Wednesday
  fakeApi({
    'GET /api/v1/health': () => health,
    'GET /api/v1/navs/status': () => navStatus('2026-10-23'),
  })
  renderApp()

  const button = await screen.findByRole('button', { name: /NAVs as of 23 Oct 2026/ })
  expect(button.querySelector('.bg-amber-500')).not.toBeNull()
})

test('says so when the backend is unreachable', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn(async () => {
      throw new TypeError('Failed to fetch')
    }),
  )
  renderApp()

  expect(await screen.findByRole('button', { name: /Backend unreachable/ })).toHaveTextContent(
    'Offline',
  )
})

test('navigates between sections, and the Cash tab belongs to Portfolio', async () => {
  fakeApi({})
  const router = renderApp()

  const nav = screen.getByRole('navigation', { name: 'Main' })
  await userEvent.click(within(nav).getByRole('link', { name: 'Invest' }))
  expect(screen.getByRole('heading', { name: 'Invest' })).toBeInTheDocument()

  await userEvent.click(within(nav).getByRole('link', { name: 'Portfolio' }))
  await userEvent.click(screen.getByRole('tab', { name: 'Cash' }))
  expect(router.state.location.pathname).toBe('/cash')
  expect(within(nav).getByRole('link', { name: 'Portfolio' })).toHaveClass('font-medium')
})

test.each([
  ['/holdings', '/'],
  ['/holdings/7', '/funds/7/transactions'],
  ['/instruments/7', '/funds/7'],
  ['/backtest/1', '/models/1/backtest'],
  ['/status', '/settings/data'],
])('the old address %s redirects to %s', async (from, to) => {
  fakeApi({})
  const router = renderApp(from)

  await vi.waitFor(() => expect(router.state.location.pathname).toBe(to))
})

test('unknown paths show a not-found page', () => {
  fakeApi({})
  renderApp('/nope')

  expect(screen.getByRole('heading', { name: 'Page not found' })).toBeInTheDocument()
})
