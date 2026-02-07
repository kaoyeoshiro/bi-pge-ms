import { useQuery } from '@tanstack/react-query'
import api, { buildQueryString } from '../client'
import { useFilterParams } from './useFilterParams'

export function useCompararChefias(chefias: string[]) {
  const params = useFilterParams()
  return useQuery({
    queryKey: ['comparar-chefias', chefias, params],
    queryFn: async () => {
      const { data } = await api.get(
        `/comparativos/chefias${buildQueryString({ ...params, chefias })}`
      )
      return data
    },
    enabled: chefias.length >= 2,
  })
}

export function useCompararProcuradores(procuradores: string[]) {
  const params = useFilterParams()
  return useQuery({
    queryKey: ['comparar-procuradores', procuradores, params],
    queryFn: async () => {
      const { data } = await api.get(
        `/comparativos/procuradores${buildQueryString({ ...params, procuradores })}`
      )
      return data
    },
    enabled: procuradores.length >= 2,
  })
}

export function useCompararPeriodos(
  p1Inicio: string, p1Fim: string,
  p2Inicio: string, p2Fim: string,
) {
  const params = useFilterParams()
  return useQuery({
    queryKey: ['comparar-periodos', p1Inicio, p1Fim, p2Inicio, p2Fim, params],
    queryFn: async () => {
      const { data } = await api.get(
        `/comparativos/periodos${buildQueryString({
          ...params,
          p1_inicio: p1Inicio,
          p1_fim: p1Fim,
          p2_inicio: p2Inicio,
          p2_fim: p2Fim,
        })}`
      )
      return data
    },
    enabled: !!p1Inicio && !!p1Fim && !!p2Inicio && !!p2Fim,
  })
}
