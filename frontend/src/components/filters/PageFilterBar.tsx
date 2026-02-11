import type { ReactNode } from 'react'
import { SelectFilter } from './SelectFilter'
import { useFilterOptions } from '../../api/hooks/useFilters'
import type { PageFilterState } from '../../hooks/usePageFilters'

type PageFilterBarProps = Omit<PageFilterState, 'params'> & {
  /** Conteúdo extra renderizado ao lado dos filtros */
  extraActions?: ReactNode
}

/**
 * Barra de filtros para páginas com filtros próprios.
 * Renderiza Ano + Date range + Limpar filtros.
 * Recebe estado local como props — completamente desacoplada do store global.
 */
export function PageFilterBar({
  anos,
  dataInicio,
  dataFim,
  setAnos,
  setDataInicio,
  setDataFim,
  clearAll,
  extraActions,
}: PageFilterBarProps) {
  const { data: options } = useFilterOptions()

  if (!options) return null

  const hasActiveFilters = anos.length > 0 || dataInicio || dataFim

  return (
    <div className="sticky top-14 z-10 flex flex-wrap items-center gap-2 border-b border-gray-200 bg-surface px-3 py-2 sm:gap-3 sm:px-6 sm:py-3">
      <SelectFilter
        label="Ano"
        options={options.anos.map(String)}
        value={anos.map(String)}
        onChange={(v) => setAnos(v.map(Number))}
        showSelectAll
      />

      {extraActions}

      <div className="flex w-full items-center gap-2 sm:ml-auto sm:w-auto">
        <input
          type="date"
          value={dataInicio ?? ''}
          onChange={(e) => setDataInicio(e.target.value || null)}
          className="min-w-0 flex-1 rounded border border-gray-300 px-2 py-1 text-xs focus:border-primary focus:outline-none sm:flex-none"
          placeholder="Data início"
        />
        <span className="text-xs text-gray-400">a</span>
        <input
          type="date"
          value={dataFim ?? ''}
          onChange={(e) => setDataFim(e.target.value || null)}
          className="min-w-0 flex-1 rounded border border-gray-300 px-2 py-1 text-xs focus:border-primary focus:outline-none sm:flex-none"
          placeholder="Data fim"
        />
      </div>

      {hasActiveFilters && (
        <button
          onClick={clearAll}
          className="rounded px-3 py-1 text-xs text-gray-500 hover:bg-gray-100 transition-colors"
        >
          Limpar filtros
        </button>
      )}
    </div>
  )
}
