import type { Schemas } from '@/api/client'
import type { BacktestForm, Frequency, Rebalance } from '@/lib/backtest'
import type { Model } from '@/lib/models'

export type Goal = Schemas['OptimiseIn']['goal'] & string
export type Candidate = Schemas['Candidate']

/** The search works on models of up to this many funds. */
export const MAX_FUNDS = 5

export const GOAL_LABELS: Record<Goal, string> = {
  xirr: 'Highest XIRR',
  drawdown: 'Lowest max drawdown',
  sharpe: 'Best Sharpe',
}

/** Everything the Optimise form holds, as typed (amounts stay strings). */
export type OptimiseForm = {
  strategy: 'regular' | 'sip'
  capital: string
  /** '' = the model's own rebalance policy. */
  rebalance: '' | Rebalance
  amount: string
  frequency: Frequency
  start: string
  end: string
  riskFree: string
  goal: Goal
  maxDrawdown: string
  minXirr: string
  step: string
  minWeight: string
  maxWeight: string
}

export const DEFAULT_OPTIMISE: OptimiseForm = {
  strategy: 'sip',
  capital: '100000',
  rebalance: '',
  amount: '10000',
  frequency: 'monthly',
  start: '',
  end: '',
  riskFree: '0',
  goal: 'xirr',
  maxDrawdown: '',
  minXirr: '',
  step: '5',
  minWeight: '0',
  maxWeight: '100',
}

const optional = (value: string) => value.trim() || null
const whole = (value: string, fallback: number) => {
  const number = Number(value.trim())
  return Number.isInteger(number) && value.trim() !== '' ? number : fallback
}

export function toRequest(form: OptimiseForm, model: Model): Schemas['OptimiseIn'] {
  const common = {
    start: optional(form.start),
    end: optional(form.end),
    risk_free_pct: form.riskFree.trim() || '0',
  }
  return {
    model_id: model.id,
    params:
      form.strategy === 'regular'
        ? {
            ...common,
            strategy: 'regular',
            capital: form.capital.trim(),
            rebalance: form.rebalance || null,
          }
        : { ...common, strategy: 'sip', amount: form.amount.trim(), frequency: form.frequency },
    goal: form.goal,
    step: whole(form.step, 5),
    min_weight: whole(form.minWeight, 0),
    max_weight: whole(form.maxWeight, 100),
    max_drawdown_pct: optional(form.maxDrawdown),
    min_xirr_pct: optional(form.minXirr),
  }
}

/** What the Backtest tab opens with when I try a split (router state). */
export type BacktestHandoff = { form: Partial<BacktestForm> }

export function handoff(
  form: OptimiseForm,
  candidate: Candidate,
  model: Model,
  start: string,
): BacktestHandoff {
  const funds = new Map(model.funds.map((member) => [member.fund.id, member.fund]))
  return {
    form: {
      strategy: form.strategy,
      capital: form.capital,
      rebalance: form.rebalance,
      amount: form.amount,
      frequency: form.frequency,
      start,
      end: form.end,
      riskFree: form.riskFree,
      split: candidate.funds.map((fund) => ({
        fund: funds.get(fund.instrument_id) ?? {
          id: fund.instrument_id,
          name: fund.name,
          plan: null,
          option: null,
        },
        weight: fund.weight,
      })),
    },
  }
}
