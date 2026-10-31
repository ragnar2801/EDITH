import type { Schemas } from '@/api/client'

export type Comparison = Schemas['FundComparisonOut']
export type ComparedFund = Schemas['ComparedFundOut']

export const COMPARE_PATH = '/compare'
export const ROLLING_YEARS = [1, 3, 5, 10] as const

/** The Compare page with these funds picked. */
export function comparePath(ids: number[]): string {
  return ids.length ? `${COMPARE_PATH}?ids=${ids.join(',')}` : COMPARE_PATH
}

/** One colour per fund, in the order picked; the benchmark has its own. */
export function seriesColor(index: number): string {
  return `var(--series-${(index % 8) + 1})`
}

/**
 * Which rows hold the best figure in a column: the highest, or with `lower` the lowest.
 * Only compares the API's strings; nothing is computed from them.
 */
export function bestRows(
  values: (string | number | null | undefined)[],
  { lower = false } = {},
): Set<number> {
  const present = values
    .map((value, row) => ({ row, value: value === null || value === undefined ? null : +value }))
    .filter((cell): cell is { row: number; value: number } => cell.value !== null)
  if (present.length < 2) return new Set()
  const pick = lower ? Math.min : Math.max
  const best = pick(...present.map((cell) => cell.value))
  return new Set(present.filter((cell) => cell.value === best).map((cell) => cell.row))
}
