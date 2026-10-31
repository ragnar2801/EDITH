import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { api, type ProblemDetails, type Schemas } from './client'

/** Turn a problem-details body into an Error with its human-readable detail, and
 * which fields were wrong when the request didn't validate. */
function failure(error: ProblemDetails): Error {
  const fields = (error.errors ?? []).map(
    (field) => `${field.loc.filter((part) => part !== 'body').join(' › ')}: ${field.msg}`,
  )
  const detail = error.detail ?? error.title
  return new Error(fields.length ? `${detail} ${fields.join('; ')}` : detail)
}

export function useHealth() {
  return useQuery({
    queryKey: ['health'],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/health')
      if (error) throw failure(error)
      return data
    },
    refetchInterval: 30_000,
    retry: false,
  })
}

export function useInstrumentSearch(q: string, kind?: Schemas['InstrumentSummary']['kind']) {
  return useQuery({
    queryKey: ['instrument-search', q, kind ?? 'any'],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/instruments/search', {
        params: { query: { q, limit: 12, ...(kind ? { kind } : {}) } },
      })
      if (error) throw failure(error)
      return data
    },
    enabled: q.length > 0,
    placeholderData: keepPreviousData, // keep showing the last results while typing
    staleTime: 60_000,
  })
}

export function useInstrument(id: number) {
  return useQuery({
    queryKey: ['instrument', id],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/instruments/{instrument_id}', {
        params: { path: { instrument_id: id } },
      })
      if (error) throw failure(error)
      return data
    },
    retry: false,
  })
}

export function useInstrumentSources() {
  return useQuery({
    queryKey: ['instrument-sources'],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/instruments/sources')
      if (error) throw failure(error)
      return data
    },
  })
}

/** Download the instrument lists; blank = every list. */
export function useRefreshInstruments() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (sources?: Schemas['RefreshIn']['sources']) => {
      const { data, error } = await api.POST('/api/v1/instruments/refresh', {
        body: sources ? { sources } : {},
      })
      if (error) throw failure(error)
      return data
    },
    onSettled: () =>
      Promise.all([
        queryClient.invalidateQueries({ queryKey: ['instrument-sources'] }),
        queryClient.invalidateQueries({ queryKey: ['instrument-search'] }),
      ]),
  })
}

export function useSetClassification(id: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (body: Schemas['OverrideIn']) => {
      const { data, error } = await api.PUT('/api/v1/instruments/{instrument_id}/classification', {
        params: { path: { instrument_id: id } },
        body,
      })
      if (error) throw failure(error)
      return data
    },
    onSuccess: (detail) => {
      queryClient.setQueryData(['instrument', id], detail)
      return queryClient.invalidateQueries({ queryKey: ['instrument-search'] })
    },
  })
}

export function useClearClassification(id: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async () => {
      const { data, error } = await api.DELETE(
        '/api/v1/instruments/{instrument_id}/classification',
        { params: { path: { instrument_id: id } } },
      )
      if (error) throw failure(error)
      return data
    },
    onSuccess: (detail) => {
      queryClient.setQueryData(['instrument', id], detail)
      return queryClient.invalidateQueries({ queryKey: ['instrument-search'] })
    },
  })
}

export function useNavStatus() {
  return useQuery({
    queryKey: ['nav-status'],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/navs/status')
      if (error) throw failure(error)
      return data
    },
  })
}

export function useNavSummary(id: number) {
  return useQuery({
    queryKey: ['nav-summary', id],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/instruments/{instrument_id}/nav-summary', {
        params: { path: { instrument_id: id } },
      })
      if (error) throw failure(error)
      return data
    },
    retry: false,
  })
}

/** A fund's NAVs from `start` (a plain date) to the latest, oldest first. */
export function useNavs(id: number, start: string | undefined, enabled = true) {
  return useQuery({
    queryKey: ['navs', id, start ?? 'all'],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/instruments/{instrument_id}/navs', {
        params: { path: { instrument_id: id }, query: start ? { start } : {} },
      })
      if (error) throw failure(error)
      return data
    },
    enabled,
    placeholderData: keepPreviousData,
  })
}

/** NAVs changed: every NAV view and anything computed from NAVs is stale. */
function invalidateNavs(queryClient: ReturnType<typeof useQueryClient>) {
  return Promise.all(
    ['nav-status', 'nav-summary', 'navs', 'portfolio', 'compare'].map((key) =>
      queryClient.invalidateQueries({ queryKey: [key] }),
    ),
  )
}

