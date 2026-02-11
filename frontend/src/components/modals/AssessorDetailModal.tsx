import { useEffect } from 'react'
import { Card } from '../ui/Card'
import { Spinner } from '../ui/Spinner'
import { ErrorAlert } from '../ui/ErrorAlert'
import { KPIGrid } from '../data/KPIGrid'
import { LineChartCard } from '../charts/LineChartCard'
import { BarChartCard } from '../charts/BarChartCard'
import { usePerfilKPIs, usePerfilTimeline, usePerfilPorCategoria, usePerfilPorModelo } from '../../api/hooks/usePerfil'
import { FilterParamsProvider, type FilterParams } from '../../api/hooks/useFilterParams'

interface AssessorDetailModalProps {
  assessor: string
  isOpen: boolean
  onClose: () => void
  params?: FilterParams
}

/**
 * Modal que exibe os detalhes de produção de um assessor específico.
 * Mostra KPIs, timeline e rankings por categoria/modelo.
 * Quando params é fornecido, filtra os dados pelo ano/período selecionado.
 */
export function AssessorDetailModal({ assessor, isOpen, onClose, params }: AssessorDetailModalProps) {
  // Fechar com ESC
  useEffect(() => {
    if (!isOpen) return
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', handleEsc)
    return () => window.removeEventListener('keydown', handleEsc)
  }, [isOpen, onClose])

  // Prevenir scroll do body quando modal aberto
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden'
    } else {
      document.body.style.overflow = ''
    }
    return () => {
      document.body.style.overflow = ''
    }
  }, [isOpen])

  if (!isOpen) return null

  // Extrai anos para exibição no título
  const anosLabel = params?.anos
    ? Array.isArray(params.anos)
      ? params.anos.join(', ')
      : params.anos
    : null

  return (
    <FilterParamsProvider value={params ?? {}}>
      <div className="fixed inset-0 z-[9999] flex items-start justify-center overflow-y-auto bg-black/50 p-4">
        {/* Backdrop - fecha ao clicar */}
        <div className="fixed inset-0" onClick={onClose} />

        {/* Modal */}
        <div className="relative z-10 my-8 w-full max-w-5xl">
          <Card className="relative">
            {/* Header */}
            <div className="sticky top-0 z-20 flex items-center justify-between border-b border-gray-200 bg-white px-6 py-4">
              <div>
                <h2 className="text-xl font-semibold text-gray-900">
                  Produção do Assessor
                  {anosLabel && <span className="ml-2 text-base font-normal text-gray-500">({anosLabel})</span>}
                </h2>
                <p className="mt-1 text-sm text-gray-600">{assessor}</p>
              </div>
              <button
                onClick={onClose}
                className="rounded-lg p-2 text-gray-400 hover:bg-gray-100 hover:text-gray-600 transition-colors"
                aria-label="Fechar"
              >
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="h-5 w-5">
                  <path d="M6.28 5.22a.75.75 0 0 0-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 1 0 1.06 1.06L10 11.06l3.72 3.72a.75.75 0 1 0 1.06-1.06L11.06 10l3.72-3.72a.75.75 0 0 0-1.06-1.06L10 8.94 6.28 5.22Z" />
                </svg>
              </button>
            </div>

            {/* Conteúdo */}
            <AssessorDetailContent assessor={assessor} />
          </Card>
        </div>
      </div>
    </FilterParamsProvider>
  )
}

/** Conteúdo interno do modal - usa useFilterParams via contexto */
function AssessorDetailContent({ assessor }: { assessor: string }) {
  const dimensao = 'assessor'

  const { data: kpis, isLoading: loadingKPIs, isError: errorKPIs } = usePerfilKPIs(dimensao, assessor)
  const { data: timeline, isLoading: loadingTimeline, isError: errorTimeline } = usePerfilTimeline(dimensao, assessor)
  const { data: porCategoria, isLoading: loadingCategoria, isError: errorCategoria } = usePerfilPorCategoria(dimensao, assessor, 'pecas_elaboradas', 10)
  const { data: porModelo, isLoading: loadingModelo, isError: errorModelo } = usePerfilPorModelo(dimensao, assessor, 'pecas_elaboradas', 10)

  const isLoading = loadingKPIs || loadingTimeline
  const hasError = errorKPIs || errorTimeline

  return (
    <div className="max-h-[70vh] overflow-y-auto p-6">
      {isLoading && (
        <div className="flex items-center justify-center py-12">
          <Spinner />
        </div>
      )}

      {hasError && <ErrorAlert message="Não foi possível carregar os dados do assessor." />}

      {!isLoading && !hasError && (
        <div className="space-y-6">
          {/* KPIs */}
          <div>
            <h3 className="mb-3 text-sm font-semibold text-gray-700 uppercase tracking-wide">
              Métricas Gerais
            </h3>
            <KPIGrid data={kpis} isLoading={false} isError={false} />
          </div>

          {/* Timeline */}
          <LineChartCard
            title="Evolução Mensal"
            series={timeline}
            isLoading={loadingTimeline}
            isError={errorTimeline}
          />

          {/* Rankings lado a lado */}
          <div className="grid gap-6 md:grid-cols-2">
            <BarChartCard
              title="Por Categoria"
              data={porCategoria}
              isLoading={loadingCategoria}
              isError={errorCategoria}
            />

            <BarChartCard
              title="Por Modelo"
              data={porModelo}
              isLoading={loadingModelo}
              isError={errorModelo}
            />
          </div>
        </div>
      )}
    </div>
  )
}
