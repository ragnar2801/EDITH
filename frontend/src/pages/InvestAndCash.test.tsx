import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createMemoryRouter, RouterProvider } from 'react-router'

import type { Schemas } from '@/api/client'
import { routes } from '@/app/routes'
import { fakeApi, fundRef, parag, problem } from '@/test/fake-api'

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

const nifty = { ...parag, id: 9, name: 'UTI Nifty 50 Index Fund', amfi_code: '120716' }

const emergency: Schemas['EmergencyOut'] = {
  goal: '150000.00',
  cash: '50000.00',
  fund: null,
  total: '50000.00',
  shortfall: '100000.00',
}

const cash: Schemas['CashOut'] = {
  accounts: [
    {
      id: 1,
      name: 'Salary',
      balance: '100000.00',
      earmark: 'deployable',
      note: null,
      updated_at: '2026-10-25T05:00:00Z',
    },
  ],
  deployable: '100000.00',
  reserved: '0.00',
  emergency,
}

const settings: Schemas['SettingsOut'] = {
  target_bucket: { id: 4, name: 'Core' },
  emergency_goal: '150000.00',
  emergency_fund: null,
  stagger_fund: null,
  stagger_threshold: '500000.00',
  stagger_months: 6,
  min_per_fund: '500.00',
  updated_at: '2026-10-25T05:00:00Z',
}

function planRow(fund: typeof parag, extra: Partial<Schemas['PlanFundOut']>) {
  return {
    fund: fundRef(fund),
    weight: '60.00',
    units: '600',
    nav: '100',
    nav_date: '2026-10-23',
    value_now: '60000.00',
    share_now: '75.00',
    invest: '18000.00',
    value_after: '78000.00',
    share_after: '60.00',
    ...extra,
  }
}

const plan: Schemas['PlanOut'] = {
  amount: '650000.00',
  bucket: { id: 4, name: 'Core' },
  emergency,
  emergency_topup: '50000.00',
  to_funds: '600000.00',
  invested: '600000.00',
  left: '0.00',
  funds: [
    planRow(parag, { invest: '388000.00' }),
    planRow(nifty, { weight: '40.00', invest: '212000.00', share_after: '40.00' }),
  ],
  value_now: '80000.00',
  value_after: '680000.00',
  stagger_fund: null,
  months: [
    { month: '2026-10-01', total: '100000.00', amounts: ['64666.00', '35333.00'] },
    { month: '2026-11-01', total: '100000.00', amounts: ['64670.00', '35335.00'] },
  ],
  ignored: [],
  min_per_fund: '500.00',
}

test('the plan shows the API figures, with a stagger table for large amounts', async () => {
  const calls = fakeApi({
    'GET /api/v1/cash': () => cash,
    'GET /api/v1/plan/settings': () => settings,
    'POST /api/v1/plan': () => plan,
  })
  renderAt('/invest')

  const form = await screen.findByRole('form', { name: 'Make a plan' })
  const amount = within(form).getByLabelText('Amount (₹)')
  expect(amount).toHaveValue('100000.00') // investable cash, to start with
  await userEvent.clear(amount)
  await userEvent.type(amount, '650000')
  await userEvent.click(within(form).getByRole('button', { name: 'Make plan' }))

  const table = await screen.findByRole('table', { name: 'Plan per fund' })
  const row = within(table).getByText('Parag Parikh Flexi Cap Fund').closest('tr')!
  expect(within(row).getByText('₹3,88,000.00')).toBeInTheDocument()
  expect(within(row).getByText('75.00%')).toBeInTheDocument()
  const months = screen.getByRole('table', { name: 'Monthly transfers' })
  expect(within(months).getByText('₹64,666.00')).toBeInTheDocument()
  expect(screen.getByText(/From a liquid or arbitrage fund · 2 months/)).toBeInTheDocument()

  const request = calls.find((call) => call.url.endsWith('/api/v1/plan'))!
  expect(await request.json()).toEqual({ amount: '650000' })
})

test('a blank amount asks for all investable cash, and errors are shown', async () => {
  const calls = fakeApi({
    'GET /api/v1/cash': () => cash,
    'GET /api/v1/plan/settings': () => settings,
    'POST /api/v1/plan': () => problem(422, 'Friday has no NAV for Parag Parikh; sync NAVs first.'),
  })
  renderAt('/invest')

  await userEvent.clear(await screen.findByLabelText('Amount (₹)'))
  await userEvent.click(screen.getByRole('button', { name: 'Make plan' }))

  expect(await screen.findByRole('alert')).toHaveTextContent('sync NAVs first')
  const request = calls.find((call) => call.url.endsWith('/api/v1/plan'))!
  expect(await request.json()).toEqual({})
})

test('without a target model, Invest asks for one', async () => {
  fakeApi({
    'GET /api/v1/cash': () => cash,
    'GET /api/v1/plan/settings': () => ({ ...settings, target_bucket: null }),
  })
  renderAt('/invest')

  expect(await screen.findByText('Choose a target model')).toBeInTheDocument()
  expect(screen.getByRole('link', { name: 'Choose' })).toHaveAttribute('href', '/models')
  expect(screen.queryByRole('button', { name: 'Make plan' })).not.toBeInTheDocument()
})

test('the Cash tab shows what cash is for', async () => {
  fakeApi({ 'GET /api/v1/cash': () => cash })
  renderAt('/cash')

  const accounts = await screen.findByRole('table', { name: 'Cash accounts' })
  expect(within(accounts).getByText('Investable')).toBeInTheDocument()
  expect(screen.getByText('Emergency shortfall').nextSibling).toHaveTextContent('₹1,00,000.00')
})

test('adding an account sends the balance as a string', async () => {
  const calls = fakeApi({
    'GET /api/v1/cash': () => cash,
    'GET /api/v1/plan/settings': () => ({ ...settings, target_bucket: null }),
    'POST /api/v1/cash/accounts': () => Response.json(cash.accounts[0], { status: 201 }),
  })
  renderAt('/cash')

  await userEvent.click(await screen.findByRole('button', { name: 'Add account' }))
  const form = screen.getByRole('form', { name: 'Add account' })
  await userEvent.type(within(form).getByLabelText('Name'), 'Savings')
  await userEvent.type(within(form).getByLabelText('Balance (₹)'), '250000.50')
  await userEvent.selectOptions(within(form).getByLabelText('Purpose'), 'emergency')
  await userEvent.click(within(form).getByRole('button', { name: 'Add account' }))

  const request = calls.find((call) => call.method === 'POST')!
  expect(await request.json()).toEqual({
    name: 'Savings',
    balance: '250000.50',
    earmark: 'emergency',
    note: null,
  })
})

test('deleting an account asks first, then confirms with a toast', async () => {
  const calls = fakeApi({
    'GET /api/v1/cash': () => cash,
    'GET /api/v1/plan/settings': () => settings,
    'DELETE /api/v1/cash/accounts/1': () => new Response(null, { status: 204 }),
  })
  renderAt('/cash')

  await userEvent.click(await screen.findByRole('button', { name: 'Actions for Salary' }))
  await userEvent.click(screen.getByRole('menuitem', { name: 'Delete' }))
  const dialog = screen.getByRole('alertdialog', { name: 'Delete Salary?' })
  await userEvent.click(within(dialog).getByRole('button', { name: 'Delete' }))

  expect(await screen.findByText('Salary deleted')).toBeInTheDocument()
  expect(calls.some((call) => call.method === 'DELETE')).toBe(true)
})
