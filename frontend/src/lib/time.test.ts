import { formatDayMonth, previousWeekday } from '@/lib/time'

test.each([
  ['2026-10-27', '2026-10-26'], // Tuesday → Monday
  ['2026-10-26', '2026-10-23'], // Monday → Friday
  ['2026-10-25', '2026-10-23'], // Sunday → Friday
  ['2026-03-01', '2026-02-27'], // across a month end
])('the weekday before %s is %s', (date, expected) => {
  expect(previousWeekday(date)).toBe(expected)
})

test('a short day and month for the header', () => {
  expect(formatDayMonth('2026-10-23')).toBe('23 Oct')
})
