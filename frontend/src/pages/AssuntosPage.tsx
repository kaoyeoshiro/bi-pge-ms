import { useState, useMemo, useEffect } from 'react'
import { TopBar } from '../components/layout/TopBar'
import { SelectFilter } from '../components/filters/SelectFilter'
import { AssuntoAutocomplete } from '../components/filters/AssuntoAutocomplete'
import { FilterParamsProvider, type FilterParams } from '../api/hooks/useFilterParams'
import { usePageFilters } from '../hooks/usePageFilters'
import { useFilterOptions } from '../api/hooks/useFilters'
import { useAssuntoDrillDown, useAssuntoResumo, useAssuntoLista } from '../api/hooks/useAssuntoExplorer'
import { DataTable } from '../components/data/DataTable'
import { KPIGrid } from '../components/data/KPIGrid'
import { BarChartCard } from '../components/charts/BarChartCard'
import { LineChartCard } from '../components/charts/LineChartCard'
import { Spinner } from '../components/ui/Spinner'
import { EmptyState } from '../components/ui/EmptyState'
import { ErrorAlert } from '../components/ui/ErrorAlert'
import { CHART_COLORS } from '../utils/colors'
import { formatNumber } from '../utils/formatters'
import type { AssuntoNode, PaginationParams } from '../types'

const TABLE_COLUMNS = [
  { key: 'id', label: 'ID' },
  { key: 'chefia', label: 'Chefia' },
  { key: 'data', label: 'Data', type: 'datetime' },
  { key: 'numero_formatado', label: 'N\u00ba Formatado' },
  { key: 'procurador', label: 'Procurador' },
]

interface BreadcrumbItem {
  codigo: number
  nome: string
}

/** Página dedicada para exploração da árvore de assuntos. */
export function AssuntosPage() {
  const { params: baseParams, ...filterBarProps } = usePageFilters()
  const { data: options } = useFilterOptions()

  // Filtros locais adicionais
  const [chefias, setChefias] = useState<string[]>([])
  const [assuntosSelecionados, setAssuntosSelecionados] = useState<AssuntoNode[]>([])

  const params = useMemo(() => {
    const p: FilterParams = { ...baseParams }
    if (chefias.length) p.chefia = chefias
    if (assuntosSelecionados.length) {
      p.assunto = assuntosSelecionados.map((a) => String(a.codigo)).join(',')
    }
    return p
  }, [baseParams, chefias, assuntosSelecionados])

  const clearAll = () => {
    filterBarProps.clearAll()
    setChefias([])
    setAssuntosSelecionados([])
  }

  return (
    <>
      <TopBar title="Explorar Assuntos" />
      <div className="sticky top-14 z-10 border-b border-gray-200 bg-surface">
        {/* Primeira linha: filtros normais */}
        <div className="flex flex-wrap items-center gap-2 px-3 py-2 sm:gap-3 sm:px-6 sm:py-3">
          <SelectFilter
            label="Ano"
            options={options?.anos.map(String) ?? []}
            value={filterBarProps.anos.map(String)}
            onChange={(v) => filterBarProps.setAnos(v.map(Number))}
            showSelectAll
          />
          <SelectFilter
            label="Chefia"
            options={options?.chefias ?? []}
            value={chefias}
            onChange={setChefias}
          />
          <div className="flex w-full items-center gap-2 sm:ml-auto sm:w-auto">
            <input
              type="date"
              value={filterBarProps.dataInicio ?? ''}
              onChange={(e) => filterBarProps.setDataInicio(e.target.value || null)}
              className="min-w-0 flex-1 rounded border border-gray-300 px-2 py-1 text-xs focus:border-primary focus:outline-none sm:flex-none"
              placeholder="Data início"
            />
            <span className="text-xs text-gray-400">a</span>
            <input
              type="date"
              value={filterBarProps.dataFim ?? ''}
              onChange={(e) => filterBarProps.setDataFim(e.target.value || null)}
              className="min-w-0 flex-1 rounded border border-gray-300 px-2 py-1 text-xs focus:border-primary focus:outline-none sm:flex-none"
              placeholder="Data fim"
            />
          </div>
          {(filterBarProps.anos.length > 0 || filterBarProps.dataInicio || filterBarProps.dataFim || chefias.length > 0 || assuntosSelecionados.length > 0) && (
            <button
              onClick={clearAll}
              className="rounded px-3 py-1 text-xs text-gray-500 hover:bg-gray-100 transition-colors"
            >
              Limpar filtros
            </button>
          )}
        </div>

        {/* Segunda linha: busca de assuntos */}
        <div className="border-t border-gray-100 px-3 py-3 sm:px-6">
          <div className="max-w-2xl">
            <label className="mb-1.5 block text-xs font-medium text-gray-700">
              Filtrar por assuntos específicos
            </label>
            <AssuntoAutocomplete
              value={assuntosSelecionados}
              onChange={setAssuntosSelecionados}
              placeholder="Buscar e selecionar assuntos..."
            />
          </div>
        </div>
      </div>

      <FilterParamsProvider value={params}>
        <AssuntosContent assuntosSelecionados={assuntosSelecionados} />
      </FilterParamsProvider>
    </>
  )
}

