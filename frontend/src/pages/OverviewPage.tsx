import { useState } from 'react'
import { TopBar } from '../components/layout/TopBar'
import { FilterBar } from '../components/filters/FilterBar'
import { KPIGrid } from '../components/data/KPIGrid'
import { LineChartCard } from '../components/charts/LineChartCard'
import { BarChartCard } from '../components/charts/BarChartCard'
import {
  useDashboardKPIs,
  useDashboardTimeline,
  useTopChefias,
  useTopProcuradores,
} from '../api/hooks/useDashboard'
import { useCargaReduzida } from '../api/hooks/useFilters'

const METRICA_OPTIONS = [
  { value: 'pendencias', label: 'Pendências' },
  { value: 'pecas_finalizadas', label: 'Peças Finalizadas' },
] as const

export function OverviewPage() {
  const [metrica, setMetrica] = useState('pendencias')

  const kpis = useDashboardKPIs()
  const timeline = useDashboardTimeline()
  const topChefias = useTopChefias(metrica)
  const topProcuradores = useTopProcuradores(metrica)
  const { crSet } = useCargaReduzida()

  const metricaLabel = METRICA_OPTIONS.find((m) => m.value === metrica)?.label ?? metrica

  return (
    <>
      <TopBar title="Visão Geral" />
      <FilterBar />
      <div className="space-y-4 p-4 sm:space-y-6 sm:p-6">
        <KPIGrid data={kpis.data} isLoading={kpis.isLoading} isError={kpis.isError} />

        <LineChartCard
          title="Evolução Mensal"
          series={timeline.data}
          isLoading={timeline.isLoading}
          isError={timeline.isError}
        />

        <div className="rounded-xl bg-surface shadow-sm border border-gray-100 px-3 py-2 sm:px-5 sm:py-3">
          <div className="flex flex-wrap items-center gap-2 sm:gap-3">
            <span className="text-sm font-semibold text-gray-700">Rankings por:</span>
            {METRICA_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                onClick={() => setMetrica(opt.value)}
                className={`rounded-lg px-4 py-1.5 text-sm transition-colors ${
                  metrica === opt.value
                    ? 'bg-primary text-white font-medium shadow-sm'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>

        <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
          <BarChartCard
            title={`Ranking Chefias — ${metricaLabel}`}
            data={topChefias.data}
            isLoading={topChefias.isLoading}
            isError={topChefias.isError}
          />
          <BarChartCard
            title={`Ranking Procuradores — ${metricaLabel}`}
            data={topProcuradores.data}
            isLoading={topProcuradores.isLoading}
            isError={topProcuradores.isError}
            cargaReduzidaSet={crSet}
          />
        </div>
      </div>
    </>
  )
}
