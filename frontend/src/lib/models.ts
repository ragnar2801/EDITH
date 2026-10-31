import type { Schemas } from '@/api/client'

type FundRef = Schemas['FundRef']

export type Model = Schemas['ModelOut']
export type Rebalance = Model['rebalance']

export const REBALANCE_LABELS: Record<Rebalance, string> = {
  none: 'No rebalancing',
  monthly: 'Rebalance monthly',
  quarterly: 'Rebalance quarterly',
  yearly: 'Rebalance yearly',
}

/** Where models live in the app. */
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

export function draftOf(model: Model): ModelDraft {
  return {
    id: model.id,
    name: model.name,
    description: model.description ?? '',
    rebalance: model.rebalance,
    benchmark: model.benchmark?.fund ?? null,
    funds: model.funds.map((member) => ({ fund: member.fund, weight: member.weight })),
  }
}
