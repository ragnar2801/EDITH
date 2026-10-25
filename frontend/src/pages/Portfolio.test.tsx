import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createMemoryRouter, RouterProvider } from 'react-router'

import type { Schemas } from '@/api/client'
import { routes } from '@/app/routes'
import {
  bucket,
  detail,
  fakeApi,
  fundRef,
  holding,
  navSummary,
  nifty,
  parag,
  recentNavs,
} from '@/test/fake-api'

function renderAt(path: string) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={createMemoryRouter(routes, { initialEntries: [path] })} />
    </QueryClientProvider>,
  )
}

afterEach(() => {
  vi.unstubAllGlobals()
})

function returns(extra: Partial<Schemas['ReturnsOut']> = {}): Schemas['ReturnsOut'] {
  return {
    invested: '15000.00',
    redeemed: '7500.00',
    value: '14400.00',
    gain: '6900.00',
    return_pct: '46.00',
    xirr_pct: '23.45',
    since: '2024-01-01',
    on: '2026-10-23',
    ...extra,
  }
}

const empty: Schemas['PortfolioOut'] = {
  returns: null,
  cost: '0.00',
  realised: '0.00',
  unrealised: null,
  benchmark_fund: null,
  benchmark: null,
  ahead: null,
  day: null,
  sips: { monthly: '0.00', count: 0, next_date: null, next_fund: null },
  funds: [],
  allocation: [],
  target: null,
  drift: [],
  cash: { deployable: '0.00', emergency: '0.00', reserved: '0.00', total: '0.00' },
  net_worth: '0.00',
  missing_nav: [],
  nav_oldest: null,
  nav_newest: null,
  last_sync: null,
}

const held: Schemas['PortfolioOut'] = {
  ...empty,
  returns: returns(),
  cost: '10000.00',
  realised: '2500.00',
  unrealised: '4400.00',
  benchmark_fund: fundRef(nifty),
  benchmark: returns({ value: '13500.00', gain: '6000.00', xirr_pct: '19.87' }),
  ahead: '900.00',
  day: { start: '2026-10-22', end: '2026-10-23', gain: '-120.50', return_pct: '-0.83' },
  sips: { monthly: '5000.00', count: 1, next_date: '2026-11-05', next_fund: fundRef(parag) },
  funds: [
    {
      fund: fundRef(parag),
      role: 'target',
      units: '90.000',
      cost: '10000.00',
      realised: '2500.00',
      unrealised: '4400.00',
      nav: '160',
      nav_date: '2026-10-23',
      share: '100.00',
      returns: returns(),
      benchmark: returns({ value: '13500.00', gain: '6000.00', xirr_pct: '19.87' }),
      ahead: '900.00',
      day: { start: '2026-10-22', end: '2026-10-23', gain: '-120.50', return_pct: '-0.83' },
    },
  ],
  allocation: [{ asset: 'equity', value: '14400.00', share: '100.00' }],
  target: { id: 1, name: 'Core' },
  drift: [
    { fund: fundRef(parag), weight: '60.00', value: '14400.00', share: '100.00', drift: '40.00' },
    { fund: fundRef(nifty), weight: '40.00', value: '0.00', share: '0.00', drift: '-40.00' },
  ],
  cash: { deployable: '4000.00', emergency: '20000.00', reserved: '0.00', total: '24000.00' },
  net_worth: '38400.00',
  nav_oldest: '2026-10-22',
  nav_newest: '2026-10-23',
  last_sync: '2026-10-23T18:00:00Z',
}

const holdingRow = {
  fund: fundRef(parag),
  units: '90.000',
  cost: '10000.00',
  lots: 2,
  active_sips: 1,
  nav_last: '2026-10-23',
}

function stat(label: string) {
  return screen.getByText(label, { selector: 'dt' }).parentElement!
}

const history: Schemas['HistoryOut'] = {
  benchmark_fund: fundRef(nifty),
  points: [
    { date: '2024-01-01', value: '10000.00', invested: '10000.00', benchmark: '10000.00' },
    { date: '2026-10-23', value: '14400.00', invested: '10000.00', benchmark: '13500.00' },
  ],
  change: { start: '2024-01-01', end: '2026-10-23', gain: '6900.00', return_pct: '60.00' },
  benchmark_change: {
    start: '2024-01-01',
    end: '2026-10-23',
    gain: '6000.00',
    return_pct: '50.00',
  },
}

