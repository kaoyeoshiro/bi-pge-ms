import { useState } from 'react'
import { Card } from '../ui/Card'
import { Spinner } from '../ui/Spinner'
import { EmptyState } from '../ui/EmptyState'
import { ErrorAlert } from '../ui/ErrorAlert'
import { CHART_COLORS } from '../../utils/colors'
import { formatCurrency, formatNumber } from '../../utils/formatters'
import type { ValorGroupItem } from '../../types'

const INITIAL_VISIBLE = 15
const EXPAND_STEP = 30

interface ValorRankingCardProps {
  title: string
  data: ValorGroupItem[] | undefined
  isLoading: boolean
  isError: boolean
  metrica: 'total' | 'medio'
}

export function ValorRankingCard({ title, data, isLoading, isError, metrica }: ValorRankingCardProps) {
  const [visibleCount, setVisibleCount] = useState(INITIAL_VISIBLE)

  if (isLoading) return <Card title={title}><Spinner /></Card>
  if (isError) return <Card title={title}><ErrorAlert /></Card>
  if (!data?.length) return <Card title={title}><EmptyState /></Card>

  const getValue = (d: ValorGroupItem) =>
    metrica === 'total' ? d.valor_total : d.valor_medio

  const maxValue = Math.max(...data.map(getValue))
  const visibleData = data.slice(0, visibleCount)
  const hasMore = visibleCount < data.length
  const remaining = data.length - visibleCount

  return (
    <Card title={title}>
      <div className="space-y-3">
        {visibleData.map((d, i) => (
          <div key={d.grupo}>
            <div className="flex items-baseline justify-between gap-2 mb-1 sm:gap-4">
              <span className="min-w-0 break-words text-[13px] leading-tight text-gray-700">
                {d.grupo}
              </span>
              <div className="flex items-baseline gap-2 shrink-0">
                <span className="text-[11px] text-gray-400 tabular-nums">
                  {formatNumber(d.qtd_processos)} proc.
                </span>
                <span className="text-[13px] font-semibold text-gray-900 tabular-nums">
                  {formatCurrency(getValue(d))}
                </span>
              </div>
            </div>
            <div className="h-5 w-full rounded bg-gray-100">
              <div
                className="h-full rounded transition-all duration-300"
                style={{
                  width: `${(getValue(d) / maxValue) * 100}%`,
                  backgroundColor: CHART_COLORS[i % CHART_COLORS.length],
                }}
              />
            </div>
          </div>
        ))}
      </div>

      {data.length > INITIAL_VISIBLE && (
        <div className="mt-4 flex items-center justify-center gap-3 border-t border-gray-100 pt-3">
          {hasMore && (
            <button
              onClick={() => setVisibleCount((prev) => Math.min(prev + EXPAND_STEP, data.length))}
              className="text-sm font-medium text-primary hover:text-primary-light transition-colors"
            >
              Ver mais {Math.min(EXPAND_STEP, remaining)} de {remaining} restantes
            </button>
          )}
          {visibleCount > INITIAL_VISIBLE && (
            <>
              {hasMore && <span className="text-gray-300">|</span>}
              <button
                onClick={() => setVisibleCount(INITIAL_VISIBLE)}
                className="text-sm font-medium text-gray-500 hover:text-gray-700 transition-colors"
              >
                Recolher
              </button>
            </>
          )}
        </div>
      )}
    </Card>
  )
}
