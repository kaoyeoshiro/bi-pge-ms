import { useState } from 'react'
import { TopBar } from '../components/layout/TopBar'
import { FilterBar } from '../components/filters/FilterBar'
import { KPIGrid } from '../components/data/KPIGrid'
import { LineChartCard } from '../components/charts/LineChartCard'
import { BarChartCard } from '../components/charts/BarChartCard'
import { DataTable } from '../components/data/DataTable'
import {
  usePendenciasKPIs,
  usePendenciasTimeline,
  usePendenciasPorGrupo,
  usePendenciasLista,
} from '../api/hooks/usePendencias'
import type { PaginationParams } from '../types'

const DIMENSOES = ['chefia', 'categoria'] as const
const DIMENSAO_LABELS: Record<string, string> = {
  chefia: 'Por Chefia',
  categoria: 'Por Categoria',
}

const TABLE_COLUMNS = [
  { key: 'id', label: 'ID' },
  { key: 'chefia', label: 'Chefia' },
  { key: 'data', label: 'Data', type: 'datetime' },
  { key: 'area', label: 'Área' },
  { key: 'categoria', label: 'Categoria' },
  { key: 'categoria_pendencia', label: 'Tipo' },
  { key: 'procurador', label: 'Procurador' },
  { key: 'numero_formatado', label: 'Nº Formatado' },
]

export function PendenciasPage() {
  const [dimensao, setDimensao] = useState<string>('chefia')
  const [pagination, setPagination] = useState<PaginationParams>({
    page: 1,
    page_size: 25,
    sort_order: 'desc',
  })

  const kpis = usePendenciasKPIs()
  const timeline = usePendenciasTimeline()
  const ranking = usePendenciasPorGrupo(dimensao)
  const lista = usePendenciasLista(pagination)

  return (
    <>
      <TopBar title="Pendências e Backlog" />
      <FilterBar />
      <div className="space-y-4 p-4 sm:space-y-6 sm:p-6">
        <KPIGrid data={kpis.data} isLoading={kpis.isLoading} isError={kpis.isError} />

        <LineChartCard
          title="Evolução Mensal de Pendências"
          series={timeline.data}
          isLoading={timeline.isLoading}
          isError={timeline.isError}
        />

        <div className="rounded-xl bg-surface shadow-sm border border-gray-100 px-3 py-2 sm:px-5 sm:py-3">
          <div className="flex flex-wrap items-center gap-2 sm:gap-3">
            <span className="text-sm font-semibold text-gray-700">Ranking por:</span>
            {DIMENSOES.map((dim) => (
              <button
                key={dim}
                onClick={() => setDimensao(dim)}
                className={`rounded-lg px-4 py-1.5 text-sm transition-colors ${
                  dimensao === dim
                    ? 'bg-primary text-white font-medium shadow-sm'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                {DIMENSAO_LABELS[dim]}
              </button>
            ))}
          </div>
        </div>

        <BarChartCard
          title={`Pendências — ${DIMENSAO_LABELS[dimensao]}`}
          data={ranking.data}
          isLoading={ranking.isLoading}
          isError={ranking.isError}
        />

        <DataTable
          data={lista.data}
          columns={TABLE_COLUMNS}
          isLoading={lista.isLoading}
          isError={lista.isError}
          pagination={pagination}
          onPaginationChange={(p) => setPagination((prev) => ({ ...prev, ...p }))}
          exportTable="pendencias"
        />
      </div>
    </>
  )
}
