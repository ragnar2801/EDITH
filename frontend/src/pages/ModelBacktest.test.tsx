import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createMemoryRouter, RouterProvider } from 'react-router'

import { routes } from '@/app/routes'
import { backtestRun, bucket, fakeApi, parag, problem } from '@/test/fake-api'

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

const tile = (label: string) => screen.getByText(label).closest('div') as HTMLElement

test('run a SIP and see it next to the benchmark', async () => {
  const calls = fakeApi({
    'GET /api/v1/buckets': () => [bucket()],
    'GET /api/v1/buckets/1/backtests': () => [],
    'POST /api/v1/backtests': () => backtestRun(),
  })
  renderAt('/models/1/backtest')

  const form = await screen.findByRole('form', { name: 'Backtest settings' })
  expect(screen.getByRole('heading', { name: 'Core' })).toBeInTheDocument() // the model is the page
  await userEvent.click(within(form).getByRole('radio', { name: 'SIP' }))
  await userEvent.clear(within(form).getByLabelText('SIP amount (₹)'))
  await userEvent.type(within(form).getByLabelText('SIP amount (₹)'), '15000.50')
  await userEvent.type(within(form).getByLabelText('From'), '2015-01-01')
  await userEvent.click(within(form).getByRole('button', { name: 'Run backtest' }))

  expect(await screen.findByText('Final value')).toBeInTheDocument()
  expect(within(tile('XIRR')).getByText('+16.56%')).toHaveClass('text-positive')
  expect(within(tile('XIRR')).getByText('Benchmark: +10.15%')).toBeInTheDocument()
  expect(within(tile('Max drawdown')).getByText('−35.14%')).toBeInTheDocument()
  expect(screen.getByRole('img', { name: 'Backtest value over time' })).toBeInTheDocument()
  expect(screen.getByText('1690.12345678')).toBeInTheDocument()
  const post = calls.find((call) => call.method === 'POST')
  expect(await post?.json()).toEqual({
    bucket_id: 1,
    save: false,
    params: {
      strategy: 'sip',
      amount: '15000.50',
      frequency: 'monthly',
      start: '2015-01-01',
      end: null,
      risk_free_pct: '0',
    },
  })
})

test('a zoom preset asks the backend for the window figures', async () => {
  const calls = fakeApi({
    'GET /api/v1/buckets': () => [bucket()],
    'GET /api/v1/buckets/1/backtests': () => [],
    'POST /api/v1/backtests': () => backtestRun(),
    'GET /api/v1/backtests/41/interval': () => ({
      start_date: '2025-10-23',
      end_date: '2026-10-23',
      start_value: '120000.00',
      end_value: '252000.00',
      return_pct: '8.18',
      max_drawdown_pct: '12.40',
      invested: '110000.00',
      withdrawn: '0.00',
      benchmark_return_pct: '-1.20',
    }),
  })
  renderAt('/models/1/backtest')
  await userEvent.click(await screen.findByRole('button', { name: 'Run backtest' }))
  await screen.findByText('Final value')

  await userEvent.click(screen.getByRole('button', { name: '1Y' }))

  expect(await screen.findByText('+8.18%')).toBeInTheDocument()
  expect(screen.getByText('Benchmark: −1.20%')).toBeInTheDocument()
  const interval = calls.find((call) => call.url.includes('/interval'))
  expect(new URL(interval!.url).search).toBe('?start=2025-10-23&end=2026-10-23')
})

test('save a run, then load a saved custom run into the form', async () => {
  let saved: ReturnType<typeof backtestRun>[] = []
  const custom = backtestRun({
    id: 7,
    saved: true,
    name: 'Switch',
    strategy: 'custom',
    params: {
      strategy: 'custom',
      start: null,
      end: null,
      risk_free_pct: '0',
      positions: [
        { instrument_id: parag.id, entry: '2025-01-01', exit: '2025-10-23', amount: '50000' },
      ],
      trades: [],
    },
  })
  custom.result = {
    ...custom.result,
    strategy: 'custom',
    trades: [
      {
        date: '2025-01-01',
        instrument_id: parag.id,
        name: parag.name,
        side: 'buy',
        units: '500.00000000',
        nav: '100',
        amount: '50000.00',
      },
      {
        date: '2025-10-23',
        instrument_id: parag.id,
        name: parag.name,
        side: 'sell',
        units: '500.00000000',
        nav: '110.5',
        amount: '55250.00',
      },
    ],
  }
  const calls = fakeApi({
    'GET /api/v1/buckets': () => [bucket()],
    'GET /api/v1/buckets/1/backtests': () => saved,
    'POST /api/v1/backtests': () => backtestRun(),
    'PATCH /api/v1/backtests/41': () => {
      saved = [custom]
      return { ...backtestRun(), saved: true, name: 'Ten k' }
    },
    'GET /api/v1/backtests/7': () => custom,
  })
  renderAt('/models/1/backtest')
  await userEvent.click(await screen.findByRole('button', { name: 'Run backtest' }))
  await userEvent.type(await screen.findByLabelText('Name for this run'), 'Ten k')
  await userEvent.click(screen.getByRole('button', { name: 'Save run' }))

  const patch = calls.find((call) => call.method === 'PATCH')
  expect(await patch?.json()).toEqual({ saved: true, name: 'Ten k' })
  await userEvent.selectOptions(await screen.findByLabelText('Saved runs'), '7')

  expect(await screen.findByText('Profit and loss per fund')).toBeInTheDocument()
  expect(screen.getByRole('radio', { name: 'Custom' })).toHaveAttribute('aria-checked', 'true')
  expect(screen.getByLabelText('Position 1 fund')).toHaveValue(String(parag.id))
  expect(screen.getByText('₹55,250.00')).toBeInTheDocument()
  expect(screen.getByText('₹110.50')).toBeInTheDocument() // NAV with its own places
})

test('a refused run shows the reason', async () => {
  fakeApi({
    'GET /api/v1/buckets': () => [bucket()],
    'GET /api/v1/buckets/1/backtests': () => [],
    'POST /api/v1/backtests': () =>
      problem(422, 'No NAVs yet for UTI Nifty 50 Index Fund; sync NAVs first.'),
  })
  renderAt('/models/1/backtest')

  await userEvent.click(await screen.findByRole('button', { name: 'Run backtest' }))

  expect(await screen.findByRole('alert')).toHaveTextContent('sync NAVs first')
})

test('the Backtest tab is part of the model page', async () => {
  fakeApi({
    'GET /api/v1/buckets': () => [bucket()],
    'GET /api/v1/buckets/1/backtests': () => [],
  })
  const router = renderAt('/models/1')

  await userEvent.click(await screen.findByRole('tab', { name: 'Backtest' }))

  expect(router.state.location.pathname).toBe('/models/1/backtest')
  expect(await screen.findByText('Ready to backtest Core')).toBeInTheDocument()
  expect(screen.queryByRole('combobox', { name: 'Model' })).not.toBeInTheDocument() // no picker
})