/** Sync every tracked fund, or only `instrumentIds`. */
export function useSyncNavs() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (instrumentIds?: number[]) => {
      const { data, error } = await api.POST('/api/v1/navs/sync', {
        body: instrumentIds ? { instrument_ids: instrumentIds } : {},
      })
      if (error) throw failure(error)
      return data
    },
    onSettled: () => invalidateNavs(queryClient),
  })
}

async function trackAndSync(id: number) {
  const tracked = await api.PUT('/api/v1/instruments/{instrument_id}/tracking', {
    params: { path: { instrument_id: id } },
  })
  if (tracked.error) throw failure(tracked.error)
  const { data, error } = await api.POST('/api/v1/navs/sync', {
    body: { instrument_ids: [id] },
  })
  if (error) throw failure(error)
  return data
}

/** Track a fund and download its history straight away. */
export function useTrackFund(id: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => trackAndSync(id),
    onSettled: () => invalidateNavs(queryClient),
  })
}

/** The same for any fund, e.g. one added to a backtest's split. */
export function useTrackAnyFund() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: trackAndSync,
    onSettled: () => invalidateNavs(queryClient),
  })
}

export function useUntrackFund(id: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async () => {
      const { data, error } = await api.DELETE('/api/v1/instruments/{instrument_id}/tracking', {
        params: { path: { instrument_id: id } },
      })
      if (error) throw failure(error)
      return data
    },
    onSettled: () => invalidateNavs(queryClient),
  })
}

export type CompareQuery = {
  ids: number[]
  benchmark?: number
  start?: string
  rollingYears: number
}

/** Funds side by side over the dates they share. */
export function useCompareFunds({ ids, benchmark, start, rollingYears }: CompareQuery) {
  return useQuery({
    queryKey: ['compare', 'funds', ids, benchmark ?? 'default', start ?? 'common', rollingYears],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/compare/funds', {
        params: {
          query: {
            ids,
            rolling_years: rollingYears,
            ...(benchmark ? { benchmark_id: benchmark } : {}),
            ...(start ? { start } : {}),
          },
        },
      })
      if (error) throw failure(error)
      return data
    },
    enabled: ids.length > 0,
    placeholderData: keepPreviousData,
  })
}

export function useModels() {
  return useQuery({
    queryKey: ['models'],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/models')
      if (error) throw failure(error)
      return data
    },
  })
}

export function useDefaultBenchmark() {
  return useQuery({
    queryKey: ['default-benchmark'],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/models/default-benchmark')
      if (error) throw failure(error)
      return data ?? null
    },
    staleTime: Infinity,
  })
}

/** Create a model (no `id`) or replace one. Then download NAVs for funds that have none. */
export function useSaveModel() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ id, body }: { id?: number; body: Schemas['ModelIn'] }) => {
      const { data, error } = id
        ? await api.PUT('/api/v1/models/{model_id}', {
            params: { path: { model_id: id } },
            body,
          })
        : await api.POST('/api/v1/models', { body })
      if (error) throw failure(error)
      const missing = [...data.funds, ...(data.benchmark ? [data.benchmark] : [])]
        .filter((member) => member.coverage.count === 0)
        .map((member) => member.fund.id)
      if (missing.length > 0) {
        const sync = await api.POST('/api/v1/navs/sync', { body: { instrument_ids: missing } })
        if (sync.error) throw failure(sync.error)
      }
      return data
    },
    onSettled: () =>
      Promise.all([
        queryClient.invalidateQueries({ queryKey: ['models'] }),
        invalidateNavs(queryClient),
      ]),
  })
}

/** Copy a model's funds, weights, benchmark and rebalance under "<name> copy". */
export function useDuplicateModel() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (id: number) => {
      const { data, error } = await api.POST('/api/v1/models/{model_id}/duplicate', {
        params: { path: { model_id: id } },
      })
      if (error) throw failure(error)
      return data
    },
    onSettled: () =>
      Promise.all([
        queryClient.invalidateQueries({ queryKey: ['models'] }),
        queryClient.invalidateQueries({ queryKey: ['nav-status'] }),
      ]),
  })
}

export function useDeleteModel() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (id: number) => {
      const { error } = await api.DELETE('/api/v1/models/{model_id}', {
        params: { path: { model_id: id } },
      })
      if (error) throw failure(error)
    },
    onSettled: () =>
      Promise.all([
        queryClient.invalidateQueries({ queryKey: ['models'] }),
        queryClient.invalidateQueries({ queryKey: ['nav-status'] }),
        queryClient.invalidateQueries({ queryKey: ['portfolio'] }),
      ]),
  })
}

