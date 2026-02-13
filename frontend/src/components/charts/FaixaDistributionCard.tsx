import { Card } from '../ui/Card'
import { Spinner } from '../ui/Spinner'
import { EmptyState } from '../ui/EmptyState'
import { ErrorAlert } from '../ui/ErrorAlert'
import { CHART_COLORS } from '../../utils/colors'
import { formatNumber, formatCurrency } from '../../utils/formatters'
import type { ValorFaixaItem } from '../../types'

interface FaixaDistributionCardProps {
  data: ValorFaixaItem[] | undefined
  isLoading: boolean
  isError: boolean
}

export function FaixaDistributionCard({ data, isLoading, isError }: FaixaDistributionCardProps) {
  if (isLoading) return <Card title="Distribuição por Faixa de Valor"><Spinner /></Card>
  if (isError) return <Card title="Distribuição por Faixa de Valor"><ErrorAlert /></Card>
  if (!data?.length) return <Card title="Distribuição por Faixa de Valor"><EmptyState /></Card>

  const maxQtd = Math.max(...data.map((d) => d.qtd))

  return (
    <Card title="Distribuição por Faixa de Valor">
      <div className="space-y-3">
        {data.map((d, i) => (
          <div key={d.faixa}>
            <div className="flex items-baseline justify-between gap-2 mb-1">
              <span className="text-[13px] leading-tight text-gray-700 font-medium">
                {d.faixa}
              </span>
              <div className="flex items-baseline gap-3 shrink-0">
                <span className="text-[12px] text-gray-500 tabular-nums">
                  {formatCurrency(d.valor_total)}
                </span>
                <span className="text-[13px] font-semibold text-gray-900 tabular-nums">
                  {formatNumber(d.qtd)}
                  <span className="ml-1 text-[11px] font-normal text-gray-400">
                    ({d.percentual.toFixed(1)}%)
                  </span>
                </span>
              </div>
            </div>
            <div className="h-5 w-full rounded bg-gray-100">
              <div
                className="h-full rounded transition-all duration-300"
                style={{
                  width: `${(d.qtd / maxQtd) * 100}%`,
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
