import { useState } from 'react'
import { TopBar } from '../components/layout/TopBar'
import { FilterBar } from '../components/filters/FilterBar'
import { KPIGrid } from '../components/data/KPIGrid'
import { LineChartCard } from '../components/charts/LineChartCard'
import { FaixaDistributionCard } from '../components/charts/FaixaDistributionCard'
import { ValorRankingCard } from '../components/charts/ValorRankingCard'
import { DataTable } from '../components/data/DataTable'
import {
  useValoresKPIs,
  useValoresDistribuicao,
  useValoresPorGrupo,
  useValoresTimeline,
  useValoresLista,
} from '../api/hooks/useValores'
import type { PaginationParams } from '../types'

const DIMENSOES = ['chefia', 'procurador', 'assunto'] as const
const DIMENSAO_LABELS: Record<string, string> = {
  chefia: 'Chefia',
  procurador: 'Procurador',
  assunto: 'Assunto',
}

const METRICAS = ['total', 'medio'] as const
const METRICA_LABELS: Record<string, string> = {
  total: 'Valor Total',
  medio: 'Valor Médio',
}

const TABLE_COLUMNS = [
  { key: 'id', label: 'ID' },
  { key: 'chefia', label: 'Chefia' },
  { key: 'data', label: 'Data', type: 'datetime' },
  { key: 'procurador', label: 'Procurador' },
  { key: 'numero_formatado', label: 'Nº Formatado' },
  { key: 'valor_acao', label: 'Valor da Causa', type: 'currency' },
]

export function ValoresPage() {
  const [dimensao, setDimensao] = useState<string>('chefia')
  const [metrica, setMetrica] = useState<string>('total')
  const [pagination, setPagination] = useState<PaginationParams>({
    page: 1,
    page_size: 25,
    sort_by: 'valor_acao',
    sort_order: 'desc',
  })

  const kpis = useValoresKPIs()
  const distribuicao = useValoresDistribuicao()
  const timeline = useValoresTimeline()
  const ranking = useValoresPorGrupo(dimensao, metrica)
  const lista = useValoresLista(pagination)

  return (
    <>
      <TopBar title="Valor da Causa" />
      <FilterBar showValorFaixa />
      <div className="space-y-4 p-4 sm:space-y-6 sm:p-6">
        <KPIGrid data={kpis.data} isLoading={kpis.isLoading} isError={kpis.isError} />

        <div className="grid gap-4 sm:gap-6 lg:grid-cols-2">
          <FaixaDistributionCard
            data={distribuicao.data}
            isLoading={distribuicao.isLoading}
            isError={distribuicao.isError}
          />
          <LineChartCard
            title="Evolução Mensal do Valor"
            series={timeline.data}
            isLoading={timeline.isLoading}
            isError={timeline.isError}
          />
        </div>

        {/* Seletores de dimensão e métrica */}
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
            <span className="mx-1 text-gray-300">|</span>
            <span className="text-sm font-semibold text-gray-700">Métrica:</span>
            {METRICAS.map((m) => (
              <button
                key={m}
                onClick={() => setMetrica(m)}
                className={`rounded-lg px-4 py-1.5 text-sm transition-colors ${
                  metrica === m
                    ? 'bg-primary text-white font-medium shadow-sm'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                {METRICA_LABELS[m]}
              </button>
            ))}
          </div>
        </div>

        <ValorRankingCard
          title={`${METRICA_LABELS[metrica]} por ${DIMENSAO_LABELS[dimensao]}`}
          data={ranking.data}
          isLoading={ranking.isLoading}
          isError={ranking.isError}
          metrica={metrica as 'total' | 'medio'}
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
