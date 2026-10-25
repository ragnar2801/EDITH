import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createMemoryRouter, RouterProvider } from 'react-router'

import { routes } from '@/app/routes'
import { detail, fakeApi, fundRef, holding, lot, parag, problem, syncRun } from '@/test/fake-api'

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

const PATH = `/api/v1/holdings/${parag.id}`
const FUND = { [`GET /api/v1/instruments/${parag.id}`]: () => detail(parag) }
const TRANSACTIONS = `/funds/${parag.id}/transactions`

const dialogClosed = () =>
  waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())

async function setDate(form: HTMLElement, label: string, value: string) {
  const input = within(form).getByLabelText(label)
  await userEvent.clear(input)
  await userEvent.type(input, value)
}

test('the portfolio lists my funds with units and cost from the API', async () => {
  fakeApi({
    'GET /api/v1/holdings': () => [
      {
        fund: fundRef(parag),
        units: '1386.50700000',
        cost: '112500.00',
        lots: 5,
        active_sips: 1,
        nav_last: '2026-10-23',
      },
    ],
  })
  renderAt('/')

  const link = await screen.findByRole('link', { name: /Parag Parikh/ })
  const row = link.closest('tr')!
  expect(within(row).getByText('1,386.507')).toBeInTheDocument()
  expect(within(row).getByText('₹1,12,500.00')).toBeInTheDocument()
  expect(link.getAttribute('href')).toBe(`/funds/${parag.id}`)
})

test('a lump sum into a fund without NAVs: track it, download NAVs, then save', async () => {
  const empty = holding({ lots: [], sips: [], units: '0', cost: '0.00' })
  empty.coverage = { first: null, last: null, count: 0 }
  const calls = fakeApi({
    ...FUND,
    [`GET ${PATH}`]: () => empty,
    [`PUT /api/v1/instruments/${parag.id}/tracking`]: () => ({}),
    'POST /api/v1/navs/sync': () => syncRun(),
    'POST /api/v1/lots': () =>
      Response.json(holding({ lots: [lot({ kind: 'lump_sum', sip_id: null })] }), { status: 201 }),
  })
  renderAt(TRANSACTIONS)

  // The header and the empty state both offer it.
  await userEvent.click((await screen.findAllByRole('button', { name: /Add lump sum/ }))[0])
  const form = screen.getByRole('form', { name: 'Lump sum' })
  await setDate(form, 'Date', '2026-01-06')
  await userEvent.type(within(form).getByLabelText('Amount (₹)'), '100000')
  await userEvent.click(within(form).getByRole('button', { name: 'Save' }))

  await dialogClosed()
  expect(await screen.findByText('₹1,00,000.00 added to Parag Parikh Flexi Cap Fund')).toBeVisible()
  const order = calls.map((call) => `${call.method} ${new URL(call.url).pathname}`)
  expect(order.indexOf('POST /api/v1/navs/sync')).toBeLessThan(order.indexOf('POST /api/v1/lots'))
  const post = calls.find((call) => call.method === 'POST' && call.url.endsWith('/lots'))
  expect(await post?.json()).toEqual({
    instrument_id: parag.id,
    buy_date: '2026-01-06',
    amount: '100000',
    nav: null,
    units: null,
    note: null,
  })
})

test('sell: units per lot I pick, blank lots are left alone', async () => {
  const lots = [
    lot(),
    lot({
      id: 12,
      kind: 'lump_sum',
      sip_id: null,
      buy_date: '2026-01-06',
      units: '1234.568',
      units_remaining: '1234.568',
    }),
    lot({ id: 13, buy_date: '2026-02-06', units: '60.000', units_remaining: '60.000' }),
    lot({ id: 14, buy_date: '2026-03-05', units: '0', units_remaining: '0', skipped: true }),
  ]
  const calls = fakeApi({
    ...FUND,
    [`GET ${PATH}`]: () => holding({ lots }),
    'POST /api/v1/sales': () => Response.json(holding({ lots }), { status: 201 }),
  })
  renderAt(TRANSACTIONS)

  await userEvent.click(await screen.findByRole('button', { name: 'Sell' }))
  const form = screen.getByRole('form', { name: 'Sale' })
  await setDate(form, 'Sale date', '2026-04-10')
  const rows = within(form).getAllByRole('listitem')
  expect(rows).toHaveLength(3) // the skipped instalment has nothing to sell
  await userEvent.click(within(rows[0]).getByRole('button', { name: 'All' }))
  await userEvent.type(within(rows[2]).getByRole('textbox'), '30')
  await userEvent.click(within(form).getByRole('button', { name: 'Sell' }))

  await dialogClosed()
  const post = calls.find((call) => call.url.endsWith('/sales'))
  expect(await post?.json()).toEqual({
    sale_date: '2026-04-10',
    nav: null,
    lots: [
      { lot_id: 11, units: '62.500' },
      { lot_id: 13, units: '30' },
    ],
  })
})

