import { useQuery } from '@tanstack/react-query'
import api, { buildQueryString } from '../client'
import { useFilterParams } from './useFilterParams'
import type { PaginatedResponse, PaginationParams, TableSchema } from '../../types'

export function useTableSchema(table: string) {
  return useQuery<TableSchema>({
    queryKey: ['explorer-schema', table],
    queryFn: async () => {
      const { data } = await api.get(`/explorer/${table}/schema`)
      return data
    },
    staleTime: 24 * 60 * 60 * 1000,
    enabled: !!table,
  })
}

export function useTableData(table: string, pagination: PaginationParams) {
  const params = useFilterParams()
  return useQuery<PaginatedResponse>({
    queryKey: ['explorer-data', table, params, pagination],
    queryFn: async () => {
      const { data } = await api.get(
        `/explorer/${table}/data${buildQueryString({ ...params, ...pagination })}`
      )
      return data
    },
    enabled: !!table,
  })
}

export function useDistinctValues(table: string, column: string) {
  return useQuery<string[]>({
    queryKey: ['explorer-distinct', table, column],
    queryFn: async () => {
      const { data } = await api.get(`/explorer/${table}/distinct/${column}`)
      return data
    },
    enabled: !!table && !!column,
    staleTime: 60 * 60 * 1000,
  })
}
