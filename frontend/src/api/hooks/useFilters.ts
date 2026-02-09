import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import api from '../client'
import type { AssuntoNode, FilterOptions } from '../../types'

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

/** Árvore hierárquica de assuntos vinculados a processos. */
export function useAssuntosTree() {
  return useQuery<AssuntoNode[]>({
    queryKey: ['assuntos-tree'],
    queryFn: async () => {
      const { data } = await api.get('/filters/assuntos')
      return data
    },
    staleTime: 60 * 60 * 1000,
  })
}

/** Retorna Set de nomes com carga reduzida. */
export function useCargaReduzida() {
  const query = useQuery<string[]>({
    queryKey: ['carga-reduzida'],
    queryFn: async () => {
      const { data } = await api.get('/filters/carga-reduzida')
      return data
    },
    staleTime: 5 * 60 * 1000,
  })

  const crSet = useMemo(
    () => new Set(query.data ?? []),
    [query.data]
  )

  return { ...query, crSet }
}
