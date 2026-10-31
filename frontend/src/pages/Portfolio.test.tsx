import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createMemoryRouter, RouterProvider } from 'react-router'

import type { Schemas } from '@/api/client'
import { routes } from '@/app/routes'
import {
  bucket,
  model,
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
  bucket: null,
  model: null,
  model_returns: null,
  ahead_of_model: null,
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
      role: 'outside',
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
  cash: { deployable: '4000.00', emergency: '20000.00', reserved: '0.00', total: '24000.00' },
  net_worth: '38400.00',
  nav_oldest: '2026-10-22',
  nav_newest: '2026-10-23',
  last_sync: '2026-10-23T18:00:00Z',
}

// The same money as one bucket following a 60 / 40 model.
const inBucket: Schemas['PortfolioOut'] = {
  ...held,
  funds: held.funds.map((fund) => ({ ...fund, role: 'target' })),
  bucket: { id: 4, name: 'Retirement', paper: false },
  model: { id: 1, name: 'Core' },
  model_returns: returns({ value: '14040.00', gain: '6540.00' }),
  ahead_of_model: '360.00',
  sips: { monthly: '0.00', count: 0, next_date: null, next_fund: null },
  drift: [
    { fund: fundRef(parag), weight: '60.00', value: '14400.00', share: '100.00', drift: '40.00' },
    { fund: fundRef(nifty), weight: '40.00', value: '0.00', share: '0.00', drift: '-40.00' },
  ],
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
  expect(within(row).getByText(/1 SIP/)).toBeInTheDocument()
  expect(screen.getByRole('region', { name: 'Allocation' })).toHaveTextContent('Equity')
})

test("the value chart shows the range's gain and return from the API", async () => {
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

test('one bucket shows against its model, each fund against its weight, with Invest', async () => {
  const calls = fakeApi({
    'GET /api/v1/buckets': () => [bucket(), bucket({ id: 6, name: 'Try', paper: true })],
    'GET /api/v1/portfolio': (request) =>
      new URL(request.url).searchParams.get('bucket_id') === '4' ? inBucket : held,
    'GET /api/v1/portfolio/history': () => history,
    'GET /api/v1/holdings': () => [holdingRow],
  })
  renderAt('/')

  await screen.findByText('Value', { selector: 'dt' })
  expect(screen.queryByText('vs model', { selector: 'dt' })).not.toBeInTheDocument()
  expect(screen.queryByRole('region', { name: 'Model' })).not.toBeInTheDocument()
  await userEvent.selectOptions(await screen.findByLabelText('Bucket'), 'Retirement')

  expect(await screen.findByText('vs model', { selector: 'dt' })).toBeInTheDocument()
  expect(within(stat('vs model')).getByText('₹360.00')).toBeInTheDocument()
  expect(within(stat('vs model')).getByText('Same money: ₹14,040.00')).toBeInTheDocument()
  expect(screen.queryByText('SIPs a month', { selector: 'dt' })).not.toBeInTheDocument()
  const model = screen.getByRole('region', { name: 'Model' })
  expect(within(model).getByText(/of 40\.00% · −40\.00 pts/)).toBeInTheDocument()
  expect(within(model).getByRole('link', { name: 'Invest' })).toHaveAttribute(
    'href',
    '/invest?bucket=4',
  )
  expect(within(model).getByRole('link', { name: 'Core' })).toHaveAttribute('href', '/models/1')
  const table = screen.getByRole('table', { name: 'Holdings' })
  expect(within(table).getByText('of 60.00%')).toBeInTheDocument()
  for (const path of ['/api/v1/portfolio?', '/api/v1/holdings?', '/api/v1/portfolio/history?']) {
    const asked = calls.some((call) => call.url.includes(path) && call.url.includes('bucket_id=4'))
    expect(asked).toBe(true)
  }
})

test('the Buckets tab lists every bucket and opens one', async () => {
  fakeApi({
    'GET /api/v1/buckets': () => [
      bucket(),
      bucket({ id: 6, name: 'Try', paper: true, model: null }),
    ],
    'GET /api/v1/portfolio': () => inBucket,
    'GET /api/v1/portfolio/history': () => history,
    'GET /api/v1/holdings': () => [holdingRow],
  })
  renderAt('/buckets')

  const table = await screen.findByRole('table', { name: 'Buckets' })
  const row = within(table).getByText('Retirement').closest('tr')!
  expect(within(row).getByText('Core')).toBeInTheDocument()
  expect(within(row).getByText('₹360.00')).toBeInTheDocument()
  expect(within(table).getByText('Paper')).toBeInTheDocument()
  await userEvent.click(within(row).getByText('₹20,400.00'))

  expect(await screen.findByLabelText('Bucket')).toHaveValue('4')
})

test('making a bucket sends its name, model and paper', async () => {
  const calls = fakeApi({
    'GET /api/v1/buckets': () => [bucket()],
    'GET /api/v1/models': () => [model()],
    'POST /api/v1/buckets': () =>
      Response.json(bucket({ id: 7, name: 'Try', paper: true }), { status: 201 }),
  })
  renderAt('/buckets')

  await userEvent.click(await screen.findByRole('button', { name: 'New bucket' }))
  const form = screen.getByRole('form', { name: 'New bucket' })
  await userEvent.type(within(form).getByLabelText('Name'), 'Try')
  await userEvent.selectOptions(within(form).getByLabelText('Model'), 'Core')
  await userEvent.click(within(form).getByRole('radio', { name: 'Paper' }))
  await userEvent.click(within(form).getByRole('button', { name: 'Make bucket' }))

  expect(await screen.findByText('Try made')).toBeInTheDocument()
  const request = calls.find((call) => call.method === 'POST')!
  expect(await request.json()).toEqual({ name: 'Try', model_id: 1, paper: true })
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

test('a model lists the buckets following it, each against the model', async () => {
  fakeApi({
    'GET /api/v1/models': () => [model()],
    'GET /api/v1/buckets': () => [bucket(), bucket({ id: 6, name: 'House', model: null })],
  })
  renderAt('/models/1')

  const buckets = await screen.findByRole('table', { name: 'Buckets' })
  const row = within(buckets).getByText('Retirement').closest('tr')!
  expect(within(row).getByText('₹360.00')).toBeInTheDocument()
  expect(within(buckets).queryByText('House')).not.toBeInTheDocument()
})
