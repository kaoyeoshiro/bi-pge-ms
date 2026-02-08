import { useState, useMemo } from 'react'
import type { FilterParams } from '../api/hooks/useFilterParams'

/**
 * Estado e setters dos filtros locais de uma página.
 * Usado por páginas que possuem filtros próprios (Perfil, Explorer).
 */
export interface PageFilterState {
  anos: number[]
  dataInicio: string | null
  dataFim: string | null
  setAnos: (anos: number[]) => void
  setDataInicio: (data: string | null) => void
  setDataFim: (data: string | null) => void
  clearAll: () => void
  /** Query params computados, prontos para uso no FilterParamsProvider. */
  params: FilterParams
}

/**
 * Hook que gerencia estado de filtros local por página.
 * Completamente isolado do store global de filtros.
 * Retorna state, setters e params computados para o FilterParamsProvider.
 */
export function usePageFilters(): PageFilterState {
  const [anos, setAnos] = useState<number[]>([])
  const [dataInicio, setDataInicio] = useState<string | null>(null)
  const [dataFim, setDataFim] = useState<string | null>(null)

  const clearAll = () => {
    setAnos([])
    setDataInicio(null)
    setDataFim(null)
  }

  const params = useMemo(() => {
    const p: FilterParams = {}
    if (anos.length) p.anos = anos.map(String)
    if (dataInicio) p.data_inicio = dataInicio
    if (dataFim) p.data_fim = dataFim
    return p
  }, [anos, dataInicio, dataFim])

  return { anos, dataInicio, dataFim, setAnos, setDataInicio, setDataFim, clearAll, params }
}
