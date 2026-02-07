import { useState, useMemo } from 'react'
import { TopBar } from '../components/layout/TopBar'
import { FilterBar } from '../components/filters/FilterBar'
import { KPIGrid } from '../components/data/KPIGrid'
import { LineChartCard } from '../components/charts/LineChartCard'
import { BarChartCard } from '../components/charts/BarChartCard'
import { DataTable } from '../components/data/DataTable'
import { Card } from '../components/ui/Card'
import { Spinner } from '../components/ui/Spinner'
import { EmptyState } from '../components/ui/EmptyState'
import { ErrorAlert } from '../components/ui/ErrorAlert'
import { useFilterOptions } from '../api/hooks/useFilters'
import {
  usePerfilKPIs,
  usePerfilTimeline,
  usePerfilPorCategoria,
  usePerfilPorModelo,
  usePerfilPorProcurador,
  usePerfilLista,
  useComparativoProcuradores,
} from '../api/hooks/usePerfil'
import { formatNumber } from '../utils/formatters'
import type { PaginationParams, ProcuradorComparativo } from '../types'

const TABELA_OPTIONS = [
  { value: 'pecas_elaboradas', label: 'Peças Elaboradas' },
  { value: 'pecas_finalizadas', label: 'Peças Finalizadas' },
  { value: 'processos_novos', label: 'Processos Novos' },
  { value: 'pendencias', label: 'Pendências' },
] as const

/** Mapa de colunas de agrupamento disponíveis por tabela. */
const TABLE_GROUPABLE: Record<string, { categoria: boolean; modelo: boolean }> = {
  pecas_elaboradas: { categoria: true, modelo: true },
  pecas_finalizadas: { categoria: true, modelo: true },
  processos_novos: { categoria: false, modelo: false },
  pendencias: { categoria: true, modelo: false },
}

const TABLE_COLUMNS: Record<string, { key: string; label: string; type?: string }[]> = {
  pecas_elaboradas: [
    { key: 'id', label: 'ID' },
    { key: 'chefia', label: 'Chefia' },
    { key: 'data', label: 'Data', type: 'datetime' },
    { key: 'usuario_criacao', label: 'Usuário de Criação' },
    { key: 'categoria', label: 'Categoria' },
    { key: 'numero_formatado', label: 'Nº Formatado' },
  ],
  pecas_finalizadas: [
    { key: 'id', label: 'ID' },
    { key: 'chefia', label: 'Chefia' },
    { key: 'data_finalizacao', label: 'Data', type: 'datetime' },
    { key: 'usuario_finalizacao', label: 'Usuário de Finalização' },
    { key: 'categoria', label: 'Categoria' },
    { key: 'numero_formatado', label: 'Nº Formatado' },
  ],
  processos_novos: [
    { key: 'id', label: 'ID' },
    { key: 'chefia', label: 'Chefia' },
    { key: 'data', label: 'Data', type: 'datetime' },
    { key: 'codigo_processo', label: 'Código' },
    { key: 'numero_formatado', label: 'Nº Formatado' },
  ],
  pendencias: [
    { key: 'id', label: 'ID' },
    { key: 'chefia', label: 'Chefia' },
    { key: 'data', label: 'Data', type: 'datetime' },
    { key: 'area', label: 'Área' },
    { key: 'categoria', label: 'Categoria' },
    { key: 'numero_formatado', label: 'Nº Formatado' },
  ],
}

// --- Comparativo entre Procuradores ---

type SortKey = keyof Pick<ProcuradorComparativo, 'procurador' | 'pecas_elaboradas' | 'pecas_finalizadas' | 'processos_novos' | 'pendencias' | 'total'>

const METRIC_COLS: { key: SortKey; label: string; short: string; color: string }[] = [
  { key: 'pecas_elaboradas', label: 'Peças Elaboradas', short: 'Elab.', color: '#1B3A5C' },
  { key: 'pecas_finalizadas', label: 'Peças Finalizadas', short: 'Final.', color: '#2E7D32' },
  { key: 'processos_novos', label: 'Processos Novos', short: 'Proc.', color: '#D4A843' },
  { key: 'pendencias', label: 'Pendências', short: 'Pend.', color: '#C62828' },
  { key: 'total', label: 'Total', short: 'Total', color: '#1565C0' },
]

