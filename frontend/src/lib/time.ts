const IST = new Intl.DateTimeFormat('en-IN', {
  dateStyle: 'medium',
  timeStyle: 'short',
  timeZone: 'Asia/Kolkata',
})

/** Show a UTC timestamp from the API in IST (D-032), e.g. "24 Oct 2026, 9:30 pm". */
export function formatDateTime(utc: string): string {
  return IST.format(new Date(utc))
}

/** Show a plain market date ("2021-07-23") without any time-zone shift. */
export function formatDate(date: string): string {
  const [year, month, day] = date.split('-').map(Number)
  return new Intl.DateTimeFormat('en-IN', { dateStyle: 'medium', timeZone: 'UTC' }).format(
    new Date(Date.UTC(year, month - 1, day)),
  )
}

/** Short month label for chart axes: "Oct 2026". */
export function formatMonthYear(date: string): string {
  const [year, month] = date.split('-').map(Number)
  return new Intl.DateTimeFormat('en-IN', {
    month: 'short',
    year: 'numeric',
    timeZone: 'UTC',
  }).format(new Date(Date.UTC(year, month - 1, 1)))
}

/** Today's date in India, where NAV dates live, as "2026-10-25". */
export function todayIst(): string {
  return new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Kolkata' }).format(new Date())
}

/** The weekday before `date` ("2026-10-26", a Monday → "2026-10-23"): the latest NAV date
 * to expect, since a day's NAVs are published that night. Holidays aren't known here. */
export function previousWeekday(date: string): string {
  const [year, month, day] = date.split('-').map(Number)
  const d = new Date(Date.UTC(year, month - 1, day))
  do d.setUTCDate(d.getUTCDate() - 1)
  while (d.getUTCDay() === 0 || d.getUTCDay() === 6)
  return d.toISOString().slice(0, 10)
}

/** "23 Oct" for compact places such as the header. */
export function formatDayMonth(date: string): string {
  const [year, month, day] = date.split('-').map(Number)
  return new Intl.DateTimeFormat('en-IN', {
    day: 'numeric',
    month: 'short',
    timeZone: 'UTC',
  }).format(new Date(Date.UTC(year, month - 1, day)))
}
