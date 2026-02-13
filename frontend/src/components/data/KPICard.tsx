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
    <div className="min-w-0 rounded-xl border border-gray-100 bg-surface p-3 shadow-sm sm:p-5">
      <p className="text-[10px] font-medium text-gray-500 uppercase tracking-wide sm:text-xs truncate">{label}</p>
      <p className="mt-1 text-lg font-bold text-primary sm:mt-2 sm:text-xl xl:text-2xl truncate" title={displayValue}>{displayValue}</p>
      {variacao !== null && variacao !== undefined && (
        <p className={`mt-1 text-xs font-medium ${variacao >= 0 ? 'text-secondary' : 'text-danger'}`}>
          {variacao >= 0 ? '+' : ''}{variacao.toLocaleString('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 })}% vs período anterior
        </p>
      )}
    </div>
  )
}
