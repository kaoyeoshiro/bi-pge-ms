import { useState } from 'react'
import { TopBar } from '../components/layout/TopBar'
import { FilterBar } from '../components/filters/FilterBar'
import { KPIGrid } from '../components/data/KPIGrid'
import { LineChartCard } from '../components/charts/LineChartCard'
import { BarChartCard } from '../components/charts/BarChartCard'
import { DataTable } from '../components/data/DataTable'
import { useProducaoKPIs, useProducaoTimeline, useProducaoPorGrupo, useProducaoLista } from '../api/hooks/useProducao'
import type { PaginationParams } from '../types'

const DIMENSOES = ['procurador', 'chefia', 'categoria', 'usuario'] as const
const DIMENSAO_LABELS: Record<string, string> = {
  procurador: 'Por Procurador',
  chefia: 'Por Chefia',
  categoria: 'Por Categoria',
  usuario: 'Por Usuário',
}

const TIPO_OPTIONS = [
  { value: 'elaboradas', label: 'Peças Elaboradas' },
  { value: 'finalizadas', label: 'Peças Finalizadas' },
] as const

const TABLE_COLUMNS = [
  { key: 'id', label: 'ID' },
  { key: 'chefia', label: 'Chefia' },
  { key: 'data', label: 'Data', type: 'datetime' },
  { key: 'usuario_criacao', label: 'Usuário de Criação' },
  { key: 'categoria', label: 'Categoria' },
  { key: 'procurador', label: 'Procurador' },
  { key: 'numero_formatado', label: 'Nº Formatado' },
]

export function ProducaoPage() {
  const [dimensao, setDimensao] = useState<string>('procurador')
  const [tipo, setTipo] = useState('elaboradas')
  const [pagination, setPagination] = useState<PaginationParams>({
    page: 1,
    page_size: 25,
    sort_order: 'desc',
  })

  const kpis = useProducaoKPIs()
  const timeline = useProducaoTimeline()
  const ranking = useProducaoPorGrupo(dimensao, tipo)
  const lista = useProducaoLista('elaboradas', pagination)

  const tipoLabel = TIPO_OPTIONS.find((t) => t.value === tipo)?.label ?? tipo

  return (
    <>
      <TopBar title="Produção" />
      <FilterBar />
      <div className="space-y-6 p-6">
        <KPIGrid data={kpis.data} isLoading={kpis.isLoading} isError={kpis.isError} />

        <LineChartCard
          title="Elaboradas vs Finalizadas por Mês"
          series={timeline.data}
          isLoading={timeline.isLoading}
          isError={timeline.isError}
        />

        <div className="rounded-xl bg-surface shadow-sm border border-gray-100 px-5 py-3">
          <div className="flex flex-wrap items-center gap-3">
            <span className="text-sm font-semibold text-gray-700">Ranking de:</span>
            {TIPO_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                onClick={() => setTipo(opt.value)}
                className={`rounded-lg px-4 py-1.5 text-sm transition-colors ${
                  tipo === opt.value
                    ? 'bg-primary text-white font-medium shadow-sm'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                {opt.label}
              </button>
            ))}

            <span className="ml-4 text-sm text-gray-300">|</span>

            {DIMENSOES.map((dim) => (
              <button
                key={dim}
                onClick={() => setDimensao(dim)}
                className={`rounded-lg px-4 py-1.5 text-sm transition-colors ${
                  dimensao === dim
                    ? 'bg-gray-700 text-white font-medium shadow-sm'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                {DIMENSAO_LABELS[dim]}
              </button>
            ))}
          </div>
        </div>

        <BarChartCard
          title={`${tipoLabel} — ${DIMENSAO_LABELS[dimensao]}`}
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
          exportTable="pecas_elaboradas"
        />
      </div>
    </>
  )
}
