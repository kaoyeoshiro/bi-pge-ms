import { useQuery } from '@tanstack/react-query'
import api, { buildQueryString } from '../client'
import { useFilterParams } from './useFilterParams'
import type { GroupCount, KPIValue, PaginatedResponse, PaginationParams, TimelineSeries } from '../../types'

export function useProducaoKPIs() {
  const params = useFilterParams()
  return useQuery<KPIValue[]>({
    queryKey: ['producao-kpis', params],
    queryFn: async () => {
      const { data } = await api.get(`/producao/kpis${buildQueryString(params)}`)
      return data
    },
  })
}

export function useProducaoTimeline() {
  const params = useFilterParams()
  return useQuery<TimelineSeries[]>({
    queryKey: ['producao-timeline', params],
    queryFn: async () => {
      const { data } = await api.get(`/producao/timeline${buildQueryString(params)}`)
      return data
    },
  })
}

export function useProducaoPorGrupo(grupo: string, tipo = 'elaboradas', limit = 15) {
  const params = useFilterParams()
  return useQuery<GroupCount[]>({
    queryKey: [`producao-por-${grupo}`, params, tipo, limit],
    queryFn: async () => {
      const { data } = await api.get(
        `/producao/por-${grupo}${buildQueryString({ ...params, tipo, limit })}`
      )
      return data
    },
  })
}

export function useProducaoLista(
  tipo: 'elaboradas' | 'finalizadas',
  pagination: PaginationParams
) {
  const params = useFilterParams()
  return useQuery<PaginatedResponse>({
    queryKey: [`producao-${tipo}`, params, pagination],
    queryFn: async () => {
      const { data } = await api.get(
        `/producao/${tipo}${buildQueryString({ ...params, ...pagination })}`
      )
      return data
    },
  })
}
