import { useQuery } from '@tanstack/react-query'
import api, { buildQueryString } from '../client'
import { useFilterParams } from './useFilterParams'
import type {
  AssuntoGroupCount,
  ChefiaMediasResponse,
  GroupCount,
  KPIValue,
  PaginatedResponse,
  PaginationParams,
  ProcuradorComparativo,
  TimelineSeries,
} from '../../types'

/** KPIs do indivíduo nas 4 tabelas. */
export function usePerfilKPIs(dimensao: string, valor: string | null) {
  const params = useFilterParams()
  return useQuery<KPIValue[]>({
    queryKey: ['perfil-kpis', dimensao, valor, params],
    queryFn: async () => {
      const { data } = await api.get(
        `/perfil/kpis${buildQueryString({ ...params, dimensao, valor: valor! })}`
      )
      return data
    },
    enabled: !!valor,
  })
}

/** Séries temporais mensais do indivíduo. */
export function usePerfilTimeline(dimensao: string, valor: string | null) {
  const params = useFilterParams()
  return useQuery<TimelineSeries[]>({
    queryKey: ['perfil-timeline', dimensao, valor, params],
    queryFn: async () => {
      const { data } = await api.get(
        `/perfil/timeline${buildQueryString({ ...params, dimensao, valor: valor! })}`
      )
      return data
    },
    enabled: !!valor,
  })
}

/** Ranking por categoria de peça do indivíduo. */
export function usePerfilPorCategoria(
  dimensao: string,
  valor: string | null,
  tabela: string | null = 'pecas_elaboradas',
  limit = 15
) {
  const params = useFilterParams()
  return useQuery<GroupCount[]>({
    queryKey: ['perfil-categorias', dimensao, valor, tabela, params, limit],
    queryFn: async () => {
      const { data } = await api.get(
        `/perfil/por-categoria${buildQueryString({
          ...params,
          dimensao,
          valor: valor!,
          tabela: tabela!,
          limit,
        })}`
      )
      return data
    },
    enabled: !!valor && !!tabela,
  })
}

/** Ranking por modelo de peça do indivíduo. */
export function usePerfilPorModelo(
  dimensao: string,
  valor: string | null,
  tabela: string | null = 'pecas_elaboradas',
  limit = 15
) {
  const params = useFilterParams()
  return useQuery<GroupCount[]>({
    queryKey: ['perfil-modelos', dimensao, valor, tabela, params, limit],
    queryFn: async () => {
      const { data } = await api.get(
        `/perfil/por-modelo${buildQueryString({
          ...params,
          dimensao,
          valor: valor!,
          tabela: tabela!,
          limit,
        })}`
      )
      return data
    },
    enabled: !!valor && !!tabela,
  })
}

/** Ranking por procurador: quais procuradores o assessor atendeu. */
export function usePerfilPorProcurador(
  dimensao: string,
  valor: string | null,
  tabela: string | null = 'pecas_elaboradas',
  limit = 15
) {
  const params = useFilterParams()
  return useQuery<GroupCount[]>({
    queryKey: ['perfil-procuradores', dimensao, valor, tabela, params, limit],
    queryFn: async () => {
      const { data } = await api.get(
        `/perfil/por-procurador${buildQueryString({
          ...params,
          dimensao,
          valor: valor!,
          tabela: tabela!,
          limit,
        })}`
      )
      return data
    },
    enabled: !!valor && !!tabela,
  })
}

/** Ranking por assunto com drill-down hierárquico. */
export function usePerfilPorAssunto(
  dimensao: string,
  valor: string | null,
  tabela: string | null = 'processos_novos',
  limit = 15,
  assuntoPai: number | null = null,
) {
  const params = useFilterParams()
  return useQuery<AssuntoGroupCount[]>({
    queryKey: ['perfil-assuntos', dimensao, valor, tabela, params, limit, assuntoPai],
    queryFn: async () => {
      const qp: Record<string, string | string[] | number | undefined | null> = {
        ...params,
        dimensao,
        valor: valor!,
        tabela: tabela!,
        limit,
      }
      if (assuntoPai !== null) qp.assunto_pai = assuntoPai
      const { data } = await api.get(`/perfil/por-assunto${buildQueryString(qp)}`)
      return data
    },
    enabled: !!valor && !!tabela,
  })
}

/** Comparativo entre procuradores de uma chefia. */
export function useComparativoProcuradores(valor: string | null) {
  const params = useFilterParams()
  return useQuery<ProcuradorComparativo[]>({
    queryKey: ['perfil-comparativo-procuradores', valor, params],
    queryFn: async () => {
      const { data } = await api.get(
        `/perfil/comparativo-procuradores${buildQueryString({ ...params, valor: valor! })}`
      )
      return data
    },
    enabled: !!valor,
  })
}

/** Comparativo entre assessores de uma chefia. */
export function useComparativoAssessores(
  chefia: string,
  params: Record<string, string | string[]>
) {
  return useQuery({
    queryKey: ['perfil-comparativo-assessores', chefia, params],
    queryFn: async () => {
      const { data } = await api.get(
        `/perfil/comparativo-assessores${buildQueryString({ ...params, valor: chefia })}`
      )
      return data
    },
    enabled: !!chefia,
  })
}

/** Lista paginada de registros do indivíduo em uma tabela. */
export function usePerfilLista(
  dimensao: string,
  valor: string | null,
  tabela: string,
  pagination: PaginationParams
) {
  const params = useFilterParams()
  return useQuery<PaginatedResponse>({
    queryKey: ['perfil-lista', dimensao, valor, tabela, params, pagination],
    queryFn: async () => {
      const { data } = await api.get(
        `/perfil/lista${buildQueryString({
          ...params,
          dimensao,
          valor: valor!,
          tabela,
          ...pagination,
        })}`
      )
      return data
    },
    enabled: !!valor,
  })
}

/** KPIs com média por unidade temporal para chefia. */
export function useChefiaMedias(
  valor: string | null,
  averageUnit: string,
  procuradorNomes: string[],
  enabled: boolean = true,
) {
  const params = useFilterParams()
  return useQuery<ChefiaMediasResponse>({
    queryKey: ['chefia-medias', valor, averageUnit, procuradorNomes, params],
    queryFn: async () => {
      const { data } = await api.get(
        `/perfil/chefia-medias${buildQueryString({
          ...params,
          valor: valor!,
          average_unit: averageUnit,
          procurador_nomes: procuradorNomes,
        })}`
      )
      return data
    },
    enabled: !!valor && enabled,
  })
}