test('Portfolio shows value, gain, the day and XIRR exactly as the API sends them', async () => {
  fakeApi({
    'GET /api/v1/portfolio': () => held,
    'GET /api/v1/portfolio/history': () => history,
    'GET /api/v1/holdings': () => [holdingRow],
  })
  renderAt('/')

  await screen.findByText('Value', { selector: 'dt' })
  expect(within(stat('Value')).getByText('₹14,400.00')).toBeInTheDocument()
  expect(within(stat('Value')).getByText('₹10,000.00 invested')).toBeInTheDocument()
  expect(within(stat('Gain')).getByText('+46.00% · ₹2,500.00 realised')).toBeInTheDocument()
  expect(within(stat('Day')).getByText('-₹120.50')).toBeInTheDocument()
  expect(within(stat('Day')).getByText('−0.83%')).toBeInTheDocument()
  expect(within(stat('XIRR')).getByText('+23.45%')).toBeInTheDocument()
  expect(within(stat('XIRR')).getByText('Benchmark: +19.87%')).toBeInTheDocument()
  expect(within(stat('vs benchmark')).getByText('₹900.00')).toBeInTheDocument()
  expect(within(stat('vs benchmark')).getByText('Same money: ₹13,500.00')).toBeInTheDocument()
  expect(within(stat('SIPs a month')).getByText('₹5,000.00')).toBeInTheDocument()
  expect(within(stat('SIPs a month')).getByText(`Next 5 Nov · ${parag.name}`)).toBeInTheDocument()

  const table = screen.getByRole('table', { name: 'Holdings' })
  const row = within(table).getByRole('link', { name: parag.name }).closest('tr')!
  expect(within(row).getByText('₹6,900.00')).toBeInTheDocument()
  expect(within(row).getByText('90.000 units')).toBeInTheDocument()
  expect(within(row).getByText('-₹120.50')).toBeInTheDocument() // day
  expect(within(row).getByText('₹900.00')).toBeInTheDocument() // vs benchmark
  expect(within(row).getByText('100.00%')).toBeInTheDocument() // weight
  expect(within(row).getByText('of 60.00%')).toBeInTheDocument() // target
  expect(within(row).getByText(/1 SIP/)).toBeInTheDocument()
  expect(screen.getByRole('region', { name: 'Allocation' })).toHaveTextContent('Equity')
})

test("the value chart shows the range's gain and return from the API (D-072)", async () => {
  const calls = fakeApi({
    'GET /api/v1/portfolio': () => held,
    'GET /api/v1/portfolio/history': () => history,
    'GET /api/v1/holdings': () => [holdingRow],
  })
  renderAt('/')

  const chart = await screen.findByRole('region', { name: 'Value over time' })
  const range = await within(chart).findByLabelText('Over this range')
  await within(range).findByText('₹6,900.00')
  expect(within(range).getByText('+60.00%')).toBeInTheDocument()
  expect(within(range).getByText('+50.00%')).toBeInTheDocument()
  expect(within(chart).getByRole('img', { name: 'Portfolio value over time' })).toBeInTheDocument()

  await userEvent.click(within(chart).getByRole('button', { name: '1Y' }))
  await vi.waitFor(() =>
    expect(calls.some((call) => new URL(call.url).search === '?start=2025-10-23')).toBe(true),
  )
})

test('the target model shows each fund against its weight, with Invest', async () => {
  fakeApi({
    'GET /api/v1/portfolio': () => held,
    'GET /api/v1/portfolio/history': () => history,
    'GET /api/v1/holdings': () => [holdingRow],
  })
  renderAt('/')

  const target = await screen.findByRole('region', { name: 'Target model' })
  expect(within(target).getByText(/of 40\.00% · −40\.00 pts/)).toBeInTheDocument()
  expect(within(target).getByRole('link', { name: 'Invest' })).toHaveAttribute('href', '/invest')
  expect(within(target).getByRole('link', { name: 'Core' })).toHaveAttribute('href', '/models/1')
})

test('with nothing held, Portfolio shows no totals', async () => {
  fakeApi({
    'GET /api/v1/portfolio': () => empty,
    'GET /api/v1/holdings': () => [],
  })
  renderAt('/')

  expect(await screen.findByText('No funds yet')).toBeInTheDocument()
  expect(screen.queryByText('XIRR', { selector: 'dt' })).not.toBeInTheDocument()
})

test('the fund page shows its returns next to the benchmark', async () => {
  fakeApi({
    'GET /api/v1/instruments/7': () => detail(parag),
    'GET /api/v1/holdings/7': () => holding(),
    'GET /api/v1/portfolio': () => held,
    'GET /api/v1/instruments/7/nav-summary': () => navSummary(),
    'GET /api/v1/instruments/7/navs': () => recentNavs,
  })
  renderAt('/funds/7')

  await screen.findByText('Unrealised', { selector: 'dt' })
  expect(within(stat('Value')).getByText('₹14,400.00')).toBeInTheDocument()
  expect(within(stat('Realised')).getByText('₹7,500.00 taken out')).toBeInTheDocument()
  expect(within(stat('XIRR')).getByText('+23.45%')).toBeInTheDocument()
  expect(within(stat('In the benchmark')).getByText('₹13,500.00')).toBeInTheDocument()
})

test('the target model shows how far each fund is from its weight (D-071)', async () => {
  fakeApi({
    'GET /api/v1/buckets': () => [bucket()],
    'GET /api/v1/plan/settings': () => ({
      target_bucket: { id: 1, name: 'Core' },
      emergency_goal: '0.00',
      emergency_fund: null,
      stagger_fund: null,
      stagger_threshold: '500000.00',
      stagger_months: 6,
      min_per_fund: '500.00',
      updated_at: '2026-10-25T05:00:00Z',
    }),
    'GET /api/v1/portfolio': () => held,
  })
  renderAt('/models/1')

  const funds = await screen.findByRole('table', { name: 'Funds' })
  expect(await within(funds).findByText('−40.00 pts')).toBeInTheDocument()
  expect(within(funds).getByText('+40.00 pts')).toBeInTheDocument()
})
