import { useState, useMemo } from 'react'
import { PerfilPage } from './PerfilPage'
import { useFilterOptions, useAssessores } from '../api/hooks/useFilters'
import { useComparativoAssessores } from '../api/hooks/usePerfil'
import { Card } from '../components/ui/Card'
import { Spinner } from '../components/ui/Spinner'
import { EmptyState } from '../components/ui/EmptyState'
import { AssessorDetailModal } from '../components/modals/AssessorDetailModal'
import { usePageFilters } from '../hooks/usePageFilters'
import { FilterParamsProvider } from '../api/hooks/useFilterParams'
import type { FilterParams } from '../api/hooks/useFilterParams'
import { formatNumber } from '../utils/formatters'
import { CHART_COLORS } from '../utils/colors'
import { PageFilterBar } from '../components/filters/PageFilterBar'

type ModoSelecao = 'individual' | 'chefia'

const TABS = [
  { id: 'individual', label: 'Análise Individual', icon: '👤' },
  { id: 'chefia', label: 'Ranking por Chefia', icon: '📊' },
] as const

export function PerfilAssessorPage() {
  const [modo, setModo] = useState<ModoSelecao>('individual')
  const [chefiaSelecionada, setChefiaSelecionada] = useState<string | null>(null)
  const [assessorSelecionado, setAssessorSelecionado] = useState<string | null>(null)

  const { data: options } = useFilterOptions()
  const { data: assessores } = useAssessores()
  const { params: baseParams, ...filterBarProps } = usePageFilters()

  const params = useMemo((): FilterParams => {
    return { ...baseParams }
  }, [baseParams])

  return (
    <>
      {/* Header customizado com título + tabs */}
      <div className="sticky top-0 z-20 border-b border-gray-200 bg-white shadow-sm">
        <div className="flex items-center gap-4 px-4 py-3 sm:px-6">
          <h2 className="text-lg font-semibold text-gray-900">
            Perfil do Assessor
          </h2>

          {/* Tabs em container destacado */}
          <div className="flex gap-1 rounded-lg border border-gray-200 bg-gray-50 p-1">
            {TABS.map((tab) => {
              const isActive = tab.id === modo
              return (
                <button
                  key={tab.id}
                  onClick={() => setModo(tab.id as ModoSelecao)}
                  className={`
                    flex items-center gap-2 rounded-md px-4 py-2 text-sm font-medium transition-all
                    ${
                      isActive
                        ? 'bg-white text-primary shadow-sm'
                        : 'text-gray-600 hover:text-gray-900'
                    }
                  `}
                >
                  <span className="text-base">{tab.icon}</span>
                  <span>{tab.label}</span>
                </button>
              )
            })}
          </div>
        </div>
      </div>

      {/* Tab: Análise Individual */}
      {modo === 'individual' && (
        <FilterParamsProvider value={params}>
          <PerfilPage
            title=""
            dimensao="assessor"
            placeholder="Selecione o assessor"
            options={assessores}
            showProcuradorChart
          />
        </FilterParamsProvider>
      )}

      {/* Tab: Ranking por Chefia */}
      {modo === 'chefia' && (
        <>
          <PageFilterBar {...filterBarProps} />
          <FilterParamsProvider value={params}>
            <div className="space-y-6 p-4 sm:p-6">
              <Card>
                <div>
                  <label className="mb-1.5 block text-sm font-medium text-gray-700">
                    Selecione a chefia
                  </label>
                  <select
                    value={chefiaSelecionada ?? ''}
                    onChange={(e) => setChefiaSelecionada(e.target.value || null)}
                    className="w-full rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm text-gray-900 shadow-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                  >
                    <option value="">-- Selecione uma chefia --</option>
                    {options?.chefias.map((c) => (
                      <option key={c} value={c}>
                        {c}
                      </option>
                    ))}
                  </select>
                </div>
              </Card>

              {!chefiaSelecionada && (
                <div className="rounded-xl border border-dashed border-gray-300 bg-gray-50 p-6 text-center sm:p-12">
                  <p className="text-sm text-gray-500">
                    Selecione uma chefia acima para ver o ranking de assessores
                  </p>
                </div>
              )}

              {chefiaSelecionada && (
                <RankingChefia
                  chefia={chefiaSelecionada}
                  params={params}
                  onAssessorClick={setAssessorSelecionado}
                />
              )}
            </div>
          </FilterParamsProvider>
        </>
      )}

      {/* Modal de detalhes do assessor */}
      <AssessorDetailModal
        assessor={assessorSelecionado || ''}
        isOpen={!!assessorSelecionado}
        onClose={() => setAssessorSelecionado(null)}
      />
    </>
  )
}

