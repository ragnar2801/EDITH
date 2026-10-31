import type { Schemas } from '@/api/client'
import type { BacktestRun } from '@/api/queries'
import type { Bucket } from '@/lib/buckets'
import { toBasisPoints } from '@/lib/weights'

export type BacktestParams = Schemas['BacktestIn']['params']
export type Strategy = BacktestParams['strategy']
export type Frequency = Schemas['SipParams']['frequency']
export type Rebalance = NonNullable<Schemas['RegularParams']['rebalance']>

export const STRATEGY_LABELS: Record<Strategy, string> = {
  regular: 'Lump sum',
  sip: 'SIP',
  swp: 'SWP',
  custom: 'Custom',
}

export const FREQUENCY_LABELS: Record<Frequency, string> = {
  weekly: 'Weekly',
  monthly: 'Monthly',
  quarterly: 'Quarterly',
}

export type PositionRow = { fundId: number | null; entry: string; exit: string; amount: string }
export type TradeRow = {
  fundId: number | null
  date: string
  side: 'buy' | 'sell'
  /** By rupee amount, by units, or (sells) everything held. */
  by: 'amount' | 'units' | 'all'
  quantity: string
}

/** A fund in the split being tried (D-075). Loaded runs may only know a fund's name. */
export type SplitFund = Pick<Schemas['FundRef'], 'id' | 'name' | 'plan' | 'option'>
export type SplitRow = { fund: SplitFund; weight: string }

/** Everything the form holds, as typed. Amounts stay strings end to end (D-032). */
export type BacktestForm = {
  strategy: Strategy
  capital: string
  /** '' = use the bucket's own rebalance policy. */
  rebalance: '' | Rebalance
  amount: string
  frequency: Frequency
  corpus: string
  withdrawal: string
  start: string
  end: string
  riskFree: string
  customMode: 'positions' | 'trades'
  positions: PositionRow[]
  trades: TradeRow[]
  /** The funds and weights to run (not custom runs); starts as the model's own. */
  split: SplitRow[]
}

export const blankPosition = (): PositionRow => ({
  fundId: null,
  entry: '',
  exit: '',
  amount: '100000',
})
export const blankTrade = (): TradeRow => ({
  fundId: null,
  date: '',
  side: 'buy',
  by: 'amount',
  quantity: '10000',
})

export const DEFAULT_FORM: BacktestForm = {
  strategy: 'sip',
  capital: '100000',
  rebalance: '',
  amount: '10000',
  frequency: 'monthly',
  corpus: '5000000',
  withdrawal: '30000',
  start: '',
  end: '',
  riskFree: '0',
  customMode: 'positions',
  positions: [blankPosition()],
  trades: [blankTrade()],
  split: [],
}

/** The model's own funds and weights, as split rows. */
export function modelSplit(bucket: Bucket): SplitRow[] {
  return bucket.funds.map((member) => ({ fund: member.fund, weight: member.weight }))
}

/** True when the split isn't the model's: other funds, or a weight that isn't the same. */
export function splitModified(split: SplitRow[], bucket: Bucket): boolean {
  if (split.length !== bucket.funds.length) return true
  const model = new Map(bucket.funds.map((m) => [m.fund.id, toBasisPoints(m.weight)]))
  return split.some((row) => {
    const points = toBasisPoints(row.weight)
    return points === null || model.get(row.fund.id) !== points
  })
}

const optional = (value: string) => value.trim() || null

/** The API request for this form. Incomplete custom rows are left out; the split is sent
 * only when it isn't the model's own. */
export function toParams(form: BacktestForm, bucket: Bucket): BacktestParams {
  const common = {
    start: optional(form.start),
    end: optional(form.end),
    risk_free_pct: form.riskFree.trim() || '0',
  }
  const split = splitModified(form.split, bucket)
    ? form.split.map((row) => ({ instrument_id: row.fund.id, weight: row.weight.trim() }))
    : null
  switch (form.strategy) {
    case 'regular':
      return {
        ...common,
        strategy: 'regular',
        capital: form.capital.trim(),
        rebalance: form.rebalance || null,
        ...(split && { split }),
      }
    case 'sip':
      return {
        ...common,
        strategy: 'sip',
        amount: form.amount.trim(),
        frequency: form.frequency,
        ...(split && { split }),
      }
    case 'swp':
      return {
        ...common,
        strategy: 'swp',
        corpus: form.corpus.trim(),
        amount: form.withdrawal.trim(),
        frequency: form.frequency,
        ...(split && { split }),
      }
    case 'custom':
      return {
        ...common,
        strategy: 'custom',
        positions:
          form.customMode === 'positions'
            ? form.positions
                .filter((row) => row.fundId !== null && row.entry && row.amount.trim())
                .map((row) => ({
                  instrument_id: row.fundId!,
                  entry: row.entry,
                  exit: optional(row.exit),
                  amount: row.amount.trim(),
                }))
            : [],
        trades:
          form.customMode === 'trades'
            ? form.trades
                .filter((row) => row.fundId !== null && row.date)
                .map((row) => ({
                  instrument_id: row.fundId!,
                  date: row.date,
                  side: row.side,
                  amount: row.by === 'amount' ? row.quantity.trim() : null,
                  units: row.by === 'units' ? row.quantity.trim() : null,
                  sell_all: row.by === 'all',
                }))
            : [],
      }
  }
}

/** The split a stored run used, with each fund's name from the model or the run. */
function runSplit(run: BacktestRun, bucket: Bucket): SplitRow[] {
  const params = run.params
  if (params.strategy === 'custom' || !params.split) return modelSplit(bucket)
  const known = new Map(bucket.funds.map((member) => [member.fund.id, member.fund]))
  const named = new Map(run.result.funds.map((fund) => [fund.instrument_id, fund.name]))
  return params.split.map((row) => ({
    fund: known.get(row.instrument_id) ?? {
      id: row.instrument_id,
      name: named.get(row.instrument_id) ?? `Fund ${row.instrument_id}`,
      plan: null,
      option: null,
    },
    weight: row.weight,
  }))
}

/** Fill the form from a stored run, so a loaded run can be changed and re-run. */
export function fromRun(run: BacktestRun, bucket: Bucket): BacktestForm {
  const params = run.params
  const form: BacktestForm = {
    ...DEFAULT_FORM,
    strategy: params.strategy,
    start: params.start ?? '',
    end: params.end ?? '',
    riskFree: params.risk_free_pct ?? '0',
    split: runSplit(run, bucket),
  }
  switch (params.strategy) {
    case 'regular':
      return { ...form, capital: params.capital, rebalance: params.rebalance ?? '' }
    case 'sip':
      return { ...form, amount: params.amount, frequency: params.frequency ?? 'monthly' }
    case 'swp':
      return {
        ...form,
        corpus: params.corpus,
        withdrawal: params.amount,
        frequency: params.frequency ?? 'monthly',
      }
    case 'custom': {
      const trades = params.trades ?? []
      return {
        ...form,
        customMode: trades.length > 0 ? 'trades' : 'positions',
        positions: (params.positions ?? []).map((p) => ({
          fundId: p.instrument_id,
          entry: p.entry,
          exit: p.exit ?? '',
          amount: p.amount,
        })),
        trades: trades.map((t) => ({
          fundId: t.instrument_id,
          date: t.date,
          side: t.side,
          by: t.sell_all ? 'all' : t.units ? 'units' : 'amount',
          quantity: t.units ?? t.amount ?? '',
        })),
      }
    }
  }
}
