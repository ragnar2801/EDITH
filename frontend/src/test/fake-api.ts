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
