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

export function useInstrumentSearch(q: string) {
  return useQuery({
    queryKey: ['instrument-search', q],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/instruments/search', {
        params: { query: { q, limit: 12 } },
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
