import type { Schemas } from '@/api/client'

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
}

const optional = (value: string) => value.trim() || null

/** The API request for this form. Incomplete custom rows are left out. */
export function toParams(form: BacktestForm): BacktestParams {
  const common = {
    start: optional(form.start),
    end: optional(form.end),
    risk_free_pct: form.riskFree.trim() || '0',
  }
  switch (form.strategy) {
    case 'regular':
      return {
        ...common,
        strategy: 'regular',
        capital: form.capital.trim(),
        rebalance: form.rebalance || null,
      }
    case 'sip':
      return { ...common, strategy: 'sip', amount: form.amount.trim(), frequency: form.frequency }
    case 'swp':
      return {
        ...common,
        strategy: 'swp',
        corpus: form.corpus.trim(),
        amount: form.withdrawal.trim(),
        frequency: form.frequency,
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

/** Fill the form from a stored run's parameters, so a loaded run can be changed and re-run. */
export function fromParams(params: BacktestParams): BacktestForm {
  const form: BacktestForm = {
    ...DEFAULT_FORM,
    strategy: params.strategy,
    start: params.start ?? '',
    end: params.end ?? '',
    riskFree: params.risk_free_pct ?? '0',
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
