import { useState, useMemo, useEffect } from 'react'
import { Card } from '../ui/Card'
import { Spinner } from '../ui/Spinner'
import { EmptyState } from '../ui/EmptyState'
import { ErrorAlert } from '../ui/ErrorAlert'
import { ClickableRow } from '../ui/ClickableRow'
import { CHART_COLORS } from '../../utils/colors'
import { formatNumber } from '../../utils/formatters'
import { useAssuntoDrillDown } from '../../api/hooks/useAssuntoExplorer'

interface BreadcrumbItem {
  codigo: number
  nome: string
}

interface AssuntoExplorerCardProps {
  title: string
  /** Quando o filtro de assunto está ativo, auto-navega para este nó com caminho completo. */
  filterAssunto?: { codigo: number; nome: string; path: { codigo: number; nome: string }[] } | null
}

/**
 * Card de exploração hierárquica de assuntos (drill-down).
 * Usado na página de Explorar Assuntos (sem filtro de perfil).
 */
export function AssuntoExplorerCard({ title, filterAssunto }: AssuntoExplorerCardProps) {
  const [path, setPath] = useState<BreadcrumbItem[]>([])

  // Auto-navegar quando o filtro de assunto muda (usa caminho completo)
  useEffect(() => {
    if (filterAssunto?.path?.length) {
      setPath(filterAssunto.path)
    } else {
      setPath([])
    }
  }, [filterAssunto?.codigo])

  const assuntoPai = path.length > 0 ? path[path.length - 1].codigo : null

  const { data, isLoading, isError } = useAssuntoDrillDown(assuntoPai, 15)

  const somaTotal = useMemo(
    () => data?.reduce((acc, d) => acc + d.total, 0) ?? 0,
    [data],
  )

  function handleDrillDown(codigo: number, nome: string) {
    setPath((prev) => [...prev, { codigo, nome }])
  }

  function handleBreadcrumb(index: number) {
    // index -1 = raiz ("Tudo"), 0 = primeiro nível, etc.
    if (index < 0) {
      setPath([])
    } else {
      setPath((prev) => prev.slice(0, index + 1))
    }
  }

  function handleBack() {
    setPath((prev) => prev.slice(0, -1))
  }

  if (isLoading) return <Card title={title}><Spinner /></Card>
  if (isError) return <Card title={title}><ErrorAlert /></Card>
  if (!data?.length) {
    return (
      <Card title={title}>
        {path.length > 0 && (
          <Breadcrumb path={path} onNavigate={handleBreadcrumb} onBack={handleBack} />
        )}
        <EmptyState />
      </Card>
    )
  }

  const maxTotal = Math.max(...data.map((d) => d.total))

  return (
    <Card title={title}>
      {/* Breadcrumb de navegação */}
      {path.length > 0 && (
        <Breadcrumb path={path} onNavigate={handleBreadcrumb} onBack={handleBack} />
      )}

      {/* Barras horizontais */}
      <div className="space-y-3">
        {data.map((d, i) => {
          const pct = somaTotal > 0 ? (d.total / somaTotal) * 100 : 0
          const canDrill = d.has_children

          return (
            <ClickableRow
              key={d.codigo}
              isClickable={canDrill}
              onClick={() => handleDrillDown(d.codigo, d.grupo)}
              ariaLabel={canDrill ? `Ver subassuntos de ${d.grupo}` : undefined}
              title={canDrill ? 'Clique para ver subassuntos' : undefined}
              showIconAlways={true}
            >
              <div className="flex items-baseline justify-between gap-2 mb-1 sm:gap-4">
                <span className="min-w-0 break-words text-[13px] leading-tight text-gray-700 group-hover:text-gray-900 transition-colors">
                  {d.grupo}
                </span>
                <span className="text-[13px] font-semibold text-gray-900 shrink-0 tabular-nums">
                  {formatNumber(d.total)}
                  <span className="ml-1 text-[11px] font-normal text-gray-400">
                    ({pct.toFixed(1)}%)
                  </span>
                </span>
              </div>
              <div className="h-5 w-full rounded bg-gray-100">
                <div
                  className="h-full rounded transition-all duration-300 group-hover:shadow-sm"
                  style={{
                    width: `${(d.total / maxTotal) * 100}%`,
                    backgroundColor: CHART_COLORS[i % CHART_COLORS.length],
                  }}
                />
              </div>
            </ClickableRow>
          )
        })}
      </div>
    </Card>
  )
}

/** Breadcrumb com botão voltar e caminho clicável. */
function Breadcrumb({
  path,
  onNavigate,
  onBack,
}: {
  path: BreadcrumbItem[]
  onNavigate: (index: number) => void
  onBack: () => void
}) {
  return (
    <div className="flex items-center gap-1.5 mb-4 text-[13px] flex-wrap">
      <button
        onClick={onBack}
        className="flex items-center justify-center h-6 w-6 rounded hover:bg-gray-100 text-gray-500 hover:text-gray-700 transition-colors shrink-0"
        title="Voltar um nível"
      >
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4">
          <path fillRule="evenodd" d="M17 10a.75.75 0 0 1-.75.75H5.612l4.158 3.96a.75.75 0 1 1-1.04 1.08l-5.5-5.25a.75.75 0 0 1 0-1.08l5.5-5.25a.75.75 0 1 1 1.04 1.08L5.612 9.25H16.25A.75.75 0 0 1 17 10Z" clipRule="evenodd" />
        </svg>
      </button>
      <button
        onClick={() => onNavigate(-1)}
        className="text-blue-600 hover:text-blue-800 hover:underline transition-colors"
      >
        Tudo
      </button>
      {path.map((item, i) => (
        <span key={item.codigo} className="flex items-center gap-1.5">
          <span className="text-gray-400">/</span>
          {i < path.length - 1 ? (
            <button
              onClick={() => onNavigate(i)}
              className="text-blue-600 hover:text-blue-800 hover:underline transition-colors"
            >
              {item.nome}
            </button>
          ) : (
            <span className="font-medium text-gray-700">{item.nome}</span>
          )}
        </span>
      ))}
    </div>
  )
}