export type BacktestRun = Schemas['BacktestRunOut']

export function useRunBacktest() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (body: Schemas['BacktestIn']) => {
      const { data, error } = await api.POST('/api/v1/backtests', { body })
      if (error) throw failure(error)
      return data
    },
    onSuccess: (run) => {
      queryClient.setQueryData(['backtest', run.id], run)
      if (run.saved) {
        return queryClient.invalidateQueries({ queryKey: ['saved-backtests', run.model_id] })
      }
    },
  })
}

export function useSavedBacktests(modelId: number | null) {
  return useQuery({
    queryKey: ['saved-backtests', modelId],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/models/{model_id}/backtests', {
        params: { path: { model_id: modelId! } },
      })
      if (error) throw failure(error)
      return data
    },
    enabled: modelId !== null,
  })
}

/** Fetch a stored run (a saved one being loaded). */
export function useLoadBacktest() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (id: number) =>
      queryClient.fetchQuery({
        queryKey: ['backtest', id],
        queryFn: async () => {
          const { data, error } = await api.GET('/api/v1/backtests/{run_id}', {
            params: { path: { run_id: id } },
          })
          if (error) throw failure(error)
          return data
        },
      }),
  })
}

export function useSaveBacktest() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ id, name }: { id: number; name: string }) => {
      const { data, error } = await api.PATCH('/api/v1/backtests/{run_id}', {
        params: { path: { run_id: id } },
        body: { saved: true, name: name || null },
      })
      if (error) throw failure(error)
      return data
    },
    onSuccess: (run) =>
      queryClient.invalidateQueries({ queryKey: ['saved-backtests', run.model_id] }),
  })
}

export function useDeleteBacktest() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ id }: { id: number; modelId: number }) => {
      const { error } = await api.DELETE('/api/v1/backtests/{run_id}', {
        params: { path: { run_id: id } },
      })
      if (error) throw failure(error)
    },
    onSuccess: (_, { modelId }) =>
      queryClient.invalidateQueries({ queryKey: ['saved-backtests', modelId] }),
  })
}

/** Figures for a window of a stored run; `null` window = nothing to ask. */
export function useBacktestInterval(
  runId: number | undefined,
  window: { start: string; end: string } | null,
) {
  return useQuery({
    queryKey: ['backtest-interval', runId, window?.start, window?.end],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/backtests/{run_id}/interval', {
        params: { path: { run_id: runId! }, query: window! },
      })
      if (error) throw failure(error)
      return data
    },
    enabled: runId !== undefined && window !== null,
    placeholderData: keepPreviousData,
  })
}

export type Optimised = Schemas['OptimiseOut']

/** Every split of a model's funds, ranked. Nothing is stored. */
export function useOptimise() {
  return useMutation({
    mutationFn: async (body: Schemas['OptimiseIn']) => {
      const { data, error } = await api.POST('/api/v1/backtests/optimise', { body })
      if (error) throw failure(error)
      return data
    },
  })
}

/** A run less an earlier one; `null` = nothing to compare with. */
export function useCompareBacktests(runId: number, against: number | null) {
  return useQuery({
    queryKey: ['backtest-compare', runId, against],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/backtests/{run_id}/compare', {
        params: { path: { run_id: runId }, query: { against: against! } },
      })
      if (error) throw failure(error)
      return data
    },
    enabled: against !== null,
  })
}

export type Holding = Schemas['HoldingOut']
export type Lot = Schemas['LotOut']

/** Funds held with real money, or in one bucket. */
export function useHoldings(bucket?: number) {
  return useQuery({
    queryKey: ['holdings', bucket ?? 'all'],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/holdings', {
        params: { query: bucket === undefined ? {} : { bucket_id: bucket } },
      })
      if (error) throw failure(error)
      return data
    },
  })
}

export function useHolding(id: number) {
  return useQuery({
    queryKey: ['holding', id],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/holdings/{instrument_id}', {
        params: { path: { instrument_id: id } },
      })
      if (error) throw failure(error)
      return data
    },
    retry: false,
  })
}

/** A fund with no NAVs yet: track it and download its history, so a blank NAV can be looked
 * up and SIP instalments can be added. */
async function ensureNavs(holding: Holding) {
  if (holding.coverage.count > 0) return
  const id = holding.fund.id
  const tracked = await api.PUT('/api/v1/instruments/{instrument_id}/tracking', {
    params: { path: { instrument_id: id } },
  })
  if (tracked.error) throw failure(tracked.error)
  const sync = await api.POST('/api/v1/navs/sync', { body: { instrument_ids: [id] } })
  if (sync.error) throw failure(sync.error)
}

