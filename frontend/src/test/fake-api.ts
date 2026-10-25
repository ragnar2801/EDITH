import type { Schemas } from '@/api/client'

type Handler = (request: Request) => unknown | Promise<unknown>

/**
 * Replace fetch with a tiny fake API: each handler answers one method + path. A handler
 * returns a JSON body, or a Response for anything else (errors, status codes).
 */
export function fakeApi(handlers: Record<string, Handler>) {
  const calls: Request[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn(async (request: Request) => {
      calls.push(request.clone())
      const url = new URL(request.url)
      const handler = handlers[`${request.method} ${url.pathname}`]
      if (!handler) return new Response('offline', { status: 503 })
      const result = await handler(request)
      return result instanceof Response ? result : Response.json(result)
    }),
  )
  return calls
}

export function problem(status: number, detail: string): Response {
  return Response.json(
    { type: 'about:blank', title: 'Error', status, detail },
    { status, headers: { 'content-type': 'application/problem+json' } },
  )
}

export const parag: Schemas['InstrumentSummary'] = {
  id: 7,
  kind: 'mutual_fund',
  name: 'Parag Parikh Flexi Cap Fund',
  market: 'IN',
  currency: 'INR',
  exchange: null,
  symbol: null,
  amfi_code: '122639',
  isin: 'INF879O01027',
  fund_house: 'PPFAS Mutual Fund',
  fund_category: 'Equity Scheme - Flexi Cap Fund',
  plan: 'direct',
  option: 'Growth',
  asset_class: 'equity',
  exposure: 'IN',
  is_active: true,
  variants: [{ id: 8, amfi_code: '122640', plan: 'regular', option: 'Growth', is_active: true }],
}

export const infosys: Schemas['InstrumentSummary'] = {
  ...parag,
  id: 3,
  kind: 'stock',
  name: 'Infosys Limited',
  exchange: 'NSE',
  symbol: 'INFY',
  amfi_code: null,
  isin: 'INE009A01021',
  fund_house: null,
  fund_category: null,
  plan: null,
  option: null,
  variants: [],
}

export function detail(
  summary: Schemas['InstrumentSummary'],
  extra: Partial<Schemas['InstrumentDetail']> = {},
): Schemas['InstrumentDetail'] {
  return {
    ...summary,
    source: 'amfi',
    series: null,
    listed_on: null,
    cik: null,
    isin_reinvestment: null,
    scheme_type: 'Open Ended',
    aliases: [],
    rule: {
      asset_class: summary.asset_class,
      allocation: [{ bucket: 'equity', percent: '100' }],
      exposure: summary.exposure,
    },
    override: null,
    created_at: '2026-10-24T10:00:00Z',
    updated_at: '2026-10-24T10:00:00Z',
    ...extra,
  }
}

export function navSummary(
  extra: Partial<Schemas['NavSummaryOut']> = {},
): Schemas['NavSummaryOut'] {
  return {
    instrument_id: parag.id,
    is_fund: true,
    tracked: true,
    tracked_by_me: true,
    used_by: [],
    coverage: { first: '2013-05-28', last: '2026-10-23', count: 3298 },
    stats: {
      first: { date: '2013-05-28', nav: '9.9992' },
      latest: { date: '2026-10-23', nav: '88.9695' },
      change_1d_pct: '-0.49',
      change_1y_pct: '11.21',
      change_since_first_pct: '789.76',
      cagr_pct: '17.23',
      high_52w: { date: '2026-06-01', nav: '95' },
      low_52w: { date: '2025-11-03', nav: '72.5' },
    },
    ...extra,
  }
}

export const recentNavs: Schemas['NavPointOut'][] = [
  { date: '2026-10-21', nav: '89.9443' },
  { date: '2026-10-22', nav: '89.4088' },
  { date: '2026-10-23', nav: '88.9695' },
]

export function syncRun(extra: Partial<Schemas['SyncRunOut']> = {}): Schemas['SyncRunOut'] {
  return {
    id: 1,
    status: 'ok',
    started_at: '2026-10-25T04:00:00Z',
    finished_at: '2026-10-25T04:00:03Z',
    funds: 2,
    added: 26,
    corrected: 0,
    failed: 0,
    results: [
      {
        instrument_id: parag.id,
        name: parag.name,
        status: 'ok',
        added: 13,
        corrected: 0,
        last_date: '2026-10-23',
        message: null,
      },
    ],
    ...extra,
  }
}

export const nifty: Schemas['InstrumentSummary'] = {
  ...parag,
  id: 9,
  name: 'UTI Nifty 50 Index Fund',
  amfi_code: '120716',
  isin: 'INF789F01XA0',
  fund_house: 'UTI Mutual Fund',
  fund_category: 'Other Scheme - Index Funds',
  variants: [],
}

export function fundRef(summary: Schemas['InstrumentSummary']): Schemas['FundRef'] {
  const { id, name, amfi_code, fund_house, fund_category, plan, option, is_active } = summary
  return { id, name, amfi_code, fund_house, fund_category, plan, option, is_active }
}

export function bucket(extra: Partial<Schemas['BucketOut']> = {}): Schemas['BucketOut'] {
  const coverage = { first: '2013-05-28', last: '2026-10-23', count: 3298 }
  return {
    id: 1,
    name: 'Core',
    description: null,
    rebalance: 'yearly',
    benchmark: { fund: fundRef(nifty), coverage },
    funds: [
      { fund: fundRef(parag), weight: '60', coverage },
      { fund: fundRef(nifty), weight: '40', coverage },
    ],
    common_start: '2013-05-28',
    created_at: '2026-10-25T04:00:00Z',
    updated_at: '2026-10-25T04:00:00Z',
    ...extra,
  }
}
