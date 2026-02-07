import { useState } from 'react'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts'
import { Card } from '../ui/Card'
import { Spinner } from '../ui/Spinner'
import { EmptyState } from '../ui/EmptyState'
import { ErrorAlert } from '../ui/ErrorAlert'
import { CHART_COLORS } from '../../utils/colors'
import { formatNumber } from '../../utils/formatters'
import type { GroupCount } from '../../types'

const INITIAL_VISIBLE = 15
const EXPAND_STEP = 30

interface BarChartCardProps {
  title: string
  data: GroupCount[] | undefined
  isLoading: boolean
  isError: boolean
  layout?: 'horizontal' | 'vertical'
  onClick?: (grupo: string) => void
  cargaReduzidaSet?: Set<string>
}

export function BarChartCard({
  title,
  data,
  isLoading,
  isError,
  layout = 'horizontal',
  onClick,
  cargaReduzidaSet,
}: BarChartCardProps) {
  if (isLoading) return <Card title={title}><Spinner /></Card>
  if (isError) return <Card title={title}><ErrorAlert /></Card>
  if (!data?.length) return <Card title={title}><EmptyState /></Card>

  if (layout === 'horizontal') {
    return <HorizontalBars title={title} data={data} onClick={onClick} cargaReduzidaSet={cargaReduzidaSet} />
  }

  return <VerticalBars title={title} data={data} onClick={onClick} />
}

/** Barras horizontais com nomes completos — HTML/CSS puro + expansão progressiva. */
function HorizontalBars({
  title,
  data,
  onClick,
  cargaReduzidaSet,
}: {
  title: string
  data: GroupCount[]
  onClick?: (grupo: string) => void
  cargaReduzidaSet?: Set<string>
}) {
  const [visibleCount, setVisibleCount] = useState(INITIAL_VISIBLE)
  const maxTotal = Math.max(...data.map((d) => d.total))
  const visibleData = data.slice(0, visibleCount)
  const hasMore = visibleCount < data.length
  const remaining = data.length - visibleCount

  function handleExpand() {
    setVisibleCount((prev) => Math.min(prev + EXPAND_STEP, data.length))
  }

  function handleCollapse() {
    setVisibleCount(INITIAL_VISIBLE)
  }

  return (
    <Card title={title}>
      <div className="space-y-3">
        {visibleData.map((d, i) => (
          <div
            key={d.grupo}
            className={onClick ? 'cursor-pointer group' : 'group'}
            onClick={() => onClick?.(d.grupo)}
          >
            <div className="flex items-baseline justify-between gap-2 mb-1 sm:gap-4">
              <span className="min-w-0 break-words text-[13px] leading-tight text-gray-700 group-hover:text-gray-900 transition-colors">
                {d.grupo}
                {cargaReduzidaSet?.has(d.grupo) && (
                  <span className="ml-1.5 inline-flex items-center rounded-full bg-amber-100 px-1.5 py-0.5 text-[10px] font-bold text-amber-700" title="Carga Reduzida">
                    CR
                  </span>
                )}
              </span>
              <span className="text-[13px] font-semibold text-gray-900 shrink-0 tabular-nums">
                {formatNumber(d.total)}
              </span>
            </div>
            <div className="h-5 w-full rounded bg-gray-100">
              <div
                className="h-full rounded transition-all duration-300"
                style={{
                  width: `${(d.total / maxTotal) * 100}%`,
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
              onClick={handleExpand}
              className="text-sm font-medium text-primary hover:text-primary-light transition-colors"
            >
              Ver mais {Math.min(EXPAND_STEP, remaining)} de {remaining} restantes
            </button>
          )}
          {visibleCount > INITIAL_VISIBLE && (
            <>
              {hasMore && <span className="text-gray-300">|</span>}
              <button
                onClick={handleCollapse}
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

/** Barras verticais (nomes no eixo X) — Recharts. */
function VerticalBars({
  title,
  data,
  onClick,
}: {
  title: string
  data: GroupCount[]
  onClick?: (grupo: string) => void
}) {
  const chartData = data.map((d) => ({
    name: d.grupo.length > 20 ? d.grupo.slice(0, 20) + '...' : d.grupo,
    fullName: d.grupo,
    total: d.total,
  }))

  return (
    <Card title={title}>
      <ResponsiveContainer width="100%" height={320}>
        <BarChart data={chartData} margin={{ top: 5, right: 20, bottom: 40, left: 10 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis
            dataKey="name"
            tick={{ fontSize: 10 }}
            angle={-45}
            textAnchor="end"
            height={80}
          />
          <YAxis tick={{ fontSize: 11 }} tickFormatter={formatNumber} />
          <Tooltip
            formatter={(value) => [formatNumber(Number(value)), 'Total']}
            labelFormatter={(_, payload) => (payload?.[0]?.payload as Record<string, string>)?.fullName ?? ''}
            contentStyle={{ fontSize: 12, borderRadius: 8 }}
          />
          <Bar
            dataKey="total"
            radius={[4, 4, 0, 0]}
            cursor={onClick ? 'pointer' : undefined}
            onClick={(entry) => onClick?.((entry as unknown as Record<string, string>).fullName)}
          >
            {chartData.map((_, i) => (
              <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </Card>
  )
}