function ComparativoProcuradoresCard({
  data,
  isLoading,
  isError,
}: {
  data: ProcuradorComparativo[] | undefined
  isLoading: boolean
  isError: boolean
}) {
  const [sortKey, setSortKey] = useState<SortKey>('total')
  const [sortAsc, setSortAsc] = useState(false)

  const sorted = useMemo(() => {
    if (!data) return []
    return [...data].sort((a, b) => {
      const av = a[sortKey]
      const bv = b[sortKey]
      if (typeof av === 'string' && typeof bv === 'string') {
        return sortAsc ? av.localeCompare(bv) : bv.localeCompare(av)
      }
      return sortAsc ? (av as number) - (bv as number) : (bv as number) - (av as number)
    })
  }, [data, sortKey, sortAsc])

  // Máximo de cada coluna para barras proporcionais
  const maxByCol = useMemo(() => {
    const m: Record<string, number> = {}
    for (const col of METRIC_COLS) {
      m[col.key] = Math.max(1, ...sorted.map((r) => r[col.key] as number))
    }
    return m
  }, [sorted])

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortAsc(!sortAsc)
    } else {
      setSortKey(key)
      setSortAsc(key === 'procurador')
    }
  }

  const sortIcon = (key: SortKey) => {
    if (sortKey !== key) return ''
    return sortAsc ? ' \u25B2' : ' \u25BC'
  }

  if (isLoading) return <Card title="Comparativo entre Procuradores"><Spinner /></Card>
  if (isError) return <Card title="Comparativo entre Procuradores"><ErrorAlert /></Card>
  if (!sorted.length) return <Card title="Comparativo entre Procuradores"><EmptyState /></Card>

  return (
    <Card title={`Comparativo entre Procuradores (${sorted.length})`}>
      <div className="overflow-auto max-h-[50vh]">
        <table className="w-full text-sm">
          <thead className="sticky top-0 bg-white z-10 border-b border-gray-200">
            <tr>
              <th
                onClick={() => handleSort('procurador')}
                className="cursor-pointer whitespace-nowrap px-3 py-2.5 text-left text-xs font-semibold uppercase text-gray-500 hover:text-gray-800 select-none"
              >
                Procurador{sortIcon('procurador')}
              </th>
              {METRIC_COLS.map((col) => (
                <th
                  key={col.key}
                  onClick={() => handleSort(col.key)}
                  className="cursor-pointer whitespace-nowrap px-3 py-2.5 text-right text-xs font-semibold uppercase text-gray-500 hover:text-gray-800 select-none"
                  title={col.label}
                >
                  {col.short}{sortIcon(col.key)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {sorted.map((row) => (
              <tr key={row.procurador} className="hover:bg-gray-50/60 transition-colors">
                <td className="px-3 py-2 text-[13px] font-medium text-gray-800 max-w-[200px] truncate" title={row.procurador}>
                  {row.procurador}
                </td>
                {METRIC_COLS.map((col) => {
                  const val = row[col.key] as number
                  const pct = (val / maxByCol[col.key]) * 100
                  return (
                    <td key={col.key} className="px-3 py-2 text-right">
                      <div className="flex flex-col items-end gap-0.5">
                        <span className={`text-[13px] tabular-nums ${col.key === 'total' ? 'font-bold text-gray-900' : 'font-medium text-gray-700'}`}>
                          {formatNumber(val)}
                        </span>
                        <div className="h-1 w-16 rounded-full bg-gray-100 overflow-hidden">
                          <div
                            className="h-full rounded-full transition-all duration-300"
                            style={{ width: `${pct}%`, backgroundColor: col.color }}
                          />
                        </div>
                      </div>
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  )
}

interface PerfilPageProps {
  title: string
  dimensao: 'procurador' | 'chefia' | 'assessor'
  placeholder: string
  /** Lista customizada de opções para o autocomplete (ex: assessores). */
  options?: string[]
  /** Quando true, exibe ranking "Por Procurador" no detalhamento. */
  showProcuradorChart?: boolean
  /** Quando true, exibe comparativo entre procuradores da chefia. */
  showComparativoProcuradores?: boolean
}

export function PerfilPage({ title, dimensao, placeholder, options: customOptions, showProcuradorChart, showComparativoProcuradores }: PerfilPageProps) {
  const [valor, setValor] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [tabela, setTabela] = useState('pecas_elaboradas')
  const [pagination, setPagination] = useState<PaginationParams>({
    page: 1,
    page_size: 25,
    sort_order: 'desc',
  })

  const filterOptions = useFilterOptions()
  const defaultOptions = dimensao === 'procurador'
    ? filterOptions.data?.procuradores ?? []
    : filterOptions.data?.chefias ?? []
  const options = customOptions ?? defaultOptions

  const filtered = useMemo(() => {
    if (!search) return options.slice(0, 20)
    const term = search.toLowerCase()
    return options.filter((o) => o.toLowerCase().includes(term)).slice(0, 20)
  }, [options, search])

  const groupable = TABLE_GROUPABLE[tabela] ?? { categoria: false, modelo: false }

  const kpis = usePerfilKPIs(dimensao, valor)
  const timeline = usePerfilTimeline(dimensao, valor)
  const categorias = usePerfilPorCategoria(dimensao, valor, groupable.categoria ? tabela : null)
  const modelos = usePerfilPorModelo(dimensao, valor, groupable.modelo ? tabela : null)
  const procuradores = usePerfilPorProcurador(
    dimensao, valor, showProcuradorChart ? tabela : null
  )
  const comparativo = useComparativoProcuradores(
    showComparativoProcuradores ? valor : null
  )
  const lista = usePerfilLista(dimensao, valor, tabela, pagination)

  const tabelaLabel = TABELA_OPTIONS.find((t) => t.value === tabela)?.label ?? tabela

  return (
    <>
      <TopBar title={title} />
      <FilterBar />
      <div className="space-y-6 p-6">
        {/* Seletor de indivíduo */}
        <div className="rounded-xl bg-surface shadow-sm border border-gray-100 p-5">
          <label className="block text-sm font-semibold text-gray-700 mb-2">
            {placeholder}
          </label>
          <div className="relative">
            <input
              type="text"
              value={valor ?? search}
              onChange={(e) => {
                setSearch(e.target.value)
                if (valor) setValor(null)
              }}
              placeholder={`Digite para buscar...`}
              className="w-full rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm text-gray-900 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
            {!valor && search && filtered.length > 0 && (
              <ul className="absolute z-20 mt-1 max-h-60 w-full overflow-auto rounded-lg border border-gray-200 bg-white shadow-lg">
                {filtered.map((opt) => (
                  <li key={opt}>
                    <button
                      type="button"
                      onClick={() => {
                        setValor(opt)
                        setSearch('')
                        setPagination((p) => ({ ...p, page: 1 }))
                      }}
                      className="w-full px-4 py-2 text-left text-sm text-gray-700 hover:bg-blue-50 hover:text-blue-700"
                    >
                      {opt}
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
          {valor && (
            <button
              onClick={() => { setValor(null); setSearch('') }}
              className="mt-2 text-xs text-blue-600 hover:underline"
            >
              Limpar seleção
            </button>
          )}
        </div>

        {!valor && (
          <div className="rounded-xl bg-gray-50 border border-dashed border-gray-300 p-12 text-center">
            <p className="text-gray-500 text-sm">
              Selecione {dimensao === 'procurador' ? 'um procurador' : dimensao === 'chefia' ? 'uma chefia' : 'um assessor'} acima para ver a análise completa.
            </p>
          </div>
        )}

        {valor && (
          <>
            <KPIGrid data={kpis.data} isLoading={kpis.isLoading} isError={kpis.isError} />

            <LineChartCard
              title="Evolução Mensal"
              series={timeline.data}
              isLoading={timeline.isLoading}
              isError={timeline.isError}
            />

            {showComparativoProcuradores && (
              <ComparativoProcuradoresCard
                data={comparativo.data}
                isLoading={comparativo.isLoading}
                isError={comparativo.isError}
              />
            )}

            {/* Seletor de tabela para detalhamento */}
            <div className="rounded-xl bg-surface shadow-sm border border-gray-100 px-5 py-3">
              <div className="flex flex-wrap items-center gap-3">
                <span className="text-sm font-semibold text-gray-700">Detalhar:</span>
                {TABELA_OPTIONS.map((opt) => (
                  <button
                    key={opt.value}
                    onClick={() => {
                      setTabela(opt.value)
                      setPagination((p) => ({ ...p, page: 1 }))
                    }}
                    className={`rounded-lg px-4 py-1.5 text-sm transition-colors ${
                      tabela === opt.value
                        ? 'bg-primary text-white font-medium shadow-sm'
                        : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                    }`}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            </div>

            {(groupable.categoria || groupable.modelo || showProcuradorChart) && (
              <div className={`grid grid-cols-1 gap-6 ${(groupable.categoria && groupable.modelo) || (groupable.categoria && showProcuradorChart) || (groupable.modelo && showProcuradorChart) ? 'xl:grid-cols-2' : ''}`}>
                {groupable.categoria && (
                  <BarChartCard
                    title={`${tabelaLabel} — Por Categoria`}
                    data={categorias.data}
                    isLoading={categorias.isLoading}
                    isError={categorias.isError}
                  />
                )}
                {groupable.modelo && (
                  <BarChartCard
                    title={`${tabelaLabel} — Por Modelo`}
                    data={modelos.data}
                    isLoading={modelos.isLoading}
                    isError={modelos.isError}
                  />
                )}
                {showProcuradorChart && (
                  <BarChartCard
                    title={`${tabelaLabel} — Por Procurador`}
                    data={procuradores.data}
                    isLoading={procuradores.isLoading}
                    isError={procuradores.isError}
                  />
                )}
              </div>
            )}

            <DataTable
              data={lista.data}
              columns={TABLE_COLUMNS[tabela] ?? TABLE_COLUMNS.pecas_elaboradas}
              isLoading={lista.isLoading}
              isError={lista.isError}
              pagination={pagination}
              onPaginationChange={(p) => setPagination((prev) => ({ ...prev, ...p }))}
              exportTable={tabela}
            />
          </>
        )}
      </div>
    </>
  )
}
