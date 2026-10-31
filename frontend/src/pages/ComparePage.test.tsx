import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createMemoryRouter, RouterProvider } from 'react-router'

import type { Schemas } from '@/api/client'
import { routes } from '@/app/routes'
import { fakeApi, fundRef, nifty, parag } from '@/test/fake-api'

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

type Fund = Schemas['ComparedFundOut']

function window(extra: Partial<Schemas['WindowFiguresOut']> = {}): Schemas['WindowFiguresOut'] {
  return {
    cagr_pct: '15.20',
    return_pct: '400.10',
    volatility_pct: '14.00',
    max_drawdown_pct: '30.50',
    recovery_days: 210,
    recovered: true,
    calmar: '0.50',
    upside_capture_pct: '95.00',
    downside_capture_pct: '70.00',
    rolling: {
      years: 3,
      periods: 2000,
      median_pct: '16.00',
      worst_pct: '-2.00',
      best_pct: '30.00',
      beat_benchmark_pct: '85.00',
      curve: [{ date: '2016-05-30', value: '16.00' }],
    },
    sip: { invested: '1600000.00', value: '4500000.00', xirr_pct: '17.10' },
    growth: [
      { date: '2013-05-28', value: '10000.00' },
      { date: '2026-10-23', value: '50010.00' },
    ],
    drawdown: [
      { date: '2013-05-28', value: '0.00' },
      { date: '2026-10-23', value: '-1.00' },
    ],
    ...extra,
  }
}

function fund(summary: typeof parag, extra: Partial<Fund> = {}): Fund {
  return {
    instrument_id: summary.id,
    fund: fundRef(summary),
    first_nav: '2013-05-28',
    last_nav: '2026-10-23',
    trailing: { y1: '12.00', y3: '18.00', y5: '20.00', y10: null },
    calendar: [
      { year: 2025, return_pct: '10.00' },
      { year: 2026, return_pct: '-3.00' },
    ],
    window: window(),
    ...extra,
  }
}

const other = { ...parag, id: 9, name: 'HDFC Flexi Cap Fund' }

function comparison(): Schemas['FundComparisonOut'] {
  return {
    window: {
      start: '2013-05-28',
      end: '2026-10-23',
      years: '13.41',
      limited_by: parag.id,
      earliest_start: '2013-01-02',
    },
    as_of: '2026-10-23',
    rolling_years: 3,
    funds: [
      fund(parag),
      fund(other, {
        trailing: { y1: '9.00', y3: '14.00', y5: '15.00', y10: null },
        window: window({ max_drawdown_pct: '25.00', cagr_pct: '12.00' }),
      }),
    ],
    benchmark: fund(nifty, { window: window({ cagr_pct: '11.00' }) }),
    calendar_years: [2025, 2026],
    correlation: [
      { a: parag.id, b: other.id, value: '0.93' },
      { a: parag.id, b: nifty.id, value: '0.88' },
      { a: other.id, b: nifty.id, value: '0.95' },
    ],
    warnings: [],
  }
}

test('funds side by side, the best in each column in bold', async () => {
  const calls = fakeApi({ 'GET /api/v1/compare/funds': () => comparison() })
  renderAt('/compare?ids=7,9')

  const returns = await screen.findByRole('table', { name: 'Returns' })
  const rows = within(returns).getAllByRole('row')
  expect(rows).toHaveLength(4) // header, two funds, the benchmark
  expect(within(rows[1]).getByText('+18.00%')).toHaveClass('font-semibold', 'text-positive')
  expect(within(rows[2]).getByText('+14.00%')).not.toHaveClass('font-semibold')
  const risk = screen.getByRole('table', { name: 'Risk' })
  expect(within(risk).getAllByRole('row')[2]).toHaveTextContent('25.00%')
  expect(within(within(risk).getAllByRole('row')[2]).getByText('25.00%')).toHaveClass(
    'font-semibold',
  ) // the smaller drop
  expect(screen.getByText('2026 YTD')).toBeInTheDocument()
  expect(screen.getByRole('img', { name: 'Growth of the funds compared' })).toBeInTheDocument()
  expect(screen.getByText(/13\.41 years/)).toBeInTheDocument()

  const url = new URL(calls[calls.length - 1].url)
  expect(url.searchParams.getAll('ids')).toEqual(['7', '9'])
  expect(url.searchParams.get('rolling_years')).toBe('3')
})

test('start earlier without the youngest fund, and remove a fund', async () => {
  const calls = fakeApi({ 'GET /api/v1/compare/funds': () => comparison() })
  const router = renderAt('/compare?ids=7,9')

  await userEvent.click(await screen.findByRole('button', { name: /Start 2 Jan 2013 without it/ }))
  expect(router.state.location.search).toContain('start=2013-01-02')
  await vi.waitFor(() =>
    expect(new URL(calls[calls.length - 1].url).searchParams.get('start')).toBe('2013-01-02'),
  )

  await userEvent.click(screen.getByRole('button', { name: 'Remove HDFC Flexi Cap Fund' }))
  expect(new URLSearchParams(router.state.location.search).get('ids')).toBe('7')
})

test('nothing picked yet', () => {
  fakeApi({})
  renderAt('/compare')

  expect(screen.getByText('Add funds to compare them')).toBeInTheDocument()
  expect(screen.getByRole('combobox', { name: 'Add a fund' })).toBeInTheDocument()
})
