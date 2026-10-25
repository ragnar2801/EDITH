import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createMemoryRouter, RouterProvider } from 'react-router'

import { routes } from '@/app/routes'
import {
  detail,
  fakeApi,
  holding,
  infosys,
  navSummary,
  parag,
  problem,
  recentNavs,
  syncRun,
} from '@/test/fake-api'

function renderAt(path: string) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const router = createMemoryRouter(routes, { initialEntries: [path] })
  render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  )
  return router
}

afterEach(() => {
  vi.unstubAllGlobals()
})

const notHeld = holding({ lots: [], sips: [], units: '0', cost: '0.00' })

test('Funds searches mutual funds only and opens the fund page', async () => {
  const calls = fakeApi({
    'GET /api/v1/navs/status': () => ({ last_run: null, funds: [] }),
    'GET /api/v1/instruments/search': () => [parag],
    'GET /api/v1/instruments/7': () => detail(parag),
    'GET /api/v1/holdings/7': () => notHeld,
  })
  const router = renderAt('/funds')

  await userEvent.type(screen.getByRole('combobox'), 'parag')
  await userEvent.click(await screen.findByRole('option', { name: /Parag/ }))

  expect(router.state.location.pathname).toBe('/funds/7')
  expect(await screen.findByRole('heading', { name: 'Parag Parikh Flexi Cap Fund' })).toBeVisible()
  const search = calls.find((call) => call.url.includes('/instruments/search'))!
  expect(new URL(search.url).searchParams.get('kind')).toBe('mutual_fund')
  await userEvent.click(screen.getByRole('tab', { name: 'Details' }))
  expect(router.state.location.pathname).toBe('/funds/7/details')
  expect(screen.getByText('INF879O01027')).toBeInTheDocument()
})

test('a fund I hold shows my position on its overview', async () => {
  fakeApi({
    'GET /api/v1/instruments/7': () => detail(parag),
    'GET /api/v1/holdings/7': () => holding(),
  })
  renderAt('/funds/7')

  const position = await screen.findByRole('region', { name: 'My position' })
  expect(within(position).getByText('62.500')).toBeInTheDocument()
  expect(within(position).getByText('₹5,000.00')).toBeInTheDocument()
  expect(screen.getByRole('button', { name: /Sell/ })).toBeInTheDocument()
})

test('a fund page lists its other plans', async () => {
  fakeApi({ 'GET /api/v1/instruments/7': () => detail(parag) })
  renderAt('/funds/7/details')

  const plans = await screen.findByRole('region', { name: 'Other plans' })
  expect(
    within(plans as HTMLElement).getByRole('link', { name: 'Regular · Growth' }),
  ).toHaveAttribute('href', '/funds/8')
})

test('setting my own classification sends exact strings and shows the result', async () => {
  const saved = detail(parag, {
    asset_class: 'hybrid',
    override: {
      asset_class: 'hybrid',
      allocation: [
        { bucket: 'equity', percent: '65' },
        { bucket: 'debt', percent: '35' },
      ],
      exposure: 'GLOBAL',
      note: 'holds US stocks',
      updated_at: '2026-10-24T16:00:00Z',
    },
  })
  const calls = fakeApi({
    'GET /api/v1/instruments/7': () => detail(parag),
    'PUT /api/v1/instruments/7/classification': () => saved,
  })
  renderAt('/funds/7/details')

  await userEvent.click(await screen.findByRole('button', { name: 'Set my own' }))
  const form = screen.getByRole('form', { name: 'My classification' })
  await userEvent.clear(within(form).getByLabelText('Equity'))
  await userEvent.type(within(form).getByLabelText('Equity'), '65')
  await userEvent.type(within(form).getByLabelText('Debt'), '35')
  await userEvent.selectOptions(within(form).getByLabelText('Exposure'), 'GLOBAL')
  await userEvent.type(within(form).getByLabelText('Note'), 'holds US stocks')
  await userEvent.click(within(form).getByRole('button', { name: 'Save' }))

  expect(await screen.findByText('Note: holds US stocks')).toBeInTheDocument()
  expect(screen.getByText('Equity 65%')).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Use the rules' })).toBeInTheDocument()
  const put = calls.find((call) => call.method === 'PUT')
  expect(await put?.json()).toEqual({
    allocation: [
      { bucket: 'equity', percent: '65' },
      { bucket: 'debt', percent: '35' },
    ],
    exposure: 'GLOBAL',
    note: 'holds US stocks',
  })
})