function RankingChefia({
  chefia,
  params,
  onAssessorClick,
}: {
  chefia: string
  params: FilterParams
  onAssessorClick: (assessor: string) => void
}) {
  const {
    data: ranking,
    isLoading,
    isError,
  } = useComparativoAssessores(chefia, params)

  if (isLoading) {
    return (
      <Card>
        <Spinner />
      </Card>
    )
  }

  if (isError) {
    return (
      <Card>
        <div className="text-center text-sm text-red-600">
          Erro ao carregar ranking de assessores
        </div>
      </Card>
    )
  }

  if (!ranking || ranking.length === 0) {
    return (
      <Card>
        <EmptyState />
      </Card>
    )
  }

  const maxTotal = Math.max(...ranking.map((r: any) => r.total))

  return (
    <Card>
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-900">
          Ranking de Assessores - {chefia}
        </h3>
        <span className="text-xs text-gray-500">
          Clique no nome para ver detalhes
        </span>
      </div>

      <div className="space-y-4">
        {ranking.map((assessor: any, index: number) => {
          const pctTotal = maxTotal > 0 ? (assessor.total / maxTotal) * 100 : 0

          return (
            <div
              key={assessor.assessor}
              className="group space-y-2 rounded-lg p-3 transition-all hover:bg-gray-50 cursor-pointer"
              onClick={() => onAssessorClick(assessor.assessor)}
            >
              {/* Cabeçalho */}
              <div className="flex items-baseline justify-between gap-2">
                <div className="flex items-center gap-2">
                  <span className="flex h-7 w-7 items-center justify-center rounded-full bg-gray-100 text-xs font-bold text-gray-700 group-hover:bg-primary group-hover:text-white transition-colors">
                    {index + 1}
                  </span>
                  <span className="text-sm font-medium text-gray-900 group-hover:text-primary transition-colors">
                    {assessor.assessor}
                  </span>
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    viewBox="0 0 16 16"
                    fill="currentColor"
                    className="h-4 w-4 text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity"
                  >
                    <path fillRule="evenodd" d="M2 8a6 6 0 1 1 12 0A6 6 0 0 1 2 8Zm6-3a.75.75 0 0 1 .75.75v2.5h2.5a.75.75 0 0 1 0 1.5h-2.5v2.5a.75.75 0 0 1-1.5 0v-2.5h-2.5a.75.75 0 0 1 0-1.5h2.5v-2.5A.75.75 0 0 1 8 5Z" clipRule="evenodd" />
                  </svg>
                </div>
                <span className="text-sm font-bold text-gray-900">
                  {formatNumber(assessor.total)}
                </span>
              </div>

              {/* Barra principal (total) */}
              <div className="h-7 w-full overflow-hidden rounded bg-gray-100">
                <div
                  className="h-full transition-all duration-300"
                  style={{
                    width: `${pctTotal}%`,
                    backgroundColor: CHART_COLORS[index % CHART_COLORS.length],
                  }}
                />
              </div>

              {/* Detalhamento */}
              <div className="flex gap-4 text-xs text-gray-600">
                <span>
                  <strong className="font-medium text-gray-700">
                    {formatNumber(assessor.pecas_elaboradas)}
                  </strong>{' '}
                  elaboradas
                </span>
                <span>
                  <strong className="font-medium text-gray-700">
                    {formatNumber(assessor.pecas_finalizadas)}
                  </strong>{' '}
                  finalizadas
                </span>
              </div>
            </div>
          )
        })}
      </div>
    </Card>
  )
}
