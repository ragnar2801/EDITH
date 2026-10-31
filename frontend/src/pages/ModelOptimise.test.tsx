import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createMemoryRouter, RouterProvider } from 'react-router'

import type { Schemas } from '@/api/client'
import { routes } from '@/app/routes'
import { backtestRun, model, fakeApi, nifty, parag } from '@/test/fake-api'

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

const metrics = (xirr: string, drawdown: string) => ({
  ...backtestRun().result.metrics,
  xirr_pct: xirr,
  max_drawdown_pct: drawdown,
})
const candidate = (weights: [number, string][], xirr: string, drawdown: string) => ({
  funds: weights.map(([id, weight]) => ({
    instrument_id: id,
    name: id === parag.id ? parag.name : nifty.name,
    weight,
  })),
  metrics: metrics(xirr, drawdown),
})

const optimised: Schemas['OptimiseOut'] = {
  start_date: '2020-02-03',
  end_date: '2026-10-30',
  tried: 21,
  eligible: 2,
  points: [
    { xirr_pct: '17.20', max_drawdown_pct: '30.10', eligible: true },
    { xirr_pct: '15.00', max_drawdown_pct: '24.00', eligible: true },
    { xirr_pct: '18.90', max_drawdown_pct: '41.00', eligible: false },
  ],
  model: candidate(
    [
      [parag.id, '60'],
      [nifty.id, '40'],
    ],
    '16.10',
    '28.00',
  ),
  benchmark: {
    instrument_id: nifty.id,
    name: nifty.name,
    curve: [],
    metrics: metrics('12.00', '35.00'),
  },
  top: [
    candidate(
      [
        [parag.id, '85'],
        [nifty.id, '15'],
      ],
      '17.20',
      '30.10',
    ),
    candidate([[nifty.id, '100']], '15.00', '24.00'),
  ],
  warnings: [],
}

test('find the best splits within a drawdown limit, then try one in the backtest', async () => {
  const calls = fakeApi({
    'GET /api/v1/models': () => [model()],
    'GET /api/v1/models/1/backtests': () => [],
    'POST /api/v1/backtests/optimise': () => optimised,
  })
  const router = renderAt('/models/1/optimise')

  const form = await screen.findByRole('form', { name: 'Optimise settings' })
  await userEvent.type(within(form).getByLabelText('Max drawdown (%)'), '32')
  await userEvent.click(within(form).getByRole('button', { name: 'Find splits' }))

  expect(await screen.findByText('Within limits')).toBeInTheDocument()
  expect(screen.getByRole('img', { name: /Every split/ })).toBeInTheDocument()
  const table = screen.getByRole('table', { name: 'Best splits' })
  const rows = within(table).getAllByRole('row')
  expect(within(rows[1]).getByText('Your model')).toBeInTheDocument()
  expect(within(rows[2]).getByText('+17.20%')).toBeInTheDocument()
  expect(within(rows[2]).getByText('85%')).toBeInTheDocument()
  const post = calls.find((call) => call.url.endsWith('/optimise'))
  expect(await post?.json()).toEqual({
    model_id: 1,
    params: {
      strategy: 'sip',
      amount: '10000',
      frequency: 'monthly',
      start: null,
      end: null,
      risk_free_pct: '0',
    },
    goal: 'xirr',
    step: 5,
    min_weight: 0,
    max_weight: 100,
    max_drawdown_pct: '32',
    min_xirr_pct: null,
  })

  await userEvent.click(within(rows[2]).getByRole('button', { name: 'Try this split' }))

  expect(router.state.location.pathname).toBe('/models/1/backtest')
  const backtest = await screen.findByRole('form', { name: 'Backtest settings' })
  expect(within(backtest).getByLabelText(`Weight of ${parag.name}`)).toHaveValue('85')
  expect(within(backtest).getByLabelText(`Weight of ${nifty.name}`)).toHaveValue('15')
  expect(within(backtest).getByLabelText('From')).toHaveValue('2020-02-03')
  expect(within(backtest).getByText('Modified')).toBeInTheDocument()
})

test('a model with more than five funds can’t be optimised', async () => {
  const many = Array.from({ length: 6 }, (_, i) => ({
    ...model().funds[0],
    fund: { ...model().funds[0].fund, id: 100 + i },
  }))
  fakeApi({
    'GET /api/v1/models': () => [model({ funds: many })],
    'GET /api/v1/models/1/backtests': () => [],
  })
  renderAt('/models/1/optimise')

  expect(await screen.findByText('Optimise works with up to 5 funds')).toBeInTheDocument()
})
