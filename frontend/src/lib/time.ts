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
