import type { KPIValue } from '../../types'
import { KPICard } from './KPICard'
import { Spinner } from '../ui/Spinner'
import { ErrorAlert } from '../ui/ErrorAlert'

interface KPIGridProps {
  data: KPIValue[] | undefined
  isLoading: boolean
  isError: boolean
}

export function KPIGrid({ data, isLoading, isError }: KPIGridProps) {
  if (isLoading) return <Spinner />
  if (isError) return <ErrorAlert />
  if (!data?.length) return null

  return (
    <div className={`grid grid-cols-2 gap-4 ${data.length <= 4 ? 'lg:grid-cols-4' : 'lg:grid-cols-5'}`}>
      {data.map((kpi) => (
        <KPICard
          key={kpi.label}
          label={kpi.label}
          valor={kpi.valor}
          formato={kpi.formato}
          variacao={kpi.variacao_percentual}
        />
      ))}
    </div>
  )
}