/** Conteúdo principal: drill-down + painel de detalhes + lista de processos. */
function AssuntosContent({ assuntosSelecionados }: { assuntosSelecionados: AssuntoNode[] }) {
  const [path, setPath] = useState<BreadcrumbItem[]>([])
  const [pagination, setPagination] = useState<PaginationParams>({
    page: 1,
    page_size: 25,
    sort_order: 'desc',
  })

  const currentCodigo = path.length > 0 ? path[path.length - 1].codigo : null

  // Limpa path quando assuntos são selecionados via busca
  useEffect(() => {
    if (assuntosSelecionados.length > 0) {
      setPath([])
    }
  }, [assuntosSelecionados])

  // Reseta paginação quando filtros mudam
  useEffect(() => {
    setPagination((prev) => ({ ...prev, page: 1 }))
  }, [assuntosSelecionados, currentCodigo])

  // Códigos para a lista de processos (autocomplete ou drill-down)
  const listaCodigos = useMemo(() => {
    if (assuntosSelecionados.length > 0) {
      return assuntosSelecionados.map((a) => a.codigo)
    }
    if (currentCodigo !== null) {
      return [currentCodigo]
    }
    return []
  }, [assuntosSelecionados, currentCodigo])

  const {
    data: drillData,
    isLoading: drillLoading,
    isError: drillError,
  } = useAssuntoDrillDown(currentCodigo)

  // Código para resumo: drill-down ativo OU exatamente 1 assunto selecionado
  const resumoCodigo = currentCodigo
    ?? (assuntosSelecionados.length === 1 ? assuntosSelecionados[0].codigo : null)

  const {
    data: resumo,
    isLoading: resumoLoading,
    isError: resumoError,
  } = useAssuntoResumo(resumoCodigo)

  const lista = useAssuntoLista(listaCodigos, pagination)

  const somaTotal = useMemo(
    () => drillData?.reduce((acc, d) => acc + d.total, 0) ?? 0,
    [drillData],
  )

  function handleDrillDown(codigo: number, nome: string) {
    setPath((prev) => [...prev, { codigo, nome }])
  }

  function handleBreadcrumb(index: number) {
    if (index < 0) {
      setPath([])
    } else {
      setPath((prev) => prev.slice(0, index + 1))
    }
  }

  function handleBack() {
    setPath((prev) => prev.slice(0, -1))
  }

  return (
    <div className="space-y-6 p-4 sm:p-6">
      {/* Info sobre filtros ativos */}
      {assuntosSelecionados.length > 0 && (
        <div className="rounded-lg bg-blue-50 p-4">
          <div className="flex items-start gap-2">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 20 20"
              fill="currentColor"
              className="h-5 w-5 shrink-0 text-blue-600"
            >
              <path
                fillRule="evenodd"
                d="M18 10a8 8 0 1 1-16 0 8 8 0 0 1 16 0Zm-7-4a1 1 0 1 1-2 0 1 1 0 0 1 2 0ZM9 9a.75.75 0 0 0 0 1.5h.253a.25.25 0 0 1 .244.304l-.459 2.066A1.75 1.75 0 0 0 10.747 15H11a.75.75 0 0 0 0-1.5h-.253a.25.25 0 0 1-.244-.304l.459-2.066A1.75 1.75 0 0 0 9.253 9H9Z"
                clipRule="evenodd"
              />
            </svg>
            <div className="flex-1">
              <p className="text-sm font-medium text-blue-900">
                Filtro de assuntos ativo
              </p>
              <p className="mt-1 text-xs text-blue-700">
                Mostrando dados apenas dos assuntos selecionados. O drill-down manual está
                desabilitado enquanto houver assuntos filtrados.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Breadcrumb (só aparece no drill-down manual) */}
      {path.length > 0 && assuntosSelecionados.length === 0 && (
        <Breadcrumb path={path} onNavigate={handleBreadcrumb} onBack={handleBack} />
      )}

      {/* Barras de navegação (drill-down manual desabilitado se há filtro de assuntos) */}
      <DrillDownBars
        data={drillData}
        isLoading={drillLoading}
        isError={drillError}
        somaTotal={somaTotal}
        onDrillDown={handleDrillDown}
        disabled={assuntosSelecionados.length > 0}
      />

      {/* Painel de detalhes (drill-down ou assunto selecionado) */}
      {resumoCodigo !== null && (
        <div className="space-y-6">
          <KPIGrid
            data={resumo?.kpis}
            isLoading={resumoLoading}
            isError={resumoError}
          />

          <div className="grid gap-6 lg:grid-cols-2">
            <BarChartCard
              title="Subassuntos"
              data={resumo?.top_filhos}
              isLoading={resumoLoading}
              isError={resumoError}
            />
            <LineChartCard
              title="Evolução Mensal por Subassunto"
              series={resumo?.timeline}
              isLoading={resumoLoading}
              isError={resumoError}
            />
          </div>
        </div>
      )}

      {/* Lista de processos (quando há assuntos selecionados ou drill-down ativo) */}
      {listaCodigos.length > 0 && (
        <DataTable
          data={lista.data}
          columns={TABLE_COLUMNS}
          isLoading={lista.isLoading}
          isError={lista.isError}
          pagination={pagination}
          onPaginationChange={(p) => setPagination((prev) => ({ ...prev, ...p }))}
          exportTable="processos_novos"
        />
      )}
    </div>
  )
}

/** Barras horizontais de drill-down com percentual e cores. */
function DrillDownBars({
  data,
  isLoading,
  isError,
  somaTotal,
  onDrillDown,
  disabled = false,
}: {
  data: import('../types').AssuntoGroupCount[] | undefined
  isLoading: boolean
  isError: boolean
  somaTotal: number
  onDrillDown: (codigo: number, nome: string) => void
  disabled?: boolean
}) {
  if (isLoading) return <div className="rounded-xl border border-gray-200 bg-white p-6"><Spinner /></div>
  if (isError) return <div className="rounded-xl border border-gray-200 bg-white p-6"><ErrorAlert /></div>
  if (!data?.length) return <div className="rounded-xl border border-gray-200 bg-white p-6"><EmptyState /></div>

  const maxTotal = Math.max(...data.map((d) => d.total))

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-6">
      <div className="space-y-3">
        {data.map((d, i) => {
          const pct = somaTotal > 0 ? (d.total / somaTotal) * 100 : 0
          const canDrill = d.has_children && !disabled

          return (
            <div
              key={d.codigo}
              className={canDrill ? 'cursor-pointer group' : 'group'}
              onClick={() => canDrill && onDrillDown(d.codigo, d.grupo)}
              title={
                disabled
                  ? 'Drill-down desabilitado enquanto há filtro de assuntos'
                  : canDrill
                  ? 'Clique para ver subassuntos'
                  : undefined
              }
            >
              <div className="flex items-baseline justify-between gap-2 mb-1 sm:gap-4">
                <span className="min-w-0 break-words text-[13px] leading-tight text-gray-700 group-hover:text-gray-900 transition-colors">
                  {d.grupo}
                  {canDrill && (
                    <span className="ml-1.5 text-[11px] text-blue-500 opacity-0 group-hover:opacity-100 transition-opacity">
                      &rsaquo;
                    </span>
                  )}
                </span>
                <span className="text-[13px] font-semibold text-gray-900 shrink-0 tabular-nums">
                  {formatNumber(d.total)}
                  <span className="ml-1 text-[11px] font-normal text-gray-400">
                    ({pct.toFixed(1)}%)
                  </span>
                </span>
              </div>
              <div className="h-5 w-full rounded bg-gray-100">
                <div
                  className="h-full rounded transition-all duration-300"
                  style={{
                    width: `${(d.total / maxTotal) * 100}%`,
                    backgroundColor: CHART_COLORS[i % CHART_COLORS.length],
                  }}
                />
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

/** Breadcrumb com botão voltar e caminho clicável. */
function Breadcrumb({
  path,
  onNavigate,
  onBack,
}: {
  path: BreadcrumbItem[]
  onNavigate: (index: number) => void
  onBack: () => void
}) {
  return (
    <div className="flex items-center gap-1.5 text-[13px] flex-wrap">
      <button
        onClick={onBack}
        className="flex items-center justify-center h-6 w-6 rounded hover:bg-gray-100 text-gray-500 hover:text-gray-700 transition-colors shrink-0"
        title="Voltar um nível"
      >
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4">
          <path fillRule="evenodd" d="M17 10a.75.75 0 0 1-.75.75H5.612l4.158 3.96a.75.75 0 1 1-1.04 1.08l-5.5-5.25a.75.75 0 0 1 0-1.08l5.5-5.25a.75.75 0 1 1 1.04 1.08L5.612 9.25H16.25A.75.75 0 0 1 17 10Z" clipRule="evenodd" />
        </svg>
      </button>
      <button
        onClick={() => onNavigate(-1)}
        className="text-blue-600 hover:text-blue-800 hover:underline transition-colors"
      >
        Tudo
      </button>
      {path.map((item, i) => (
        <span key={item.codigo} className="flex items-center gap-1.5">
          <span className="text-gray-400">/</span>
          {i < path.length - 1 ? (
            <button
              onClick={() => onNavigate(i)}
              className="text-blue-600 hover:text-blue-800 hover:underline transition-colors"
            >
              {item.nome}
            </button>
          ) : (
            <span className="font-medium text-gray-700">{item.nome}</span>
          )}
        </span>
      ))}
    </div>
  )
}
