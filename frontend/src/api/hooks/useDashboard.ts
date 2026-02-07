import { useQuery } from '@tanstack/react-query'
import api, { buildQueryString } from '../client'
import { useFilterParams } from './useFilterParams'
import type { GroupCount, KPIValue, TimelineSeries } from '../../types'

export function useDashboardKPIs() {
  const params = useFilterParams()
  return useQuery<KPIValue[]>({
    queryKey: ['dashboard-kpis', params],
    queryFn: async () => {
      const { data } = await api.get(`/dashboard/kpis${buildQueryString(params)}`)
      return data
    },
  })
}

export function useDashboardTimeline() {
  const params = useFilterParams()
  return useQuery<TimelineSeries[]>({
    queryKey: ['dashboard-timeline', params],
    queryFn: async () => {
      const { data } = await api.get(`/dashboard/timeline${buildQueryString(params)}`)
      return data
    },
  })
}

export function useTopChefias(metrica = 'pecas_elaboradas', limit = 500) {
  const params = useFilterParams()
  return useQuery<GroupCount[]>({
    queryKey: ['dashboard-top-chefias', params, metrica, limit],
    queryFn: async () => {
      const { data } = await api.get(
        `/dashboard/top-chefias${buildQueryString({ ...params, limit, metrica })}`
      )
      return data
    },
  })
}

export function useTopProcuradores(metrica = 'pecas_elaboradas', limit = 500) {
  const params = useFilterParams()
  return useQuery<GroupCount[]>({
    queryKey: ['dashboard-top-procuradores', params, metrica, limit],
    queryFn: async () => {
      const { data } = await api.get(
        `/dashboard/top-procuradores${buildQueryString({ ...params, limit, metrica })}`
      )
      return data
    },
  })
}
