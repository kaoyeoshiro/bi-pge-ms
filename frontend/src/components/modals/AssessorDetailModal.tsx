import { useEffect } from 'react'
import { Card } from '../ui/Card'
import { Spinner } from '../ui/Spinner'
import { ErrorAlert } from '../ui/ErrorAlert'
import { KPIGrid } from '../data/KPIGrid'
import { LineChartCard } from '../charts/LineChartCard'
import { BarChartCard } from '../charts/BarChartCard'
import { usePerfilKPIs, usePerfilTimeline, usePerfilPorCategoria, usePerfilPorModelo } from '../../api/hooks/usePerfil'

interface AssessorDetailModalProps {
  assessor: string
  isOpen: boolean
  onClose: () => void
}

/**
 * Modal que exibe os detalhes de produção de um assessor específico.
 * Mostra KPIs, timeline e rankings por categoria/modelo.
 */
export function AssessorDetailModal({ assessor, isOpen, onClose }: AssessorDetailModalProps) {
  const dimensao = 'assessor'

  const { data: kpis, isLoading: loadingKPIs } = usePerfilKPIs(dimensao, assessor)
  const { data: timeline, isLoading: loadingTimeline } = usePerfilTimeline(dimensao, assessor)
  const { data: porCategoria } = usePerfilPorCategoria(dimensao, assessor, 'pecas_elaboradas', 10)
  const { data: porModelo } = usePerfilPorModelo(dimensao, assessor, 'pecas_elaboradas', 10)

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

  const isLoading = loadingKPIs || loadingTimeline

  return (
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
          <div className="max-h-[70vh] overflow-y-auto p-6">
            {isLoading && (
              <div className="flex items-center justify-center py-12">
                <Spinner />
              </div>
            )}

            {!isLoading && kpis && (
              <div className="space-y-6">
                {/* KPIs */}
                <div>
                  <h3 className="mb-3 text-sm font-semibold text-gray-700 uppercase tracking-wide">
                    Métricas Gerais
                  </h3>
                  <KPIGrid kpis={kpis} />
                </div>

                {/* Timeline */}
                {timeline && timeline.length > 0 && (
                  <div>
                    <h3 className="mb-3 text-sm font-semibold text-gray-700 uppercase tracking-wide">
                      Evolução Mensal
                    </h3>
                    <LineChartCard series={timeline} height={250} />
                  </div>
                )}

                {/* Rankings lado a lado */}
                <div className="grid gap-6 md:grid-cols-2">
                  {porCategoria && porCategoria.length > 0 && (
                    <div>
                      <h3 className="mb-3 text-sm font-semibold text-gray-700 uppercase tracking-wide">
                        Por Categoria
                      </h3>
                      <BarChartCard
                        data={porCategoria}
                        title=""
                        labelKey="grupo"
                        dataKey="total"
                        height={300}
                      />
                    </div>
                  )}

                  {porModelo && porModelo.length > 0 && (
                    <div>
                      <h3 className="mb-3 text-sm font-semibold text-gray-700 uppercase tracking-wide">
                        Por Modelo
                      </h3>
                      <BarChartCard
                        data={porModelo}
                        title=""
                        labelKey="grupo"
                        dataKey="total"
                        height={300}
                      />
                    </div>
                  )}
                </div>
              </div>
            )}

            {!isLoading && !kpis && (
              <ErrorAlert message="Não foi possível carregar os dados do assessor." />
            )}
          </div>
        </Card>
      </div>
    </div>
  )
}
