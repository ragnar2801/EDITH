import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createMemoryRouter, RouterProvider } from 'react-router'

import { routes } from '@/app/routes'
import { detail, fakeApi, infosys, parag, problem } from '@/test/fake-api'

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

test('the instruments page searches and opens the chosen instrument', async () => {
  fakeApi({
    'GET /api/v1/instruments/sources': () => [
      {
        source: 'nse',
        active_instruments: 2968,
        last_run: null,
        last_success: {
          status: 'ok',
          finished_at: '2026-10-24T16:00:00Z',
          rows: 2968,
          added: 0,
          updated: 0,
          deactivated: 0,
          message: null,
        },
      },
    ],
    'GET /api/v1/instruments/search': () => [infosys],
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
  const router = renderAt('/instruments')

  expect(
    await screen.findByText(/2,968 active · refreshed 24 Oct 2026, 9:30 pm/),
  ).toBeInTheDocument()
  await userEvent.type(screen.getByRole('combobox'), 'infos')
  await userEvent.click(await screen.findByRole('option', { name: /Infosys/ }))

  expect(router.state.location.pathname).toBe('/instruments/3')
  expect(await screen.findByRole('heading', { name: 'Infosys Limited' })).toBeInTheDocument()
  expect(screen.getByText('INE009A01021')).toBeInTheDocument()
  expect(screen.getByText('8 Feb 1995')).toBeInTheDocument() // a market date, no time-zone shift
  expect(screen.getByText(/Infosys Technologies Limited/)).toBeInTheDocument()
})

test('a fund page lists its other plans', async () => {
  fakeApi({ 'GET /api/v1/instruments/7': () => detail(parag) })
  renderAt('/instruments/7')

  const plans = (await screen.findByText('Other plans and options')).closest('[data-slot=card]')
  expect(
    within(plans as HTMLElement).getByRole('link', { name: 'Regular · Growth' }),
  ).toHaveAttribute('href', '/instruments/8')
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
  renderAt('/instruments/7')

  await userEvent.click(await screen.findByRole('button', { name: 'Set my own classification' }))
  const form = screen.getByRole('form', { name: 'My classification' })
  await userEvent.clear(within(form).getByLabelText('Equity'))
  await userEvent.type(within(form).getByLabelText('Equity'), '65')
  await userEvent.type(within(form).getByLabelText('Debt'), '35')
  await userEvent.selectOptions(within(form).getByLabelText('Exposure'), 'GLOBAL')
  await userEvent.type(within(form).getByLabelText('Note (optional)'), 'holds US stocks')
  await userEvent.click(within(form).getByRole('button', { name: 'Save' }))

  expect(await screen.findByText('Note: holds US stocks')).toBeInTheDocument()
  expect(screen.getByText('Equity 65%')).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Use the rules again' })).toBeInTheDocument()
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
  renderAt('/instruments/7')

  await userEvent.click(await screen.findByRole('button', { name: 'Set my own classification' }))
  const equity = screen.getByLabelText('Equity')
  await userEvent.clear(equity)
  await userEvent.type(equity, '90')
  await userEvent.click(screen.getByRole('button', { name: 'Save' }))

  expect(await screen.findByRole('alert')).toHaveTextContent('shares must add up to 100, not 90')
})

test('an unknown instrument says so', async () => {
  fakeApi({ 'GET /api/v1/instruments/999': () => problem(404, 'No instrument with id 999.') })
  renderAt('/instruments/999')

  expect(await screen.findByRole('heading', { name: 'Instrument not found' })).toBeInTheDocument()
  expect(screen.getByText('No instrument with id 999.')).toBeInTheDocument()
})
