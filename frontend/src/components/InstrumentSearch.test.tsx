import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

import { InstrumentSearch } from '@/components/InstrumentSearch'
import { fakeApi, infosys, parag } from '@/test/fake-api'

function renderSearch(onSelect = vi.fn()) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={queryClient}>
      <InstrumentSearch onSelect={onSelect} />
    </QueryClientProvider>,
  )
  return onSelect
}

afterEach(() => {
  vi.unstubAllGlobals()
})

test('typing searches and shows each result with its plan, asset class and other plans', async () => {
  const calls = fakeApi({ 'GET /api/v1/instruments/search': () => [parag, infosys] })
  renderSearch()

  await userEvent.type(screen.getByRole('combobox'), 'parag parikh flexi')

  const option = await screen.findByRole('option', { name: /Parag Parikh Flexi Cap Fund/ })
  expect(option).not.toHaveTextContent('122639') // identity, not identifiers (D-060)
  expect(option).toHaveTextContent('Direct · Growth')
  expect(option).toHaveTextContent('Equity')
  expect(option).toHaveTextContent('1 other plan')
  expect(screen.getByRole('option', { name: /Infosys Limited/ })).toHaveTextContent('NSE · INFY')
  // Debounced: one request for the whole phrase, not one per keystroke.
  const queries = calls.map((call) => new URL(call.url).searchParams.get('q'))
  expect(queries.at(-1)).toBe('parag parikh flexi')
  expect(queries.length).toBeLessThan(4)
})

test('arrow keys and Enter pick a result', async () => {
  fakeApi({ 'GET /api/v1/instruments/search': () => [parag, infosys] })
  const onSelect = renderSearch()
  const input = screen.getByRole('combobox')

  await userEvent.type(input, 'inf')
  await screen.findByRole('option', { name: /Infosys/ })
  await userEvent.keyboard('{ArrowDown}{Enter}')

  expect(onSelect).toHaveBeenCalledWith(infosys)
  expect(input).toHaveValue('')
  expect(screen.queryByRole('listbox')).not.toBeInTheDocument()
})

test('clicking a result picks it', async () => {
  fakeApi({ 'GET /api/v1/instruments/search': () => [parag] })
  const onSelect = renderSearch()

  await userEvent.type(screen.getByRole('combobox'), 'parag')
  await userEvent.click(await screen.findByRole('option', { name: /Parag/ }))

  expect(onSelect).toHaveBeenCalledWith(parag)
})

test('says when nothing matches', async () => {
  fakeApi({ 'GET /api/v1/instruments/search': () => [] })
  renderSearch()

  await userEvent.type(screen.getByRole('combobox'), 'zzzz')

  expect(await screen.findByText('No matches for “zzzz”.')).toBeInTheDocument()
})

test('Escape closes the list', async () => {
  fakeApi({ 'GET /api/v1/instruments/search': () => [parag] })
  renderSearch()

  await userEvent.type(screen.getByRole('combobox'), 'parag')
  await screen.findByRole('listbox')
  await userEvent.keyboard('{Escape}')

  await waitFor(() => expect(screen.queryByRole('listbox')).not.toBeInTheDocument())
})
