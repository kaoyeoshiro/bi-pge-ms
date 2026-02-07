import { useMemo } from 'react'
import { useFilterStore } from '../../stores/useFilterStore'

/**
 * Extrai os valores primitivos do store de filtros e computa
 * os query params de forma estável (sem criar novo objeto a cada render).
 */
export function useFilterParams() {
  const anos = useFilterStore((s) => s.anos)
  const mes = useFilterStore((s) => s.mes)
  const dataInicio = useFilterStore((s) => s.dataInicio)
  const dataFim = useFilterStore((s) => s.dataFim)
  const chefias = useFilterStore((s) => s.chefias)
  const procuradores = useFilterStore((s) => s.procuradores)
  const categorias = useFilterStore((s) => s.categorias)
  const areas = useFilterStore((s) => s.areas)

  return useMemo(() => {
    const params: Record<string, string | string[]> = {}
    if (anos.length) params.anos = anos.map(String)
    if (mes) params.mes = String(mes)
    if (dataInicio) params.data_inicio = dataInicio
    if (dataFim) params.data_fim = dataFim
    if (chefias.length) params.chefia = chefias
    if (procuradores.length) params.procurador = procuradores
    if (categorias.length) params.categoria = categorias
    if (areas.length) params.area = areas
    return params
  }, [anos, mes, dataInicio, dataFim, chefias, procuradores, categorias, areas])
}
