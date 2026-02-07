import { useQuery } from '@tanstack/react-query'
import api from '../client'
import type { FilterOptions } from '../../types'

export function useFilterOptions() {
  return useQuery<FilterOptions>({
    queryKey: ['filter-options'],
    queryFn: async () => {
      const { data } = await api.get('/filters/options')
      return data
    },
    staleTime: 60 * 60 * 1000,
  })
}

/** Lista de assessores (usuários que não são procuradores). */
export function useAssessores() {
  return useQuery<string[]>({
    queryKey: ['assessores'],
    queryFn: async () => {
      const { data } = await api.get('/filters/assessores')
      return data
    },
    staleTime: 60 * 60 * 1000,
  })
}
