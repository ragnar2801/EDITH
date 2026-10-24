import { formatMoney } from './money'

test('formats INR with Indian digit grouping', () => {
  expect(formatMoney({ amount: '1234567.89', currency: 'INR' })).toBe('₹12,34,567.89')
})

test('formats USD', () => {
  expect(formatMoney({ amount: '1234.5', currency: 'USD' })).toBe('$1,234.50')
})

test('keeps every digit of amounts too large for a float', () => {
  // As a JS number, 99999999999999.99 would print as 99,999,999,999,999.98 or similar.
  expect(formatMoney({ amount: '99999999999999.99', currency: 'USD' })).toBe(
    '$99,999,999,999,999.99',
  )
})
