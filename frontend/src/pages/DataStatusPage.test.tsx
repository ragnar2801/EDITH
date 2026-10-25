import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createMemoryRouter, RouterProvider } from 'react-router'

import { routes } from '@/app/routes'
import { fakeApi, parag, syncRun } from '@/test/fake-api'

function renderAt(path: string) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={createMemoryRouter(routes, { initialEntries: [path] })} />
    </QueryClientProvider>,
  )
}

const status = {
  last_run: syncRun(),
  funds: [
    {
      fund: {
        id: parag.id,
        name: parag.name,
        amfi_code: '122639',
        fund_house: 'PPFAS Mutual Fund',
        fund_category: 'Equity Scheme - Flexi Cap Fund',
        plan: 'direct',
        option: 'Growth',
        is_active: true,
      },
      tracked_by_me: true,
      used_by: ['bucket Core'],
      coverage: { first: '2013-05-28', last: '2026-10-23', count: 3298 },
      last_result: syncRun().results[0],
    },
  ],
}

afterEach(() => {
  vi.unstubAllGlobals()
})

test('lists tracked funds with their NAV dates and the last sync', async () => {
  fakeApi({ 'GET /api/v1/navs/status': () => status })
  renderAt('/status')

  const row = (await screen.findByRole('link', { name: parag.name })).closest('tr')!
  expect(within(row).getByText('3,298')).toBeInTheDocument()
  expect(within(row).getByText('28 May 2013')).toBeInTheDocument()
  expect(within(row).getByText('23 Oct 2026')).toBeInTheDocument()
  expect(within(row).getByText('You, Model Core')).toBeInTheDocument()
  expect(
    screen.getByText(/Last sync 25 Oct 2026, 9:30 am · 26 NAVs added for 2 funds/),
  ).toBeVisible()
})

test('sync all and sync one fund', async () => {
  const calls = fakeApi({
    'GET /api/v1/navs/status': () => status,
    'POST /api/v1/navs/sync': () =>
      syncRun({
        status: 'partial',
        results: [
          {
            ...syncRun().results[0],
            status: 'fallback',
            added: 1,
            message: 'history unavailable (HTTP 502); latest NAV from AMFI',
          },
        ],
      }),
  })
  renderAt('/status')

  await userEvent.click(await screen.findByRole('button', { name: 'Sync all NAVs' }))
  expect(await screen.findByText(/latest NAV from AMFI/)).toBeInTheDocument()
  await userEvent.click(screen.getByRole('button', { name: `Sync ${parag.name}` }))

  const posts = calls.filter((call) => call.method === 'POST')
  expect(await posts[0].json()).toEqual({})
  expect(await posts[1].json()).toEqual({ instrument_ids: [parag.id] })
})

test('says how to start when nothing is tracked', async () => {
  fakeApi({ 'GET /api/v1/navs/status': () => ({ last_run: null, funds: [] }) })
  renderAt('/status')

  expect(await screen.findByText('No funds tracked')).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Sync all NAVs' })).toBeDisabled()
})
