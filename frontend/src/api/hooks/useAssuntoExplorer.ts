import { useQuery } from '@tanstack/react-query'
import api, { buildQueryString } from '../client'
import { useFilterParams } from './useFilterParams'
import type { AssuntoGroupCount, AssuntoResumo, AssuntoNode, PaginatedResponse, PaginationParams } from '../../types'

/** Drill-down hierárquico na árvore de assuntos. */
export function useAssuntoDrillDown(
  assuntoPai: number | null,
  limit = 50,
) {
  const params = useFilterParams()
  return useQuery<AssuntoGroupCount[]>({
    queryKey: ['assunto-drill-down', assuntoPai, limit, params],
    queryFn: async () => {
      const qp: Record<string, string | string[] | number | undefined | null> = {
        ...params,
        limit,
      }
      if (assuntoPai !== null) qp.assunto_pai = assuntoPai
      const { data } = await api.get(`/assuntos/drill-down${buildQueryString(qp)}`)
      return data
    },
  })
}

/** Resumo completo de um nó de assunto (KPIs, top chefias, timeline). */
export function useAssuntoResumo(codigo: number | null) {
  const params = useFilterParams()
  return useQuery<AssuntoResumo>({
    queryKey: ['assunto-resumo', codigo, params],
    queryFn: async () => {
      const { data } = await api.get(
        `/assuntos/resumo${buildQueryString({ ...params, codigo: codigo! })}`
      )
      return data
    },
    enabled: !!codigo,
  })
}

/** Busca textual de assuntos por nome (autocomplete). */
export function useAssuntoSearch(query: string) {
  return useQuery<AssuntoNode[]>({
    queryKey: ['assunto-search', query],
    queryFn: async () => {
      const { data } = await api.get(
        `/assuntos/search${buildQueryString({ q: query })}`
      )
      return data
    },
    enabled: query.length >= 2,
    staleTime: 5 * 60 * 1000, // 5 minutos
  })
}

/** Lista paginada de processos filtrados por assunto (com descendentes). */
export function useAssuntoLista(
  assuntoCodigos: number[],
  pagination: PaginationParams,
) {
  const params = useFilterParams()
  return useQuery<PaginatedResponse>({
    queryKey: ['assunto-lista', params, assuntoCodigos, pagination],
    queryFn: async () => {
      const qp: Record<string, string | string[] | number | undefined | null> = {
        ...params,
        ...pagination,
      }
      if (assuntoCodigos.length > 0) {
        qp.assunto = assuntoCodigos.map(String).join(',')
      }
      const { data } = await api.get(
        `/assuntos/lista${buildQueryString(qp)}`
      )
      return data
    },
    enabled: assuntoCodigos.length > 0,
  })
}

/** Retorna o caminho hierárquico completo até o assunto (da raiz até ele). */
export function useAssuntoPath(codigo: number | null) {
  return useQuery<AssuntoNode[]>({
    queryKey: ['assunto-path', codigo],
    queryFn: async () => {
      const { data } = await api.get(`/assuntos/path/${codigo}`)
      return data
    },
    enabled: !!codigo,
    staleTime: 60 * 60 * 1000, // 1 hora (paths são estáveis)
  })
}
