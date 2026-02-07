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

interface BarChartCardProps {
  title: string
  data: GroupCount[] | undefined
  isLoading: boolean
  isError: boolean
  layout?: 'horizontal' | 'vertical'
  onClick?: (grupo: string) => void
}

export function BarChartCard({
  title,
  data,
  isLoading,
  isError,
  layout = 'horizontal',
  onClick,
}: BarChartCardProps) {
  if (isLoading) return <Card title={title}><Spinner /></Card>
  if (isError) return <Card title={title}><ErrorAlert /></Card>
  if (!data?.length) return <Card title={title}><EmptyState /></Card>

  if (layout === 'horizontal') {
    return <HorizontalBars title={title} data={data} onClick={onClick} />
  }

  return <VerticalBars title={title} data={data} onClick={onClick} />
}

/** Barras horizontais com nomes completos — HTML/CSS puro. */
function HorizontalBars({
  title,
  data,
  onClick,
}: {
  title: string
  data: GroupCount[]
  onClick?: (grupo: string) => void
}) {
  const maxTotal = Math.max(...data.map((d) => d.total))

  return (
    <Card title={title}>
      <div className="space-y-3">
        {data.map((d, i) => (
          <div
            key={d.grupo}
            className={onClick ? 'cursor-pointer group' : 'group'}
            onClick={() => onClick?.(d.grupo)}
          >
            <div className="flex items-baseline justify-between gap-4 mb-1">
              <span className="text-[13px] leading-tight text-gray-700 group-hover:text-gray-900 transition-colors">
                {d.grupo}
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
