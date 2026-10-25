/** Zoom presets for date charts. Date arithmetic only; no amounts are touched. */
export type RangeKey = '1M' | '3M' | '6M' | 'YTD' | '1Y' | '3Y' | '5Y' | 'MAX'

export const RANGES: { key: RangeKey; label: string; months?: number; ytd?: boolean }[] = [
  { key: '1M', label: '1M', months: 1 },
  { key: '3M', label: '3M', months: 3 },
  { key: '6M', label: '6M', months: 6 },
  { key: 'YTD', label: 'YTD', ytd: true },
  { key: '1Y', label: '1Y', months: 12 },
  { key: '3Y', label: '3Y', months: 36 },
  { key: '5Y', label: '5Y', months: 60 },
  { key: 'MAX', label: 'Max' },
]

/** `months` before a plain date ("2026-10-23"), staying in UTC so nothing shifts. */
export function shiftMonths(date: string, months: number): string {
  const [year, month, day] = date.split('-').map(Number)
  const shifted = new Date(Date.UTC(year, month - 1, day))
  shifted.setUTCMonth(shifted.getUTCMonth() - months)
  return shifted.toISOString().slice(0, 10)
}

/** First date shown for a preset ending on `last`, or `null` for the whole history. */
export function rangeStart(key: RangeKey, last: string): string | null {
  const range = RANGES.find((r) => r.key === key)!
  if (range.ytd) return `${last.slice(0, 4)}-01-01`
  if (range.months) return shiftMonths(last, range.months)
  return null
}

/** Presets that would show less than the whole history from `first` to `last`. */
export function usefulRanges(first: string, last: string) {
  return RANGES.map((range) => {
    const start = rangeStart(range.key, last)
    return { ...range, disabled: range.key !== 'MAX' && (start === null || start <= first) }
  })
}
