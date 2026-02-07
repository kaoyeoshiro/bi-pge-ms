import { useState } from 'react'
import { TopBar } from '../components/layout/TopBar'
import { FilterBar } from '../components/filters/FilterBar'
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

  const kpis = useProcessosKPIs()
  const timeline = useProcessosTimeline()
  const porChefia = useProcessosPorGrupo('chefia')
  const porProcurador = useProcessosPorGrupo('procurador')
  const lista = useProcessosLista(pagination)

  return (
    <>
      <TopBar title="Processos Novos" />
      <FilterBar />
      <div className="space-y-6 p-6">
        <KPIGrid data={kpis.data} isLoading={kpis.isLoading} isError={kpis.isError} />

        <LineChartCard
          title="Processos Novos por Mês"
          series={timeline.data}
          isLoading={timeline.isLoading}
          isError={timeline.isError}
        />

        <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
          <BarChartCard
            title="Processos Novos — Por Chefia"
            data={porChefia.data}
            isLoading={porChefia.isLoading}
            isError={porChefia.isError}
          />
          <BarChartCard
            title="Processos Novos — Por Procurador"
            data={porProcurador.data}
            isLoading={porProcurador.isLoading}
            isError={porProcurador.isError}
          />
        </div>

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