/** Every change to a holding answers with the fund's new holding (or nothing, for deletes). */
function useHoldingChange<T>(
  instrumentId: number,
  change: (body: T) => Promise<{ data?: Holding; error?: ProblemDetails }>,
) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (body: T) => {
      const { data, error } = await change(body)
      if (error) throw failure(error)
      return data
    },
    onSettled: () =>
      Promise.all([
        queryClient.invalidateQueries({ queryKey: ['holding', instrumentId] }),
        queryClient.invalidateQueries({ queryKey: ['holdings'] }),
        invalidateNavs(queryClient),
      ]),
  })
}

export function useAddLumpSum(holding: Holding) {
  return useHoldingChange(
    holding.fund.id,
    async (body: Omit<Schemas['LumpSumIn'], 'instrument_id'>) => {
      await ensureNavs(holding)
      return api.POST('/api/v1/lots', { body: { ...body, instrument_id: holding.fund.id } })
    },
  )
}

export function useUpdateLot(instrumentId: number) {
  return useHoldingChange(
    instrumentId,
    ({ id, body }: { id: number; body: Schemas['LotEditIn'] }) =>
      api.PUT('/api/v1/lots/{lot_id}', { params: { path: { lot_id: id } }, body }),
  )
}

export function useDeleteLot(instrumentId: number) {
  return useHoldingChange(instrumentId, (id: number) =>
    api.DELETE('/api/v1/lots/{lot_id}', { params: { path: { lot_id: id } } }),
  )
}

/** Start a SIP (no `id`) or change one. */
export function useSaveSip(holding: Holding) {
  return useHoldingChange(
    holding.fund.id,
    async ({ id, body }: { id?: number; body: Schemas['SipEditIn'] }) => {
      if (id) return api.PUT('/api/v1/sips/{sip_id}', { params: { path: { sip_id: id } }, body })
      await ensureNavs(holding)
      return api.POST('/api/v1/sips', { body: { ...body, instrument_id: holding.fund.id } })
    },
  )
}

export function useDeleteSip(instrumentId: number) {
  return useHoldingChange(instrumentId, (id: number) =>
    api.DELETE('/api/v1/sips/{sip_id}', { params: { path: { sip_id: id } } }),
  )
}

export function useSell(instrumentId: number) {
  return useHoldingChange(instrumentId, (body: Schemas['SaleIn']) =>
    api.POST('/api/v1/sales', { body }),
  )
}

export function useDeleteSale(instrumentId: number) {
  return useHoldingChange(instrumentId, (id: number) =>
    api.DELETE('/api/v1/sales/{sale_id}', { params: { path: { sale_id: id } } }),
  )
}

export type Cash = Schemas['CashOut']
export type CashAccount = Schemas['AccountOut']
export type PlanSettings = Schemas['SettingsOut']
export type CashPlan = Schemas['PlanOut']

export function useCash() {
  return useQuery({
    queryKey: ['cash'],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/cash')
      if (error) throw failure(error)
      return data
    },
  })
}

/** Cash and settings feed the plan, so every change refreshes all three. */
function invalidateCash(queryClient: ReturnType<typeof useQueryClient>) {
  return Promise.all([
    queryClient.invalidateQueries({ queryKey: ['cash'] }),
    queryClient.invalidateQueries({ queryKey: ['plan-settings'] }),
    queryClient.invalidateQueries({ queryKey: ['plan'] }),
    queryClient.invalidateQueries({ queryKey: ['portfolio'] }),
  ])
}

/** Add an account (no `id`) or change one. */
export function useSaveCashAccount() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ id, body }: { id?: number; body: Schemas['AccountIn'] }) => {
      const { data, error } = id
        ? await api.PUT('/api/v1/cash/accounts/{account_id}', {
            params: { path: { account_id: id } },
            body,
          })
        : await api.POST('/api/v1/cash/accounts', { body })
      if (error) throw failure(error)
      return data
    },
    onSuccess: () => invalidateCash(queryClient),
  })
}

export function useDeleteCashAccount() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (id: number) => {
      const { error } = await api.DELETE('/api/v1/cash/accounts/{account_id}', {
        params: { path: { account_id: id } },
      })
      if (error) throw failure(error)
    },
    onSuccess: () => invalidateCash(queryClient),
  })
}

export function usePlanSettings() {
  return useQuery({
    queryKey: ['plan-settings'],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/plan/settings')
      if (error) throw failure(error)
      return data
    },
  })
}

