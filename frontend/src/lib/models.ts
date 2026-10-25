import type { Schemas } from '@/api/client'
import type { Bucket, Rebalance } from '@/lib/buckets'

type FundRef = Schemas['FundRef']

/** Where models (buckets, D-061) live in the app. */
export const MODELS_PATH = '/buckets'

export function modelPath(id: number): string {
  return `${MODELS_PATH}/${id}`
}

export function backtestPath(id: number): string {
  return `/backtest/${id}`
}

export type ModelDraft = {
  id?: number
  name: string
  description: string
  rebalance: Rebalance
  benchmark: FundRef | null
  funds: { fund: FundRef; weight: string }[]
}

export function newDraft(benchmark: FundRef | null): ModelDraft {
  return { name: '', description: '', rebalance: 'none', benchmark, funds: [] }
}

export function draftOf(bucket: Bucket): ModelDraft {
  return {
    id: bucket.id,
    name: bucket.name,
    description: bucket.description ?? '',
    rebalance: bucket.rebalance,
    benchmark: bucket.benchmark?.fund ?? null,
    funds: bucket.funds.map((member) => ({ fund: member.fund, weight: member.weight })),
  }
}
