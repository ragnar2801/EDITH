import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createMemoryRouter, RouterProvider } from 'react-router'

import { routes } from '@/app/routes'
import { bucket, fakeApi, fundRef, nifty, parag, problem, syncRun } from '@/test/fake-api'

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

async function addFund(name: RegExp) {
  await userEvent.type(screen.getByRole('combobox', { name: 'Add a fund' }), 'fund')
  await userEvent.click(await screen.findByRole('option', { name }))
}

test('create a model: exact weights, default benchmark, NAVs downloaded, then backtest it', async () => {
  let saved: ReturnType<typeof bucket>[] = []
  const created = bucket({
    funds: bucket().funds.map((member) => ({
      ...member,
      coverage: { first: null, last: null, count: 0 },
    })),
  })
  const calls = fakeApi({
    'GET /api/v1/buckets': () => saved,
    'GET /api/v1/buckets/default-benchmark': () => fundRef(nifty),
    'GET /api/v1/instruments/search': () => [parag, nifty],
    'POST /api/v1/buckets': () => {
      saved = [bucket()]
      return Response.json(created, { status: 201 })
    },
    'POST /api/v1/navs/sync': () => syncRun(),
    'GET /api/v1/navs/status': () => ({ last_run: null, funds: [] }),
  })
  renderAt('/models')

  await userEvent.click((await screen.findAllByRole('link', { name: /New model/ }))[0])
  const form = await screen.findByRole('form', { name: 'Model' })
  await userEvent.type(within(form).getByLabelText('Name'), 'Core')
  await userEvent.selectOptions(within(form).getByLabelText('Rebalance'), 'yearly')
  expect(within(form).getByText('UTI Nifty 50 Index Fund')).toBeInTheDocument() // default
  await addFund(/Parag Parikh/)
  await addFund(/UTI Nifty 50/)
  await userEvent.type(within(form).getByLabelText(/Weight of Parag/), '60')
  await userEvent.type(within(form).getByLabelText(/Weight of UTI/), '39.9')
  expect(within(form).getByText('Total 99.9%')).toHaveClass('text-destructive')
  await userEvent.clear(within(form).getByLabelText(/Weight of UTI/))
  await userEvent.type(within(form).getByLabelText(/Weight of UTI/), '40')
  expect(within(form).getByText('Total 100%')).toHaveClass('text-positive')
  await userEvent.click(within(form).getByRole('button', { name: 'Save model' }))

  // A new model lands on its backtest.
  expect(await screen.findByRole('heading', { name: 'Core' })).toBeInTheDocument()
  expect(screen.getByRole('tab', { name: 'Backtest' })).toHaveAttribute('aria-selected', 'true')
  const post = calls.find((call) => call.method === 'POST' && call.url.endsWith('/buckets'))
  expect(await post?.json()).toEqual({
    name: 'Core',
    description: null,
    rebalance: 'yearly',
    benchmark_id: nifty.id,
    funds: [
      { instrument_id: parag.id, weight: '60' },
      { instrument_id: nifty.id, weight: '40' },
    ],
  })
  const sync = calls.find((call) => call.url.endsWith('/navs/sync'))
  expect(await sync?.json()).toEqual({ instrument_ids: [parag.id, nifty.id] })
})

test('equal weights split 100 exactly', async () => {
  fakeApi({
    'GET /api/v1/buckets': () => [],
    'GET /api/v1/buckets/default-benchmark': () => null,
    'GET /api/v1/instruments/search': () => [parag, nifty, { ...nifty, id: 10, name: 'Third' }],
  })
  renderAt('/models')

  await userEvent.click((await screen.findAllByRole('link', { name: /New model/ }))[0])
  await screen.findByRole('form', { name: 'Model' })
  await addFund(/Parag Parikh/)
  await addFund(/UTI Nifty 50/)
  await addFund(/Third/)
  await userEvent.click(screen.getByRole('button', { name: 'Equal weights' }))

  expect(screen.getByLabelText(/Weight of Parag/)).toHaveValue('33.34')
  expect(screen.getByLabelText(/Weight of Third/)).toHaveValue('33.33')
  expect(screen.getByText('Total 100%')).toBeInTheDocument()
})

