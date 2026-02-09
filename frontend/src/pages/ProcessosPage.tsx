import { useState, useEffect } from 'react'
import { TopBar } from '../components/layout/TopBar'
import { FilterBar } from '../components/filters/FilterBar'
import { TreeSelectFilter } from '../components/filters/TreeSelectFilter'
import { KPIGrid } from '../components/data/KPIGrid'
import { LineChartCard } from '../components/charts/LineChartCard'
import { BarChartCard } from '../components/charts/BarChartCard'
import { DataTable } from '../components/data/DataTable'
import {
  useProcessosKPIs,
  useProcessosTimeline,
  useProcessosPorGrupo,
  useProcessosLista,
} from '../api/hooks/useProcessos'
import { useAssuntosTree } from '../api/hooks/useFilters'
import { useFilterStore } from '../stores/useFilterStore'
import type { PaginationParams } from '../types'

const TABLE_COLUMNS = [
  { key: 'id', label: 'ID' },
  { key: 'chefia', label: 'Chefia' },
  { key: 'data', label: 'Data', type: 'datetime' },
  { key: 'codigo_processo', label: 'Código' },
  { key: 'numero_formatado', label: 'Nº Formatado' },
  { key: 'procurador', label: 'Procurador' },
]

export function ProcessosPage() {
  const [pagination, setPagination] = useState<PaginationParams>({
    page: 1,
    page_size: 25,
    sort_order: 'desc',
  })

  const { data: assuntosTree } = useAssuntosTree()
  const assuntos = useFilterStore((s) => s.assuntos)
  const setAssuntos = useFilterStore((s) => s.setAssuntos)

  // Limpar filtro de assunto ao sair da página (só faz sentido aqui)
  useEffect(() => {
    return () => setAssuntos([])
  }, [setAssuntos])

  const kpis = useProcessosKPIs()
  const timeline = useProcessosTimeline()
  const porChefia = useProcessosPorGrupo('chefia')
  const lista = useProcessosLista(pagination)

  return (
    <>
      <TopBar title="Processos Novos" />
      <FilterBar />
      {assuntosTree && assuntosTree.length > 0 && (
        <div className="flex items-center gap-2 border-b border-gray-200 bg-surface px-3 py-2 sm:px-6 sm:py-2">
          <TreeSelectFilter
            label="Assunto"
            tree={assuntosTree}
            value={assuntos}
            onChange={setAssuntos}
          />
          {assuntos.length > 0 && (
            <button
              onClick={() => setAssuntos([])}
              className="rounded px-2 py-1 text-xs text-gray-500 hover:bg-gray-100 transition-colors"
            >
              Limpar assunto
            </button>
          )}
        </div>
      )}
      <div className="space-y-4 p-4 sm:space-y-6 sm:p-6">
        <KPIGrid data={kpis.data} isLoading={kpis.isLoading} isError={kpis.isError} />

        <LineChartCard
          title="Processos Novos por Mês"
          series={timeline.data}
          isLoading={timeline.isLoading}
          isError={timeline.isError}
        />

        <BarChartCard
          title="Processos Novos — Por Chefia"
          data={porChefia.data}
          isLoading={porChefia.isLoading}
          isError={porChefia.isError}
        />

        <DataTable
          data={lista.data}
          columns={TABLE_COLUMNS}
          isLoading={lista.isLoading}
          isError={lista.isError}
          pagination={pagination}
          onPaginationChange={(p) => setPagination((prev) => ({ ...prev, ...p }))}
          exportTable="processos_novos"
        />
      </div>
    </>
  )
}
