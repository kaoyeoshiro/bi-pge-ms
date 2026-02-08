import { useState } from 'react'
import { TopBar } from '../components/layout/TopBar'
import { PageFilterBar } from '../components/filters/PageFilterBar'
import { FilterParamsProvider } from '../api/hooks/useFilterParams'
import { DataTable } from '../components/data/DataTable'
import { useTableSchema, useTableData } from '../api/hooks/useExplorer'
import { usePageFilters } from '../hooks/usePageFilters'
import type { PaginationParams } from '../types'

const TABLES = [
  { value: 'processos_novos', label: 'Processos Novos' },
  { value: 'pecas_elaboradas', label: 'Peças Elaboradas' },
  { value: 'pendencias', label: 'Pendências' },
  { value: 'pecas_finalizadas', label: 'Peças Finalizadas' },
]

/**
 * Wrapper que isola os filtros da página do store global.
 * O FilterParamsProvider faz com que os hooks de API usem filtros locais.
 */
export function ExplorerPage() {
  const { params, ...filterBarProps } = usePageFilters()

  return (
    <>
      <TopBar title="Explorar Dados" />
      <PageFilterBar {...filterBarProps} />
      <FilterParamsProvider value={params}>
        <ExplorerPageContent />
      </FilterParamsProvider>
    </>
  )
}

/**
 * Conteúdo interno da página de exploração.
 * Os hooks de API resolvem useFilterParams() via contexto local.
 */
function ExplorerPageContent() {
  const [selectedTable, setSelectedTable] = useState('processos_novos')
  const [pagination, setPagination] = useState<PaginationParams>({
    page: 1,
    page_size: 25,
    sort_order: 'desc',
  })

  const schema = useTableSchema(selectedTable)
  const tableData = useTableData(selectedTable, pagination)

  const columns = schema.data?.columns.map((col) => ({
    key: col.name,
    label: col.label,
    type: col.type === 'datetime' ? 'datetime' : undefined,
  })) ?? []

  const handleTableChange = (table: string) => {
    setSelectedTable(table)
    setPagination({ page: 1, page_size: 25, sort_order: 'desc' })
  }

  return (
    <div className="space-y-4 p-4 sm:space-y-6 sm:p-6">
      <div className="flex flex-wrap items-center gap-2 sm:gap-3">
        <span className="text-sm font-medium text-gray-600">Tabela:</span>
        <div className="flex flex-wrap gap-1">
          {TABLES.map((t) => (
            <button
              key={t.value}
              onClick={() => handleTableChange(t.value)}
              className={`rounded-lg px-3 py-1.5 text-xs transition-colors sm:px-4 sm:py-2 sm:text-sm ${
                selectedTable === t.value
                  ? 'bg-primary text-white font-medium'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
        {schema.data && (
          <span className="w-full text-xs text-gray-500 sm:ml-auto sm:w-auto">
            {schema.data.total_rows.toLocaleString('pt-BR')} registros totais
          </span>
        )}
      </div>

      <DataTable
        data={tableData.data}
        columns={columns}
        isLoading={tableData.isLoading}
        isError={tableData.isError}
        pagination={pagination}
        onPaginationChange={(p) => setPagination((prev) => ({ ...prev, ...p }))}
        exportTable={selectedTable}
      />
    </div>
  )
}