test('a rejected classification shows the reason', async () => {
  fakeApi({
    'GET /api/v1/instruments/7': () => detail(parag),
    'PUT /api/v1/instruments/7/classification': () =>
      problem(422, 'shares must add up to 100, not 90'),
  })
  renderAt('/funds/7/details')

  await userEvent.click(await screen.findByRole('button', { name: 'Set my own' }))
  const equity = screen.getByLabelText('Equity')
  await userEvent.clear(equity)
  await userEvent.type(equity, '90')
  await userEvent.click(screen.getByRole('button', { name: 'Save' }))

  expect(await screen.findByRole('alert')).toHaveTextContent('shares must add up to 100, not 90')
})

test('an unknown instrument says so', async () => {
  fakeApi({ 'GET /api/v1/instruments/999': () => problem(404, 'No instrument with id 999.') })
  renderAt('/funds/999')

  expect(await screen.findByRole('heading', { name: 'Fund not found' })).toBeInTheDocument()
  expect(screen.getByText('No instrument with id 999.')).toBeInTheDocument()
})

test('a tracked fund shows its NAV figures and chart', async () => {
  fakeApi({
    'GET /api/v1/instruments/7': () => detail(parag),
    'GET /api/v1/holdings/7': () => notHeld,
    'GET /api/v1/instruments/7/nav-summary': () => navSummary(),
    'GET /api/v1/instruments/7/navs': () => recentNavs,
  })
  renderAt('/funds/7')

  const card = await screen.findByRole('region', { name: 'NAV history' })
  expect(screen.queryByRole('region', { name: 'My position' })).not.toBeInTheDocument()
  expect(await within(card).findByText('Latest NAV')).toBeInTheDocument()
  expect(within(card).getAllByText('₹88.9695')[0]).toBeInTheDocument()
  expect(within(card).getByText('−0.49%')).toHaveClass('text-destructive')
  expect(within(card).getByText('+11.21%')).toHaveClass('text-positive')
  expect(within(card).getByText('₹72.50')).toBeInTheDocument() // 52-week low
  expect(await within(card).findByRole('img', { name: 'NAV over time' })).toBeInTheDocument()
  expect(within(card).getByRole('button', { name: '1Y' })).toHaveAttribute('aria-pressed', 'true')
})

test('tracking a fund downloads its history', async () => {
  let tracked = false
  const calls = fakeApi({
    'GET /api/v1/instruments/7': () => detail(parag),
    'GET /api/v1/holdings/7': () => notHeld,
    'GET /api/v1/instruments/7/nav-summary': () =>
      tracked
        ? navSummary()
        : navSummary({
            tracked: false,
            tracked_by_me: false,
            coverage: { first: null, last: null, count: 0 },
            stats: null,
          }),
    'PUT /api/v1/instruments/7/tracking': () => {
      tracked = true
      return navSummary({ coverage: { first: null, last: null, count: 0 }, stats: null })
    },
    'POST /api/v1/navs/sync': () => syncRun(),
    'GET /api/v1/instruments/7/navs': () => recentNavs,
  })
  renderAt('/funds/7')

  await userEvent.click(await screen.findByRole('button', { name: 'Track NAVs' }))

  expect(await screen.findByText('Latest NAV')).toBeInTheDocument()
  const sync = calls.find((call) => call.method === 'POST')
  expect(await sync?.json()).toEqual({ instrument_ids: [7] })
})

test('a stock (from an old link) has details but no NAV card', async () => {
  fakeApi({
    'GET /api/v1/instruments/3': () =>
      detail(infosys, {
        source: 'nse',
        series: 'EQ',
        listed_on: '1995-02-08',
        aliases: [
          { kind: 'name', value: 'Infosys Technologies Limited', changed_on: '2011-06-16' },
        ],
      }),
  })
  renderAt('/funds/3')

  expect(await screen.findByRole('heading', { name: 'Infosys Limited' })).toBeInTheDocument()
  expect(screen.queryByText('NAV history')).not.toBeInTheDocument()
  expect(screen.getByText('INE009A01021')).toBeInTheDocument()
  expect(screen.getByText('8 Feb 1995')).toBeInTheDocument() // a market date, no time-zone shift
  expect(screen.getByText(/Infosys Technologies Limited/)).toBeInTheDocument()
})
