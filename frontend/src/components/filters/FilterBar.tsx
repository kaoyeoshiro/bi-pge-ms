import { useFilterStore } from '../../stores/useFilterStore'
import { useFilterOptions } from '../../api/hooks/useFilters'
import { SelectFilter } from './SelectFilter'
import { ValorFaixaFilter } from './ValorFaixaFilter'

interface FilterBarProps {
  /** Exibe o filtro de faixa de valor da causa. */
  showValorFaixa?: boolean
}

export function FilterBar({ showValorFaixa = false }: FilterBarProps) {
  const { data: options } = useFilterOptions()
  const store = useFilterStore()

  if (!options) return null

  return (
    <div className="sticky top-14 z-10 border-b border-gray-200 bg-surface">
      <div className="flex flex-wrap items-center gap-2 px-3 py-2 sm:gap-3 sm:px-6 sm:py-3">
        <SelectFilter
          label="Ano"
          options={options.anos.map(String)}
          value={store.anos.map(String)}
          onChange={(v) => store.setAnos(v.map(Number))}
          showSelectAll
        />
        <SelectFilter
          label="Chefia"
          options={options.chefias}
          value={store.chefias}
          onChange={store.setChefias}
        />
        <SelectFilter
          label="Procurador"
          options={options.procuradores}
          value={store.procuradores}
          onChange={store.setProcuradores}
        />
        <SelectFilter
          label="Categoria"
          options={options.categorias}
          value={store.categorias}
          onChange={store.setCategorias}
        />
        <SelectFilter
          label="Área"
          options={options.areas}
          value={store.areas}
          onChange={store.setAreas}
        />
        <div className="flex w-full items-center gap-2 sm:ml-auto sm:w-auto">
          <input
            type="date"
            value={store.dataInicio ?? ''}
            onChange={(e) => store.setDataInicio(e.target.value || null)}
            className="min-w-0 flex-1 rounded border border-gray-300 px-2 py-1 text-xs focus:border-primary focus:outline-none sm:flex-none"
            placeholder="Data início"
          />
          <span className="text-xs text-gray-400">a</span>
          <input
            type="date"
            value={store.dataFim ?? ''}
            onChange={(e) => store.setDataFim(e.target.value || null)}
            className="min-w-0 flex-1 rounded border border-gray-300 px-2 py-1 text-xs focus:border-primary focus:outline-none sm:flex-none"
            placeholder="Data fim"
          />
        </div>

        <button
          onClick={store.clearAll}
          className="rounded px-3 py-1 text-xs text-gray-500 hover:bg-gray-100 transition-colors"
        >
          Limpar filtros
        </button>
      </div>

      {showValorFaixa && (
        <div className="border-t border-gray-100 px-3 py-1.5 sm:px-6 sm:py-2">
          <ValorFaixaFilter />
        </div>
      )}
    </div>
  )
}