export type Bucket = Schemas['BucketOut']

/** Every bucket with what it holds. Under 'portfolio': whatever changes the portfolio
 * changes these figures too. */
export function useBuckets() {
  return useQuery({
    queryKey: ['portfolio', 'buckets'],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/buckets')
      if (error) throw failure(error)
      return data
    },
  })
}

/** Make a bucket (no `id`) or change one. */
export function useSaveBucket() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ id, body }: { id?: number; body: Schemas['BucketIn'] }) => {
      const { data, error } = id
        ? await api.PUT('/api/v1/buckets/{bucket_id}', {
            params: { path: { bucket_id: id } },
            body,
          })
        : await api.POST('/api/v1/buckets', { body })
      if (error) throw failure(error)
      return data
    },
    onSettled: () =>
      Promise.all([
        queryClient.invalidateQueries({ queryKey: ['portfolio'] }),
        queryClient.invalidateQueries({ queryKey: ['plan'] }),
        queryClient.invalidateQueries({ queryKey: ['holding'] }),
      ]),
  })
}

export function useDeleteBucket() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (id: number) => {
      const { error } = await api.DELETE('/api/v1/buckets/{bucket_id}', {
        params: { path: { bucket_id: id } },
      })
      if (error) throw failure(error)
    },
    onSettled: () =>
      Promise.all(
        ['portfolio', 'plan', 'holding', 'holdings'].map((key) =>
          queryClient.invalidateQueries({ queryKey: [key] }),
        ),
      ),
  })
}

export function useSavePlanSettings() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (body: Schemas['SettingsIn']) => {
      const { data, error } = await api.PUT('/api/v1/plan/settings', { body })
      if (error) throw failure(error)
      return data
    },
    onSuccess: () => invalidateCash(queryClient),
  })
}

/** A bucket's plan for `amount` ('' = all deployable cash); nothing is asked until it's not
 * null. */
export function useCashPlan(bucketId: number, amount: string | null) {
  return useQuery({
    queryKey: ['plan', bucketId, amount],
    queryFn: async () => {
      const { data, error } = await api.POST('/api/v1/plan', {
        body: amount ? { bucket_id: bucketId, amount } : { bucket_id: bucketId },
      })
      if (error) throw failure(error)
      return data
    },
    enabled: amount !== null,
    retry: false,
  })
}

/** Buy a paper bucket's plan for `amount` at each fund's latest NAV. */
export function useBuyOnPaper() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (body: Schemas['PaperBuyIn']) => {
      const { data, error } = await api.POST('/api/v1/plan/paper', { body })
      if (error) throw failure(error)
      return data
    },
    onSettled: () =>
      Promise.all(
        ['portfolio', 'plan', 'holding', 'nav-status'].map((key) =>
          queryClient.invalidateQueries({ queryKey: [key] }),
        ),
      ),
  })
}

export type Portfolio = Schemas['PortfolioOut']
export type FundPosition = Schemas['FundPositionOut']

export type PortfolioHistory = Schemas['HistoryOut']

/** Value, P&L, XIRR, allocation and drift of real money, or of one bucket; all worked out by
 * the backend. */
export function usePortfolio({
  enabled = true,
  bucket,
}: { enabled?: boolean; bucket?: number } = {}) {
  return useQuery({
    queryKey: ['portfolio', 'view', bucket ?? 'all'],
    enabled,
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/portfolio', {
        params: { query: bucket === undefined ? {} : { bucket_id: bucket } },
      })
      if (error) throw failure(error)
      return data
    },
  })
}

/** Value, invested and the benchmark over time from `start`, with the range's gain. */
export function usePortfolioHistory(start: string | undefined, enabled = true, bucket?: number) {
  return useQuery({
    // Under 'portfolio', so every change that refreshes the portfolio refreshes this too.
    queryKey: ['portfolio', 'history', bucket ?? 'all', start ?? 'all'],
    enabled,
    placeholderData: keepPreviousData,
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/portfolio/history', {
        params: {
          query: {
            ...(start ? { start } : {}),
            ...(bucket === undefined ? {} : { bucket_id: bucket }),
          },
        },
      })
      if (error) throw failure(error)
      return data
    },
  })
}

/** Where FM's phone sends its lots and the last import. Imports arrive in the background. */
export function useFmStatus() {
  return useQuery({
    queryKey: ['fm'],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/fm')
      if (error) throw failure(error)
      return data
    },
    refetchInterval: 30_000,
  })
}