test('a refused sale shows why and keeps the form open', async () => {
  fakeApi({
    ...FUND,
    [`GET ${PATH}`]: () => holding(),
    'POST /api/v1/sales': () => problem(409, 'The 05 Jan 2026 lot has only 62.5 units left.'),
  })
  renderAt(TRANSACTIONS)

  await userEvent.click(await screen.findByRole('button', { name: 'Sell' }))
  const form = screen.getByRole('form', { name: 'Sale' })
  await userEvent.type(within(form).getByRole('textbox', { name: /Units to sell/ }), '70')
  await userEvent.click(within(form).getByRole('button', { name: 'Sell' }))

  expect(await within(form).findByRole('alert')).toHaveTextContent('only 62.5 units left')
})

test('start a SIP; lots show what was sold from them, with an undo', async () => {
  const sold = lot({
    units_remaining: '30.000',
    cost_remaining: '2400.00',
    sales: [
      {
        id: 21,
        sale_date: '2026-04-10',
        units: '32.500',
        nav: '91',
        amount: '2957.50',
        realised: '357.50',
      },
    ],
  })
  const calls = fakeApi({
    ...FUND,
    [`GET ${PATH}`]: () => holding({ lots: [sold] }),
    'POST /api/v1/sips': () => Response.json(holding(), { status: 201 }),
    'DELETE /api/v1/sales/21': () => new Response(null, { status: 204 }),
  })
  renderAt(TRANSACTIONS)

  expect(await screen.findByText(/Sold 32.500 units for ₹2,957.50/)).toBeInTheDocument()
  await userEvent.click(screen.getByRole('button', { name: /Undo the 10 Apr 2026 sale/ }))
  await userEvent.click(screen.getByRole('button', { name: /More for Parag/ }))
  await userEvent.click(screen.getByRole('menuitem', { name: 'Start a SIP' }))
  const form = screen.getByRole('form', { name: 'SIP' })
  await userEvent.type(within(form).getByLabelText('Amount each month (₹)'), '5000')
  await setDate(form, 'Start date', '2026-01-01')
  await userEvent.click(within(form).getByRole('button', { name: 'Start SIP' }))

  await dialogClosed()
  expect(calls.some((call) => call.method === 'DELETE' && call.url.endsWith('/sales/21'))).toBe(
    true,
  )
  const post = calls.find((call) => call.url.endsWith('/sips'))
  expect(await post?.json()).toEqual({
    instrument_id: parag.id,
    amount: '5000',
    day: 5,
    start_date: '2026-01-01',
    end_date: null,
    note: null,
  })
})

test('add a lump sum from anywhere in three steps: fund, amount, save', async () => {
  const empty = holding({ lots: [], sips: [], units: '0', cost: '0.00' })
  const calls = fakeApi({
    'GET /api/v1/holdings': () => [],
    'GET /api/v1/instruments/search': () => [parag],
    [`GET ${PATH}`]: () => empty,
    'POST /api/v1/lots': () =>
      Response.json(holding({ lots: [lot({ kind: 'lump_sum', sip_id: null })] }), { status: 201 }),
  })
  renderAt('/')

  await userEvent.click(screen.getByRole('button', { name: 'Add' }))
  await userEvent.type(screen.getByRole('combobox', { name: 'Fund' }), 'parag')
  await userEvent.click(await screen.findByRole('option', { name: /Parag Parikh/ }))
  const form = await screen.findByRole('form', { name: 'Lump sum' })
  expect(screen.getByRole('radio', { name: 'Sell' })).toBeDisabled() // nothing to sell yet
  // The fund's latest NAV date, not today: today has no NAV until the evening (or on weekends).
  expect(within(form).getByLabelText('Date')).toHaveValue('2026-10-23')
  await userEvent.type(within(form).getByLabelText('Amount (₹)'), '25000')
  await userEvent.click(within(form).getByRole('button', { name: 'Save' }))

  await dialogClosed()
  expect(await screen.findByText('₹25,000.00 added to Parag Parikh Flexi Cap Fund')).toBeVisible()
  const post = calls.find((call) => call.method === 'POST' && call.url.endsWith('/lots'))
  expect(await post?.json()).toMatchObject({ instrument_id: parag.id, amount: '25000' })
})
