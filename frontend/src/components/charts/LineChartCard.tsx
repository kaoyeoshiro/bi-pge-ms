import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'
import { Card } from '../ui/Card'
import { Spinner } from '../ui/Spinner'
import { EmptyState } from '../ui/EmptyState'
import { ErrorAlert } from '../ui/ErrorAlert'
import { CHART_COLORS } from '../../utils/colors'
import { formatPeriod, formatNumber } from '../../utils/formatters'
import type { TimelineSeries } from '../../types'

interface LineChartCardProps {
  title: string
  series: TimelineSeries[] | undefined
  isLoading: boolean
  isError: boolean
}

export function LineChartCard({ title, series, isLoading, isError }: LineChartCardProps) {
  if (isLoading) return <Card title={title}><Spinner /></Card>
  if (isError) return <Card title={title}><ErrorAlert /></Card>
  if (!series?.length || !series.some((s) => s.dados.length > 0))
    return <Card title={title}><EmptyState /></Card>

  // Monta dados consolidados por período
  const periodMap = new Map<string, Record<string, number>>()
  for (const s of series) {
    for (const p of s.dados) {
      const existing = periodMap.get(p.periodo) ?? {}
      existing[s.nome] = p.valor
      periodMap.set(p.periodo, existing)
    }
  }

  const chartData = Array.from(periodMap.entries())
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([periodo, values]) => ({ periodo, ...values }))

  return (
    <Card title={title}>
      <ResponsiveContainer width="100%" height={320}>
        <LineChart data={chartData} margin={{ top: 5, right: 20, bottom: 5, left: 10 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis
            dataKey="periodo"
            tickFormatter={formatPeriod}
            tick={{ fontSize: 11 }}
            interval="preserveStartEnd"
          />
          <YAxis tick={{ fontSize: 11 }} tickFormatter={formatNumber} />
          <Tooltip
            labelFormatter={(label) => formatPeriod(String(label))}
            formatter={(value) => [formatNumber(Number(value)), '']}
            contentStyle={{ fontSize: 12, borderRadius: 8 }}
          />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          {series.map((s, i) => (
            <Line
              key={s.nome}
              type="monotone"
              dataKey={s.nome}
              stroke={CHART_COLORS[i % CHART_COLORS.length]}
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4 }}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </Card>
  )
}
