import type { Schemas } from '@/api/client'

export type InstrumentSummary = Schemas['InstrumentSummary']
export type InstrumentDetail = Schemas['InstrumentDetail']
export type Bucket = Schemas['Share']['bucket']
export type Exposure = Schemas['ClassificationOut']['exposure']

export const BUCKETS: Bucket[] = ['equity', 'debt', 'gold', 'silver', 'other']

export const BUCKET_LABELS: Record<Bucket, string> = {
  equity: 'Equity',
  debt: 'Debt',
  gold: 'Gold',
  silver: 'Silver',
  other: 'Other',
}

export const ASSET_CLASS_LABELS: Record<InstrumentSummary['asset_class'], string> = {
  ...BUCKET_LABELS,
  hybrid: 'Hybrid',
  unclassified: 'Unclassified',
}

export const KIND_LABELS: Record<InstrumentSummary['kind'], string> = {
  stock: 'Stock',
  etf: 'ETF',
  mutual_fund: 'Mutual fund',
}

export const EXPOSURE_LABELS: Record<Exposure, string> = {
  IN: 'India',
  US: 'US',
  GLOBAL: 'Global',
}

const EXCHANGE_LABELS: Record<string, string> = {
  NYSE_ARCA: 'NYSE Arca',
  NYSE_AMERICAN: 'NYSE American',
  NYSE_TEXAS: 'NYSE Texas',
  CBOE: 'Cboe',
  US_OTHER: 'US',
}

export function exchangeLabel(exchange: string): string {
  return EXCHANGE_LABELS[exchange] ?? exchange
}

/** How an instrument is identified at a glance: "NSE · INFY" or "AMFI 122639". */
export function listingLabel(
  instrument: Pick<InstrumentSummary, 'exchange' | 'symbol' | 'amfi_code'>,
) {
  if (instrument.exchange && instrument.symbol) {
    return `${exchangeLabel(instrument.exchange)} · ${instrument.symbol}`
  }
  return instrument.amfi_code ? `AMFI ${instrument.amfi_code}` : '—'
}

/** "Direct · Growth" for a fund variant; empty for anything else. */
export function planLabel(instrument: Pick<InstrumentSummary, 'plan' | 'option'>): string {
  const plan =
    instrument.plan === 'direct' ? 'Direct' : instrument.plan === 'regular' ? 'Regular' : null
  return [plan, instrument.option].filter(Boolean).join(' · ')
}

/** Where a fund (or any instrument) lives in the app. */
export function fundPath(id: number, tab?: 'transactions' | 'details'): string {
  return tab ? `/funds/${id}/${tab}` : `/funds/${id}`
}
