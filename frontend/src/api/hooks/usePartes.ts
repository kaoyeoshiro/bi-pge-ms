import { useQuery } from '@tanstack/react-query'
import api, { buildQueryString } from '../client'
import type {
  PaginatedResponse,
  PaginationParams,
  ParteNormalizada,
  ParteProcessoItem,
  PartesKPIs,
} from '../../types'

export function usePartesKPIs() {
  return useQuery<PartesKPIs>({
    queryKey: ['partes-kpis'],
    queryFn: async () => {
      const { data } = await api.get('/partes/kpis')
      return data
    },
    staleTime: 5 * 60 * 1000,
  })
}

export function usePartesRanking(
  role: string | null,
  pagination: PaginationParams,
) {
  return useQuery<PaginatedResponse<ParteNormalizada>>({
    queryKey: ['partes-ranking', role, pagination],
    queryFn: async () => {
      const params: Record<string, string | number | undefined> = {
        page: pagination.page,
        page_size: pagination.page_size,
        sort_by: pagination.sort_by,
        sort_order: pagination.sort_order,
        search: pagination.search || undefined,
      }
      if (role) params.role = role
      const { data } = await api.get(`/partes/ranking${buildQueryString(params)}`)
      return data
    },
  })
}

export function useParteDetalhe(parteId: number | null) {
  return useQuery<ParteNormalizada>({
    queryKey: ['parte-detalhe', parteId],
    queryFn: async () => {
      const { data } = await api.get(`/partes/${parteId}`)
      return data
    },
    enabled: parteId !== null,
  })
}

export function useParteProcessos(
  parteId: number | null,
  page: number = 1,
  pageSize: number = 10,
) {
  return useQuery<PaginatedResponse<ParteProcessoItem>>({
    queryKey: ['parte-processos', parteId, page, pageSize],
    queryFn: async () => {
      const { data } = await api.get(
        `/partes/${parteId}/processos${buildQueryString({ page, page_size: pageSize })}`,
      )
      return data
    },
    enabled: parteId !== null,
  })
}
