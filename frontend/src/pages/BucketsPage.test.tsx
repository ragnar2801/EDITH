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

test('create a bucket: exact weights, default benchmark, then its NAVs are downloaded', async () => {
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
  renderAt('/buckets')

  await userEvent.click(await screen.findByRole('button', { name: /New bucket/ }))
  const form = screen.getByRole('form', { name: 'Bucket' })
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
  await userEvent.click(within(form).getByRole('button', { name: 'Save bucket' }))

  await screen.findByText('vs UTI Nifty 50 Index Fund', { exact: false })
  const links = screen.getAllByRole('link', { name: 'Backtest' })
  expect(links.map((link) => link.getAttribute('href'))).toContain('/backtest/1')
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
  renderAt('/buckets')

  await userEvent.click((await screen.findAllByRole('button', { name: /New bucket/ }))[0])
  await addFund(/Parag Parikh/)
  await addFund(/UTI Nifty 50/)
  await addFund(/Third/)
  await userEvent.click(screen.getByRole('button', { name: 'Equal weights' }))

  expect(screen.getByLabelText(/Weight of Parag/)).toHaveValue('33.34')
  expect(screen.getByLabelText(/Weight of Third/)).toHaveValue('33.33')
  expect(screen.getByText('Total 100%')).toBeInTheDocument()
})

test('a refused bucket shows the reason', async () => {
  fakeApi({
    'GET /api/v1/buckets': () => [bucket()],
    'GET /api/v1/buckets/default-benchmark': () => fundRef(nifty),
    'PUT /api/v1/buckets/1': () => problem(422, 'Weights must add up to 100, not 99.99.'),
  })
  renderAt('/buckets')

  await userEvent.click(await screen.findByRole('button', { name: 'Edit' }))
  await userEvent.click(screen.getByRole('button', { name: 'Save bucket' }))

  expect(await screen.findByRole('alert')).toHaveTextContent('not 99.99')
})

test('the dashboard lists buckets', async () => {
  fakeApi({
    'GET /api/v1/buckets': () => [bucket()],
    'GET /api/v1/navs/status': () => ({ last_run: syncRun(), funds: [] }),
  })
  renderAt('/')

  expect(await screen.findByText('Core')).toBeInTheDocument()
  expect(screen.getByText(/2 funds · Rebalance yearly · vs UTI Nifty 50 Index Fund/)).toBeVisible()
  expect(screen.getByText('26 NAVs added')).toBeInTheDocument()
})
