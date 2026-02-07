import { useQuery } from '@tanstack/react-query'
import api, { buildQueryString } from '../client'
import { useFilterParams } from './useFilterParams'
import type { GroupCount, KPIValue, PaginatedResponse, PaginationParams, TimelineSeries } from '../../types'

export function useProcessosKPIs() {
  const params = useFilterParams()
  return useQuery<KPIValue[]>({
    queryKey: ['processos-kpis', params],
    queryFn: async () => {
      const { data } = await api.get(`/processos/kpis${buildQueryString(params)}`)
      return data
    },
  })
}

export function useProcessosTimeline() {
  const params = useFilterParams()
  return useQuery<TimelineSeries[]>({
    queryKey: ['processos-timeline', params],
    queryFn: async () => {
      const { data } = await api.get(`/processos/timeline${buildQueryString(params)}`)
      return data
    },
  })
}

export function useProcessosPorGrupo(grupo: string, limit = 500) {
  const params = useFilterParams()
  return useQuery<GroupCount[]>({
    queryKey: [`processos-por-${grupo}`, params, limit],
    queryFn: async () => {
      const { data } = await api.get(
        `/processos/por-${grupo}${buildQueryString({ ...params, limit })}`
      )
      return data
    },
  })
}

export function useProcessosLista(pagination: PaginationParams) {
  const params = useFilterParams()
  return useQuery<PaginatedResponse>({
    queryKey: ['processos-lista', params, pagination],
    queryFn: async () => {
      const { data } = await api.get(
        `/processos/lista${buildQueryString({ ...params, ...pagination })}`
      )
      return data
    },
  })
}
