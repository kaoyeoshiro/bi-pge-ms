import { formatKPI } from '../../utils/formatters'

interface KPICardProps {
  label: string
  valor: number
  formato?: string
  variacao?: number | null
}

export function KPICard({ label, valor, formato, variacao }: KPICardProps) {
  const displayValue = formatKPI(valor, formato)

  return (
    <div className="rounded-xl border border-gray-100 bg-surface p-3 shadow-sm sm:p-5">
      <p className="text-[10px] font-medium text-gray-500 uppercase tracking-wide sm:text-xs">{label}</p>
      <p className="mt-1 text-xl font-bold text-primary sm:mt-2 sm:text-2xl">{displayValue}</p>
      {variacao !== null && variacao !== undefined && (
        <p className={`mt-1 text-xs font-medium ${variacao >= 0 ? 'text-secondary' : 'text-danger'}`}>
          {variacao >= 0 ? '+' : ''}{variacao.toLocaleString('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 })}% vs período anterior
        </p>
      )}
    </div>
  )
}
