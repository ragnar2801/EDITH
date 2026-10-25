import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
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

test('Portfolio shows value, gain and XIRR exactly as the API sends them (D-070)', async () => {
  fakeApi({
    'GET /api/v1/portfolio': () => held,
    'GET /api/v1/holdings': () => [holdingRow],
  })
  renderAt('/')

  await screen.findByText('Value', { selector: 'dt' })
  expect(within(stat('Value')).getByText('₹14,400.00')).toBeInTheDocument()
  expect(within(stat('Value')).getByText(`${nifty.name}: ₹13,500.00`)).toBeInTheDocument()
  expect(within(stat('Invested')).getByText('₹10,000.00')).toBeInTheDocument()
  expect(within(stat('Gain')).getByText('+46.00% · ₹2,500.00 realised')).toBeInTheDocument()
  expect(within(stat('XIRR')).getByText('+23.45%')).toBeInTheDocument()
  expect(within(stat('XIRR')).getByText(`${nifty.name}: +19.87%`)).toBeInTheDocument()

  const row = screen.getByRole('link', { name: parag.name }).closest('tr')!
  expect(within(row).getByText('₹6,900.00')).toBeInTheDocument()
  expect(within(row).getByText('100.00%')).toBeInTheDocument() // weight
  expect(within(row).getByText('60.00%')).toBeInTheDocument() // target
  expect(within(row).getByText(/1 SIP/)).toBeInTheDocument()
  expect(screen.getByRole('region', { name: 'Allocation' })).toHaveTextContent('Equity')
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
