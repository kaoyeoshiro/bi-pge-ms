import { useFilterParams } from '../../api/hooks/useFilterParams'
import { buildQueryString } from '../../api/client'

interface ExportButtonProps {
  table: string
}

export function ExportButton({ table }: ExportButtonProps) {
  const params = useFilterParams()

  const download = (format: 'csv' | 'excel') => {
    const qs = buildQueryString(params)
    window.open(`/api/export/${table}/${format}${qs}`, '_blank')
  }

  return (
    <div className="flex items-center gap-1">
      <button
        onClick={() => download('csv')}
        className="rounded border border-gray-300 px-2 py-1 text-xs text-gray-600 hover:bg-gray-50 transition-colors"
      >
        CSV
      </button>
      <button
        onClick={() => download('excel')}
        className="rounded border border-gray-300 px-2 py-1 text-xs text-gray-600 hover:bg-gray-50 transition-colors"
      >
        Excel
      </button>
    </div>
  )
}
