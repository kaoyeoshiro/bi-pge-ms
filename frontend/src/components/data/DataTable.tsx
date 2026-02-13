import { useState } from 'react'
import type { PaginatedResponse, PaginationParams } from '../../types'
import { Spinner } from '../ui/Spinner'
import { EmptyState } from '../ui/EmptyState'
import { ErrorAlert } from '../ui/ErrorAlert'
import { formatCurrency, formatDateTime } from '../../utils/formatters'
import { ExportButton } from './ExportButton'

interface DataTableProps {
  data: PaginatedResponse | undefined
  columns: Array<{ key: string; label: string; type?: string }>
  isLoading: boolean
  isError: boolean
  pagination: PaginationParams
  onPaginationChange: (params: Partial<PaginationParams>) => void
  exportTable?: string
}

export function DataTable({
  data,
  columns,
  isLoading,
  isError,
  pagination,
  onPaginationChange,
  exportTable,
}: DataTableProps) {
  const [searchInput, setSearchInput] = useState(pagination.search ?? '')

  const handleSearch = () => {
    onPaginationChange({ search: searchInput || undefined, page: 1 })
  }

  const handleSort = (column: string) => {
    if (pagination.sort_by === column) {
      onPaginationChange({
        sort_order: pagination.sort_order === 'asc' ? 'desc' : 'asc',
      })
    } else {
      onPaginationChange({ sort_by: column, sort_order: 'desc' })
    }
  }

  if (isError) return <ErrorAlert />

  return (
    <div className="rounded-xl border border-gray-100 bg-surface shadow-sm">
      <div className="flex flex-wrap items-center gap-2 border-b border-gray-100 px-3 py-2 sm:gap-3 sm:px-5 sm:py-3">
        <div className="relative min-w-0 flex-1">
          <input
            type="text"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            placeholder="Buscar..."
            className="w-full rounded-lg border border-gray-300 px-3 py-1.5 text-sm focus:border-primary focus:outline-none sm:max-w-sm"
          />
        </div>
        <button
          onClick={handleSearch}
          className="rounded-lg bg-primary px-3 py-1.5 text-xs font-medium text-white hover:bg-primary-light transition-colors"
        >
          Buscar
        </button>
        {exportTable && <ExportButton table={exportTable} />}
      </div>

      {isLoading ? (
        <Spinner />
      ) : !data?.items.length ? (
        <EmptyState />
      ) : (
        <>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-gray-100 bg-gray-50/50">
                <tr>
                  {columns.map((col) => (
                    <th
                      key={col.key}
                      onClick={() => handleSort(col.key)}
                      className="cursor-pointer whitespace-nowrap px-4 py-2.5 text-xs font-semibold text-gray-500 uppercase tracking-wide hover:text-primary transition-colors"
                    >
                      {col.label}
                      {pagination.sort_by === col.key && (
                        <span className="ml-1">
                          {pagination.sort_order === 'asc' ? ' \u2191' : ' \u2193'}
                        </span>
                      )}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {data.items.map((row, i) => (
                  <tr key={i} className="hover:bg-gray-50/50 transition-colors">
                    {columns.map((col) => (
                      <td key={col.key} className="whitespace-nowrap px-4 py-2.5 text-sm text-gray-700">
                        {col.type === 'datetime'
                          ? formatDateTime(row[col.key] as string)
                          : col.type === 'currency'
                            ? row[col.key] != null
                              ? formatCurrency(row[col.key] as number)
                              : '-'
                            : String(row[col.key] ?? '')}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-2 border-t border-gray-100 px-3 py-2 sm:px-5 sm:py-3">
            <p className="text-xs text-gray-500">
              {data.total.toLocaleString('pt-BR')} registros | Pág. {data.page}/{data.total_pages}
            </p>
            <div className="flex items-center gap-2">
              <button
                disabled={data.page <= 1}
                onClick={() => onPaginationChange({ page: data.page - 1 })}
                className="rounded border border-gray-300 px-3 py-1 text-xs text-gray-600 hover:bg-gray-50 disabled:opacity-40 transition-colors"
              >
                Anterior
              </button>
              <button
                disabled={data.page >= data.total_pages}
                onClick={() => onPaginationChange({ page: data.page + 1 })}
                className="rounded border border-gray-300 px-3 py-1 text-xs text-gray-600 hover:bg-gray-50 disabled:opacity-40 transition-colors"
              >
                Próxima
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
