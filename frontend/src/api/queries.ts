import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { api, type ProblemDetails, type Schemas } from './client'

/** Turn a problem-details body (D-035) into an Error with its human-readable detail. */
function failure(error: ProblemDetails): Error {
  return new Error(error.detail ?? error.title)
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
    ['nav-status', 'nav-summary', 'navs'].map((key) =>
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

/** Track a fund and download its history straight away. */
export function useTrackFund(id: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async () => {
      const tracked = await api.PUT('/api/v1/instruments/{instrument_id}/tracking', {
        params: { path: { instrument_id: id } },
      })
      if (tracked.error) throw failure(tracked.error)
      const { data, error } = await api.POST('/api/v1/navs/sync', {
        body: { instrument_ids: [id] },
      })
      if (error) throw failure(error)
      return data
    },
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

export function useBuckets() {
  return useQuery({
    queryKey: ['buckets'],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/buckets')
      if (error) throw failure(error)
      return data
    },
  })
}

export function useDefaultBenchmark() {
  return useQuery({
    queryKey: ['default-benchmark'],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/buckets/default-benchmark')
      if (error) throw failure(error)
      return data ?? null
    },
    staleTime: Infinity,
  })
}

/** Create a bucket (no `id`) or replace one. Then download NAVs for funds that have none. */
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
        queryClient.invalidateQueries({ queryKey: ['buckets'] }),
        invalidateNavs(queryClient),
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
      Promise.all([
        queryClient.invalidateQueries({ queryKey: ['buckets'] }),
        queryClient.invalidateQueries({ queryKey: ['nav-status'] }),
      ]),
  })
}
