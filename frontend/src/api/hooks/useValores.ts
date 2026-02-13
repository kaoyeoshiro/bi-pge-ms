import { useQuery } from '@tanstack/react-query'
import api, { buildQueryString } from '../client'
import { useFilterParams } from './useFilterParams'
import type { KPIValue, PaginatedResponse, PaginationParams, TimelineSeries, ValorFaixaItem, ValorGroupItem } from '../../types'

export function useValoresKPIs() {
  const params = useFilterParams()
  return useQuery<KPIValue[]>({
    queryKey: ['valores-kpis', params],
    queryFn: async () => {
      const { data } = await api.get(`/valores/kpis${buildQueryString(params)}`)
      return data
    },
  })
}

export function useValoresDistribuicao() {
  const params = useFilterParams()
  return useQuery<ValorFaixaItem[]>({
    queryKey: ['valores-distribuicao', params],
    queryFn: async () => {
      const { data } = await api.get(`/valores/distribuicao${buildQueryString(params)}`)
      return data
    },
  })
}

export function useValoresPorGrupo(grupo: string, metrica: string, limit = 15) {
  const params = useFilterParams()
  return useQuery<ValorGroupItem[]>({
    queryKey: ['valores-por-grupo', params, grupo, metrica, limit],
    queryFn: async () => {
      const { data } = await api.get(
        `/valores/por-grupo${buildQueryString({ ...params, grupo, metrica, limit })}`
      )
      return data
    },
  })
}

export function useValoresTimeline() {
  const params = useFilterParams()
  return useQuery<TimelineSeries[]>({
    queryKey: ['valores-timeline', params],
    queryFn: async () => {
      const { data } = await api.get(`/valores/timeline${buildQueryString(params)}`)
      return data
    },
  })
}

export function useValoresLista(pagination: PaginationParams) {
  const params = useFilterParams()
  return useQuery<PaginatedResponse>({
    queryKey: ['valores-lista', params, pagination],
    queryFn: async () => {
      const { data } = await api.get(
        `/valores/lista${buildQueryString({ ...params, ...pagination })}`
      )
      return data
    },
  })
}
