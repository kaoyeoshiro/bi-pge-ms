import { useFilterStore } from '../../stores/useFilterStore'
import { useFilterOptions } from '../../api/hooks/useFilters'
import { SelectFilter } from './SelectFilter'

export function FilterBar() {
  const { data: options } = useFilterOptions()
  const store = useFilterStore()

  if (!options) return null

  return (
    <div className="sticky top-14 z-10 flex flex-wrap items-center gap-3 border-b border-gray-200 bg-surface px-6 py-3">
      <SelectFilter
        label="Ano"
        options={options.anos.map(String)}
        value={store.ano ? [String(store.ano)] : []}
        onChange={(v) => store.setAno(v.length ? Number(v[0]) : null)}
        single
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

      <div className="flex items-center gap-2 ml-auto">
        <input
          type="date"
          value={store.dataInicio ?? ''}
          onChange={(e) => store.setDataInicio(e.target.value || null)}
          className="rounded border border-gray-300 px-2 py-1 text-xs focus:border-primary focus:outline-none"
          placeholder="Data início"
        />
        <span className="text-xs text-gray-400">a</span>
        <input
          type="date"
          value={store.dataFim ?? ''}
          onChange={(e) => store.setDataFim(e.target.value || null)}
          className="rounded border border-gray-300 px-2 py-1 text-xs focus:border-primary focus:outline-none"
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
  )
}
