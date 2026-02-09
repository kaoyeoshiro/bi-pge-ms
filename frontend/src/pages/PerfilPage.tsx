import { useState, useMemo } from 'react'
import { TopBar } from '../components/layout/TopBar'
import { PageFilterBar } from '../components/filters/PageFilterBar'
import { TreeSelectFilter } from '../components/filters/TreeSelectFilter'
import { FilterParamsProvider } from '../api/hooks/useFilterParams'
import type { FilterParams } from '../api/hooks/useFilterParams'
import { KPIGrid } from '../components/data/KPIGrid'
import { LineChartCard } from '../components/charts/LineChartCard'
import { BarChartCard } from '../components/charts/BarChartCard'
import { AssuntoDrilldownCard } from '../components/charts/AssuntoDrilldownCard'
import { DataTable } from '../components/data/DataTable'
import { Card } from '../components/ui/Card'
import { Spinner } from '../components/ui/Spinner'
import { EmptyState } from '../components/ui/EmptyState'
import { ErrorAlert } from '../components/ui/ErrorAlert'
import { SelectFilter } from '../components/filters/SelectFilter'
import { useCargaReduzida, useFilterOptions, useAssuntosTree } from '../api/hooks/useFilters'
import {
  usePerfilKPIs,
  usePerfilTimeline,
  usePerfilPorCategoria,
  usePerfilPorModelo,
  usePerfilPorProcurador,
  usePerfilLista,
  useComparativoProcuradores,
  useChefiaMedias,
} from '../api/hooks/usePerfil'
import { usePageFilters } from '../hooks/usePageFilters'
import { formatNumber, formatDecimal } from '../utils/formatters'
import type { PaginationParams, ProcuradorComparativo } from '../types'

/** Opções de tabela para detalhamento — chefia (inclui processos novos). */
const TABELA_OPTIONS_CHEFIA = [
  { value: 'pecas_finalizadas', label: 'Peças Finalizadas' },
  { value: 'processos_novos', label: 'Processos Novos' },
  { value: 'pendencias', label: 'Pendências' },
] as const

/** Opções de tabela para detalhamento — procurador (sem processos novos). */
const TABELA_OPTIONS_PROCURADOR = [
  { value: 'pecas_finalizadas', label: 'Peças Finalizadas' },
  { value: 'pendencias', label: 'Pendências' },
] as const

