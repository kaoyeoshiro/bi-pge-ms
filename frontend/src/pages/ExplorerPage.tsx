import { useState } from 'react'
import { TopBar } from '../components/layout/TopBar'
import { FilterBar } from '../components/filters/FilterBar'
import { DataTable } from '../components/data/DataTable'
import { useTableSchema, useTableData } from '../api/hooks/useExplorer'
import type { PaginationParams } from '../types'

const TABLES = [
  { value: 'processos_novos', label: 'Processos Novos' },
  { value: 'pecas_elaboradas', label: 'Peças Elaboradas' },
  { value: 'pendencias', label: 'Pendências' },
  { value: 'pecas_finalizadas', label: 'Peças Finalizadas' },
]

export function ExplorerPage() {
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
    <>
      <TopBar title="Explorar Dados" />
      <FilterBar />
      <div className="space-y-6 p-6">
        <div className="flex items-center gap-3">
          <span className="text-sm font-medium text-gray-600">Tabela:</span>
          <div className="flex gap-1">
            {TABLES.map((t) => (
              <button
                key={t.value}
                onClick={() => handleTableChange(t.value)}
                className={`rounded-lg px-4 py-2 text-sm transition-colors ${
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
            <span className="ml-auto text-xs text-gray-500">
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
    </>
  )
}
