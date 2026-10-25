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
  renderAt('/settings/data')

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
  renderAt('/settings/data')

  await userEvent.click(await screen.findByRole('button', { name: 'Sync all NAVs' }))
  expect(await screen.findByText(/latest NAV from AMFI/)).toBeInTheDocument()
  await userEvent.click(screen.getByRole('button', { name: `Sync ${parag.name}` }))

  const posts = calls.filter((call) => call.method === 'POST')
  expect(await posts[0].json()).toEqual({})
  expect(await posts[1].json()).toEqual({ instrument_ids: [parag.id] })
})

test('says how to start when nothing is tracked', async () => {
  fakeApi({ 'GET /api/v1/navs/status': () => ({ last_run: null, funds: [] }) })
  renderAt('/settings/data')

  expect(await screen.findByText('No funds tracked')).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Sync all NAVs' })).toBeDisabled()
})

const amfiSource = (lastSuccess: boolean) => ({
  source: 'amfi',
  active_instruments: lastSuccess ? 8821 : 0,
  last_run: null,
  last_success: lastSuccess
    ? {
        status: 'ok',
        finished_at: '2026-10-24T16:00:00Z',
        rows: 14412,
        added: 14412,
        updated: 0,
        deactivated: 0,
        message: null,
      }
    : null,
})

test('the fund lists download from Settings · Data', async () => {
  let downloaded = false
  const calls = fakeApi({
    'GET /api/v1/navs/status': () => ({ last_run: null, funds: [] }),
    'GET /api/v1/instruments/sources': () => [amfiSource(downloaded)],
    'POST /api/v1/instruments/refresh': () => {
      downloaded = true
      return ['nse', 'amfi', 'us'].map((source) => ({
        source,
        status: 'ok',
        rows: 10,
        added: 10,
        updated: 0,
        deactivated: 0,
        reactivated: 0,
        message: null,
        warnings: [],
      }))
    },
  })
  renderAt('/settings/data')

  const lists = await screen.findByRole('region', { name: 'Fund lists' })
  expect(await within(lists).findByText('Not downloaded')).toBeInTheDocument()
  await userEvent.click(within(lists).getByRole('button', { name: 'Download lists' }))

  expect(await screen.findByText('Lists downloaded')).toBeInTheDocument()
  expect(await within(lists).findByText(/8,821 active · 24 Oct 2026, 9:30 pm/)).toBeVisible()
  const post = calls.find((call) => call.url.endsWith('/instruments/refresh'))
  expect(await post?.json()).toEqual({})
})

test('first run: a banner downloads the fund list, and a checklist shows what is left', async () => {
  let downloaded = false
  const calls = fakeApi({
    'GET /api/v1/instruments/sources': () => [amfiSource(downloaded)],
    'POST /api/v1/instruments/refresh': () => {
      downloaded = true
      return [
        {
          source: 'amfi',
          status: 'ok',
          rows: 14412,
          added: 14412,
          updated: 0,
          deactivated: 0,
          reactivated: 0,
          message: null,
          warnings: [],
        },
      ]
    },
    'GET /api/v1/cash': () => ({
      accounts: [],
      deployable: '0.00',
      reserved: '0.00',
      emergency: { goal: '0.00', cash: '0.00', fund: null, total: '0.00', shortfall: '0.00' },
    }),
    'GET /api/v1/holdings': () => [],
    'GET /api/v1/buckets': () => [],
    'GET /api/v1/plan/settings': () => ({
      target_bucket: null,
      emergency_goal: '0.00',
      emergency_fund: null,
      stagger_fund: null,
      stagger_threshold: '500000.00',
      stagger_months: 6,
      min_per_fund: '500.00',
      updated_at: '2026-10-25T05:00:00Z',
    }),
  })
  renderAt('/')

  const steps = await screen.findByRole('region', { name: 'Get set up' })
  expect(
    within(steps)
      .getAllByRole('listitem')
      .map((item) => item.textContent),
  ).toEqual([
    'Add your cashAdd cash',
    'Add your fundsAdd transaction',
    'Choose a target modelNew model',
  ])
  const banner = (await screen.findByText('Fund list not downloaded')).closest('[role=status]')!
  await userEvent.click(within(banner as HTMLElement).getByRole('button', { name: 'Download' }))

  expect(await screen.findByText('14,412 funds downloaded')).toBeInTheDocument()
  await vi.waitFor(() => expect(screen.queryByText('Fund list not downloaded')).toBeNull())
  const post = calls.find((call) => call.url.endsWith('/instruments/refresh'))
  expect(await post?.json()).toEqual({ sources: ['amfi'] })
})