/** Opções de tabela para detalhamento — assessor (inclui elaboradas). */
const TABELA_OPTIONS_ASSESSOR = [
  { value: 'pecas_elaboradas', label: 'Peças Elaboradas' },
  { value: 'pecas_finalizadas', label: 'Peças Finalizadas' },
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

type SortKey = keyof Pick<ProcuradorComparativo, 'procurador' | 'pecas_finalizadas' | 'pendencias' | 'total'>

const METRIC_COLS: { key: SortKey; label: string; short: string; color: string }[] = [
  { key: 'pecas_finalizadas', label: 'Peças Finalizadas', short: 'Final.', color: '#2E7D32' },
  { key: 'pendencias', label: 'Pendências', short: 'Pend.', color: '#C62828' },
  { key: 'total', label: 'Total', short: 'Total', color: '#1565C0' },
]

function ComparativoProcuradoresCard({
  data,
  isLoading,
  isError,
  cargaReduzidaSet,
}: {
  data: ProcuradorComparativo[] | undefined
  isLoading: boolean
  isError: boolean
  cargaReduzidaSet?: Set<string>
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
      <p className="text-xs text-gray-400 mb-3 -mt-1">Métricas de procurador: peças finalizadas e pendências atribuídas ao responsável</p>
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
                  {cargaReduzidaSet?.has(row.procurador) && (
                    <span className="ml-1.5 inline-flex items-center rounded-full bg-amber-100 px-1.5 py-0.5 text-[10px] font-bold text-amber-700" title="Carga Reduzida">
                      CR
                    </span>
                  )}
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

export interface PerfilPageProps {
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

/**
 * Wrapper que isola os filtros da página do store global.
 * O FilterParamsProvider faz com que todos os hooks de API chamados
 * dentro de PerfilPageContent usem os filtros locais (ano, data).
 */
export function PerfilPage(props: PerfilPageProps) {
  const { params: baseParams, ...filterBarProps } = usePageFilters()
  const isChefia = props.dimensao === 'chefia'

  // Assunto: estado local, só relevante para chefia (processos_novos)
  const [assuntos, setAssuntos] = useState<number[]>([])
  const { data: assuntosTree } = useAssuntosTree()

  const params = useMemo(() => {
    if (!isChefia || !assuntos.length) return baseParams
    return { ...baseParams, assunto: assuntos.join(',') } as FilterParams
  }, [baseParams, isChefia, assuntos])

  // Detectar qual assunto raiz foi selecionado (para auto-drill no card)
  const selectedRootAssunto = useMemo(() => {
    if (!assuntos.length || !assuntosTree) return null
    for (const node of assuntosTree) {
      if (assuntos.includes(node.codigo)) {
        return { codigo: node.codigo, nome: node.nome }
      }
    }
    return null
  }, [assuntos, assuntosTree])

  const handleClearAll = () => {
    filterBarProps.clearAll()
    setAssuntos([])
  }

  return (
    <>
      <TopBar title={props.title} />
      <PageFilterBar {...filterBarProps} clearAll={handleClearAll} />
      {isChefia && assuntosTree && assuntosTree.length > 0 && (
        <div className="flex items-center gap-2 border-b border-gray-200 bg-surface px-3 py-2 sm:px-6 sm:py-2">
          <TreeSelectFilter
            label="Assunto"
            tree={assuntosTree}
            value={assuntos}
            onChange={setAssuntos}
          />
          {assuntos.length > 0 && (
            <button
              onClick={() => setAssuntos([])}
              className="rounded px-2 py-1 text-xs text-gray-500 hover:bg-gray-100 transition-colors"
            >
              Limpar assunto
            </button>
          )}
        </div>
      )}
      <FilterParamsProvider value={params}>
        <PerfilPageContent {...props} filterAssunto={selectedRootAssunto} />
      </FilterParamsProvider>
    </>
  )
}

/**
 * Conteúdo interno da página de perfil.
 * Todos os hooks de API aqui resolvem useFilterParams() via contexto local.
 */
function PerfilPageContent({ dimensao, placeholder, options: customOptions, showProcuradorChart, showComparativoProcuradores, filterAssunto }: PerfilPageProps & { filterAssunto?: { codigo: number; nome: string } | null }) {
  const [valor, setValor] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const tabelaOptions = dimensao === 'assessor'
    ? TABELA_OPTIONS_ASSESSOR
    : dimensao === 'chefia'
      ? TABELA_OPTIONS_CHEFIA
      : TABELA_OPTIONS_PROCURADOR
  const [tabela, setTabela] = useState<string>(tabelaOptions[0].value)
  const [pagination, setPagination] = useState<PaginationParams>({
    page: 1,
    page_size: 25,
    sort_order: 'desc',
  })

  // Estados para médias de chefia
  const [displayMode, setDisplayMode] = useState<'total' | 'average'>('total')
  const [averageUnit, setAverageUnit] = useState<'day' | 'month' | 'year'>('month')
  const [selectedProcuradores, setSelectedProcuradores] = useState<string[]>([])

  const { crSet } = useCargaReduzida()
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

  // Lista de procuradores derivada do comparativo (para filtro de médias)
  const procuradorOptions = useMemo(() => {
    if (!comparativo.data) return []
    return comparativo.data.map((c) => c.procurador).sort()
  }, [comparativo.data])

  // Hook de médias de chefia
  const chefiaMedias = useChefiaMedias(
    dimensao === 'chefia' ? valor : null,
    averageUnit,
    selectedProcuradores,
    displayMode === 'average',
  )

  const lista = usePerfilLista(dimensao, valor, tabela, pagination)

  const tabelaLabel = tabelaOptions.find((t) => t.value === tabela)?.label ?? tabela

  return (
    <div className="space-y-4 p-4 sm:space-y-6 sm:p-6">
      {/* Seletor de indivíduo */}
      <div className="rounded-xl bg-surface shadow-sm border border-gray-100 p-3 sm:p-5">
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
        <div className="rounded-xl bg-gray-50 border border-dashed border-gray-300 p-6 text-center sm:p-12">
          <p className="text-gray-500 text-sm">
            Selecione {dimensao === 'procurador' ? 'um procurador' : dimensao === 'chefia' ? 'uma chefia' : 'um assessor'} acima para ver a análise completa.
          </p>
        </div>
      )}

      {valor && (
        <>
          {/* Painel de controle: Totais vs Médias (apenas chefia) */}
          {dimensao === 'chefia' && (
            <div className="rounded-xl bg-surface shadow-sm border border-gray-100 px-3 py-2 sm:px-5 sm:py-3">
              <div className="flex flex-wrap items-center gap-3">
                <span className="text-sm font-semibold text-gray-700">Exibir como:</span>
                <button
                  onClick={() => {
                    setDisplayMode('total')
                    setSelectedProcuradores([])
                  }}
                  className={`rounded-lg px-4 py-1.5 text-sm transition-colors ${
                    displayMode === 'total'
                      ? 'bg-primary text-white font-medium shadow-sm'
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}
                >
                  Totais
                </button>
                <button
                  onClick={() => setDisplayMode('average')}
                  className={`rounded-lg px-4 py-1.5 text-sm transition-colors ${
                    displayMode === 'average'
                      ? 'bg-primary text-white font-medium shadow-sm'
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}
                >
                  Médias
                </button>

                {displayMode === 'average' && (
                  <>
                    <span className="ml-2 text-sm text-gray-500">por:</span>
                    {([['day', 'Dia'], ['month', 'Mês'], ['year', 'Ano']] as const).map(([unit, label]) => (
                      <button
                        key={unit}
                        onClick={() => setAverageUnit(unit)}
                        className={`rounded-lg px-3 py-1.5 text-sm transition-colors ${
                          averageUnit === unit
                            ? 'bg-blue-600 text-white font-medium shadow-sm'
                            : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                        }`}
                      >
                        {label}
                      </button>
                    ))}
                    {procuradorOptions.length > 0 && (
                      <div className="ml-2 flex items-center gap-1.5">
                        <SelectFilter
                          label="Procuradores"
                          options={procuradorOptions}
                          value={selectedProcuradores}
                          onChange={setSelectedProcuradores}
                          showSelectAll
                        />
                        <div className="group relative">
                          <button
                            type="button"
                            className="flex h-6 w-6 items-center justify-center rounded-full text-gray-400 hover:bg-gray-100 hover:text-gray-600 transition-colors"
                            aria-label="Informações sobre filtro de procuradores"
                          >
                            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4">
                              <path fillRule="evenodd" d="M18 10a8 8 0 1 1-16 0 8 8 0 0 1 16 0Zm-7-4a1 1 0 1 1-2 0 1 1 0 0 1 2 0ZM9 9a.75.75 0 0 0 0 1.5h.253a.25.25 0 0 1 .244.304l-.459 2.066A1.75 1.75 0 0 0 10.747 15H11a.75.75 0 0 0 0-1.5h-.253a.25.25 0 0 1-.244-.304l.459-2.066A1.75 1.75 0 0 0 9.253 9H9Z" clipRule="evenodd" />
                            </svg>
                          </button>
                          <div className="pointer-events-none absolute bottom-full left-1/2 z-30 mb-2 w-64 -translate-x-1/2 rounded-lg bg-gray-800 px-3 py-2 text-xs leading-relaxed text-white shadow-lg opacity-0 transition-opacity group-hover:opacity-100 group-focus-within:opacity-100">
                            Ao selecionar um ou mais procuradores, as médias exibidas passam a ser calculadas exclusivamente com base na produção dos selecionados, e não na produção total da chefia.
                            <div className="absolute left-1/2 top-full -translate-x-1/2 border-4 border-transparent border-t-gray-800" />
                          </div>
                        </div>
                      </div>
                    )}
                  </>
                )}
              </div>
            </div>
          )}

          {/* KPIs: totais ou médias */}
          {displayMode === 'average' && dimensao === 'chefia' ? (
            chefiaMedias.isLoading ? (
              <Spinner />
            ) : chefiaMedias.isError ? (
              <ErrorAlert />
            ) : chefiaMedias.data ? (
              <div className="grid grid-cols-2 gap-4 lg:grid-cols-3">
                {chefiaMedias.data.kpis.map((kpi) => (
                  <div key={kpi.label} className="rounded-xl border border-gray-100 bg-surface p-3 shadow-sm sm:p-5">
                    <p className="text-[10px] font-medium text-gray-500 uppercase tracking-wide sm:text-xs">{kpi.label}</p>
                    <p className="mt-1 text-xl font-bold text-primary sm:mt-2 sm:text-2xl">
                      {formatDecimal(kpi.media)}
                    </p>
                    <p className="mt-1 text-xs text-gray-400">
                      Total: {formatNumber(kpi.total)} em {chefiaMedias.data!.units_count} {chefiaMedias.data!.unit_label}
                      {chefiaMedias.data!.person_count > 1 && (
                        <span className="ml-1 text-blue-500">
                          ({chefiaMedias.data!.person_count} procuradores)
                        </span>
                      )}
                    </p>
                  </div>
                ))}
              </div>
            ) : null
          ) : (
            <KPIGrid data={kpis.data} isLoading={kpis.isLoading} isError={kpis.isError} />
          )}

          {/* Gráfico: timeline padrão ou filtrada */}
          <LineChartCard
            title="Evolução Mensal"
            series={
              displayMode === 'average' && dimensao === 'chefia' && chefiaMedias.data
                ? chefiaMedias.data.timeline
                : timeline.data
            }
            isLoading={
              displayMode === 'average' && dimensao === 'chefia'
                ? chefiaMedias.isLoading
                : timeline.isLoading
            }
            isError={
              displayMode === 'average' && dimensao === 'chefia'
                ? chefiaMedias.isError
                : timeline.isError
            }
          />

          {showComparativoProcuradores && (
            <ComparativoProcuradoresCard
              data={comparativo.data}
              isLoading={comparativo.isLoading}
              isError={comparativo.isError}
              cargaReduzidaSet={crSet}
            />
          )}

          {/* Seletor de tabela para detalhamento */}
          <div className="rounded-xl bg-surface shadow-sm border border-gray-100 px-3 py-2 sm:px-5 sm:py-3">
            <div className="flex flex-wrap items-center gap-2 sm:gap-3">
              <span className="text-sm font-semibold text-gray-700">Detalhar:</span>
              {tabelaOptions.map((opt) => (
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

          {(groupable.categoria || groupable.modelo || showProcuradorChart || dimensao === 'chefia') && (
            <div className={`grid grid-cols-1 gap-6 ${(groupable.categoria && groupable.modelo) || (groupable.categoria && showProcuradorChart) || (groupable.modelo && showProcuradorChart) || dimensao === 'chefia' ? 'xl:grid-cols-2' : ''}`}>
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
                  cargaReduzidaSet={crSet}
                />
              )}
              {dimensao === 'chefia' && (
                <AssuntoDrilldownCard
                  title={`${tabelaLabel} — Por Assunto`}
                  dimensao={dimensao}
                  valor={valor}
                  tabela={tabela}
                  filterAssunto={filterAssunto}
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
  )
}