test('a refused model shows the reason', async () => {
  fakeApi({
    'GET /api/v1/buckets': () => [bucket()],
    'GET /api/v1/buckets/default-benchmark': () => fundRef(nifty),
    'PUT /api/v1/buckets/1': () => problem(422, 'Weights must add up to 100, not 99.99.'),
  })
  renderAt('/models')

  await userEvent.click(await screen.findByRole('button', { name: 'Actions for Core' }))
  await userEvent.click(screen.getByRole('menuitem', { name: 'Edit' }))
  await userEvent.click(await screen.findByRole('button', { name: 'Save model' }))

  expect(await screen.findByRole('alert')).toHaveTextContent('not 99.99')
})

test('the target model wears a badge; another can be made the target', async () => {
  const settings = {
    target_bucket: { id: 1, name: 'Core' },
    emergency_goal: '150000.00',
    emergency_fund: { ...fundRef(nifty) },
    stagger_fund: null,
    stagger_threshold: '500000.00',
    stagger_months: 6,
    min_per_fund: '500.00',
    updated_at: '2026-10-25T05:00:00Z',
  }
  const calls = fakeApi({
    'GET /api/v1/buckets': () => [bucket(), bucket({ id: 2, name: 'Index only' })],
    'GET /api/v1/plan/settings': () => settings,
    'PUT /api/v1/plan/settings': () => ({
      ...settings,
      target_bucket: { id: 2, name: 'Index only' },
    }),
  })
  renderAt('/models')

  const core = (await screen.findByRole('link', { name: 'Core' })).closest('tr')!
  expect(await within(core).findByText('Target')).toBeInTheDocument()
  await userEvent.click(screen.getByRole('button', { name: 'Actions for Index only' }))
  await userEvent.click(screen.getByRole('menuitem', { name: 'Set as target' }))

  expect(await screen.findByText('Index only is your target')).toBeInTheDocument()
  const put = calls.find((call) => call.method === 'PUT')
  expect(await put?.json()).toEqual({
    target_bucket_id: 2,
    emergency_goal: '150000.00',
    emergency_fund_id: nifty.id,
    stagger_fund_id: null,
    stagger_threshold: '500000.00',
    stagger_months: 6,
    min_per_fund: '500.00',
  })
})

test('a model page shows its funds and links each to its fund page', async () => {
  fakeApi({ 'GET /api/v1/buckets': () => [bucket()] })
  renderAt('/models/1')

  const funds = await screen.findByRole('table', { name: 'Funds' })
  const row = within(funds).getByText('Parag Parikh Flexi Cap Fund').closest('tr')!
  expect(within(row).getByText('60%')).toBeInTheDocument()
  expect(screen.getByText('vs UTI Nifty 50 Index Fund')).toBeInTheDocument()
})

test('duplicate a model: the copy opens in the editor', async () => {
  const copy = bucket({ id: 2, name: 'Core copy' })
  let saved = [bucket()]
  const calls = fakeApi({
    'GET /api/v1/buckets': () => saved,
    'GET /api/v1/buckets/default-benchmark': () => fundRef(nifty),
    'POST /api/v1/buckets/1/duplicate': () => {
      saved = [bucket(), copy]
      return Response.json(copy, { status: 201 })
    },
  })
  renderAt('/models')

  await userEvent.click(await screen.findByRole('button', { name: 'Actions for Core' }))
  await userEvent.click(screen.getByRole('menuitem', { name: 'Duplicate' }))

  expect(await screen.findByText('Copied Core to Core copy')).toBeInTheDocument()
  const form = await screen.findByRole('form', { name: 'Model' })
  expect(await within(form).findByDisplayValue('Core copy')).toBeInTheDocument()
  expect(calls.some((call) => call.method === 'POST' && call.url.endsWith('/1/duplicate'))).toBe(
    true,
  )
})
