import type { Schemas } from '@/api/client'
import type { Bucket, Rebalance } from '@/lib/buckets'

type FundRef = Schemas['FundRef']

/** Where models (buckets) live in the app. */
export const MODELS_PATH = '/models'

export function modelPath(id: number, tab?: 'backtest' | 'optimise' | 'edit'): string {
  return tab ? `${MODELS_PATH}/${id}/${tab}` : `${MODELS_PATH}/${id}`
}

export function backtestPath(id: number): string {
  return modelPath(id, 'backtest')
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
