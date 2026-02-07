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
  const [pagination, setPagination] = useState<PaginationParams>({
    page: 1,
    page_size: 25,
    sort_order: 'desc',
  })

  const kpis = usePendenciasKPIs()
  const timeline = usePendenciasTimeline()
  const porArea = usePendenciasPorGrupo('area')
  const porCategoria = usePendenciasPorGrupo('categoria')
  const porChefia = usePendenciasPorGrupo('chefia')
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

        <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
          <BarChartCard
            title="Pendências — Por Área Jurídica"
            data={porArea.data}
            isLoading={porArea.isLoading}
            isError={porArea.isError}
          />
          <BarChartCard
            title="Pendências — Por Categoria"
            data={porCategoria.data}
            isLoading={porCategoria.isLoading}
            isError={porCategoria.isError}
          />
        </div>

        <BarChartCard
          title="Pendências — Por Chefia"
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
          exportTable="pendencias"
        />
      </div>
    </>
  )
}
