import type { Schemas } from '@/api/client'
import { bucketPath } from '@/lib/buckets'
import { fundPath, planLabel } from '@/lib/instruments'
import { modelPath, REBALANCE_LABELS } from '@/lib/models'

export type CompareKind = 'funds' | 'buckets' | 'models'
export type FundComparison = Schemas['FundComparisonOut']
export type BucketComparison = Schemas['BucketComparisonOut']
export type ModelComparison = Schemas['ModelComparisonOut']
export type AnyComparison = FundComparison | BucketComparison | ModelComparison
/** One fund, bucket or model as the API compares it, without what names it. */
export type Compared = Omit<Schemas['ComparedFundOut'], 'fund'>
export type Money = Schemas['BucketMoney']

/** A compared fund, bucket or model, named for showing. */
export type Item = {
  id: number
  name: string
  detail: string | null
  to: string
  data: Compared
  money?: Money | null
}

/** What every comparison shares, with its items named. */
export type Comparison = Omit<FundComparison, 'items' | 'benchmark'> & {
  items: Item[]
  benchmark: Item | null
}

/** The benchmark's id in correlation pairs. */
export const BENCHMARK = 0

export const COMPARE_PATH = '/compare'
export const COMPARE_PATHS: Record<CompareKind, string> = {
  funds: COMPARE_PATH,
  buckets: `${COMPARE_PATH}/buckets`,
  models: `${COMPARE_PATH}/models`,
}
export const ROLLING_YEARS = [1, 3, 5, 10] as const

/** The Compare page with these picked. */
export function comparePath(ids: number[], kind: CompareKind = 'funds'): string {
  const path = COMPARE_PATHS[kind]
  return ids.length ? `${path}?ids=${ids.join(',')}` : path
}

/** One colour per pick, in the order picked; the benchmark has its own. */
export function seriesColor(index: number): string {
  return `var(--series-${(index % 8) + 1})`
}

function fundItem(row: Schemas['ComparedFundOut']): Item {
  const { fund, ...data } = row
  return { id: fund.id, name: fund.name, detail: planLabel(fund), to: fundPath(fund.id), data }
}

/** Each kind of comparison as the same named items. */
export function named(kind: CompareKind, comparison: AnyComparison): Comparison {
  const benchmark = comparison.benchmark ? fundItem(comparison.benchmark) : null
  if (kind === 'buckets') {
    const items = (comparison as BucketComparison).items.map(
      ({ bucket, model, money, ...data }): Item => ({
        id: bucket.id,
        name: bucket.name,
        detail: [bucket.paper && 'Paper', model?.name].filter(Boolean).join(' · ') || null,
        to: bucketPath(bucket.id),
        data,
        money,
      }),
    )
    return { ...comparison, items, benchmark }
  }
  if (kind === 'models') {
    const items = (comparison as ModelComparison).items.map(
      ({ model, rebalance, ...data }): Item => ({
        id: model.id,
        name: model.name,
        detail: REBALANCE_LABELS[rebalance],
        to: modelPath(model.id),
        data,
      }),
    )
    return { ...comparison, items, benchmark }
  }
  return { ...comparison, items: (comparison as FundComparison).items.map(fundItem), benchmark }
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
