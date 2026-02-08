import { createContext, useContext, useMemo } from 'react'
import type { ReactNode } from 'react'
import { useFilterStore } from '../../stores/useFilterStore'

export type FilterParams = Record<string, string | string[]>

/**
 * Contexto que permite páginas com filtros próprios sobrescreverem
 * o retorno de useFilterParams(). Quando presente, o hook retorna
 * os params do provider ao invés do store global.
 */
const FilterParamsContext = createContext<FilterParams | undefined>(undefined)

/**
 * Provider que isola o contexto de filtros para uma subárvore.
 * Páginas que possuem filtros próprios (Perfil, Comparativos, Explorer)
 * devem envolver seu conteúdo com este provider.
 */
export function FilterParamsProvider({
  value,
  children,
}: {
  value: FilterParams
  children: ReactNode
}) {
  return (
    <FilterParamsContext.Provider value={value}>
      {children}
    </FilterParamsContext.Provider>
  )
}

/**
 * Extrai os valores primitivos do store de filtros e computa
 * os query params de forma estável (sem criar novo objeto a cada render).
 *
 * Quando envolto por um FilterParamsProvider, retorna os params
 * do provider (filtros locais da página) ao invés do store global.
 */
export function useFilterParams() {
  const override = useContext(FilterParamsContext)

  const anos = useFilterStore((s) => s.anos)
  const mes = useFilterStore((s) => s.mes)
  const dataInicio = useFilterStore((s) => s.dataInicio)
  const dataFim = useFilterStore((s) => s.dataFim)
  const chefias = useFilterStore((s) => s.chefias)
  const procuradores = useFilterStore((s) => s.procuradores)
  const categorias = useFilterStore((s) => s.categorias)
  const areas = useFilterStore((s) => s.areas)

  return useMemo(() => {
    // Se um FilterParamsProvider está presente, usar seus params
    if (override !== undefined) return override

    // Caso contrário, usar o store global
    const params: FilterParams = {}
    if (anos.length) params.anos = anos.map(String)
    if (mes) params.mes = String(mes)
    if (dataInicio) params.data_inicio = dataInicio
    if (dataFim) params.data_fim = dataFim
    if (chefias.length) params.chefia = chefias
    if (procuradores.length) params.procurador = procuradores
    if (categorias.length) params.categoria = categorias
    if (areas.length) params.area = areas
    return params
  }, [override, anos, mes, dataInicio, dataFim, chefias, procuradores, categorias, areas])
}
