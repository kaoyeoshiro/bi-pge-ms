import { useQuery } from '@tanstack/react-query'
import api, { buildQueryString } from '../client'
import { useFilterParams } from './useFilterParams'
import type { GroupCount, KPIValue, PaginatedResponse, PaginationParams, TimelineSeries } from '../../types'

export function usePendenciasKPIs() {
  const params = useFilterParams()
  return useQuery<KPIValue[]>({
    queryKey: ['pendencias-kpis', params],
    queryFn: async () => {
      const { data } = await api.get(`/pendencias/kpis${buildQueryString(params)}`)
      return data
    },
  })
}

export function usePendenciasTimeline() {
  const params = useFilterParams()
  return useQuery<TimelineSeries[]>({
    queryKey: ['pendencias-timeline', params],
    queryFn: async () => {
      const { data } = await api.get(`/pendencias/timeline${buildQueryString(params)}`)
      return data
    },
  })
}

export function usePendenciasPorGrupo(grupo: string, limit = 500) {
  const params = useFilterParams()
  return useQuery<GroupCount[]>({
    queryKey: [`pendencias-por-${grupo}`, params, limit],
    queryFn: async () => {
      const { data } = await api.get(
        `/pendencias/por-${grupo}${buildQueryString({ ...params, limit })}`
      )
      return data
    },
  })
}

export function usePendenciasPorTipo() {
  const params = useFilterParams()
  return useQuery<Array<{ grupo: string; total: number }>>({
    queryKey: ['pendencias-por-tipo', params],
    queryFn: async () => {
      const { data } = await api.get(`/pendencias/por-tipo${buildQueryString(params)}`)
      return data
    },
  })
}

export function usePendenciasLista(pagination: PaginationParams) {
  const params = useFilterParams()
  return useQuery<PaginatedResponse>({
    queryKey: ['pendencias-lista', params, pagination],
    queryFn: async () => {
      const { data } = await api.get(
        `/pendencias/lista${buildQueryString({ ...params, ...pagination })}`
      )
      return data
    },
  })
}
