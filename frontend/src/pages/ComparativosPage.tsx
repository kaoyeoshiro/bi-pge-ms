import { useState, useMemo } from 'react'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'
import { TopBar } from '../components/layout/TopBar'
import { FilterParamsProvider } from '../api/hooks/useFilterParams'
import { Card } from '../components/ui/Card'
import { Spinner } from '../components/ui/Spinner'
import { EmptyState } from '../components/ui/EmptyState'
import { useCargaReduzida, useFilterOptions } from '../api/hooks/useFilters'
import { useCompararChefias, useCompararProcuradores, useCompararPeriodos } from '../api/hooks/useComparativos'
import { SelectFilter } from '../components/filters/SelectFilter'
import { formatNumber } from '../utils/formatters'
import type { FilterParams } from '../api/hooks/useFilterParams'

type TabType = 'chefias' | 'procuradores' | 'periodos'
type PeriodMode = 'all' | 'anos' | 'periodo'

const PERIOD_MODES: { key: PeriodMode; label: string }[] = [
  { key: 'all', label: 'Todo o período' },
  { key: 'anos', label: 'Por Ano' },
  { key: 'periodo', label: 'Intervalo' },
]

/** Params vazio (sem filtros globais) — estável para evitar re-renders. */
const EMPTY_PARAMS: FilterParams = {}

/**
 * Wrapper que isola a página de Comparativos do store global de filtros.
 * A página possui seus próprios controles de seleção (chefias, procuradores, períodos).
 */
export function ComparativosPage() {
  return (
    <>
      <TopBar title="Comparativos" />
      <FilterParamsProvider value={EMPTY_PARAMS}>
        <ComparativosPageContent />
      </FilterParamsProvider>
    </>
  )
}

/**
 * Conteúdo interno da página de Comparativos.
 * Os hooks de API resolvem useFilterParams() via contexto (params vazio).
 */
function ComparativosPageContent() {
  const [activeTab, setActiveTab] = useState<TabType>('chefias')
  const [selectedChefias, setSelectedChefias] = useState<string[]>([])
  const [selectedProcs, setSelectedProcs] = useState<string[]>([])
  const [p1Inicio, setP1Inicio] = useState('')
  const [p1Fim, setP1Fim] = useState('')
  const [p2Inicio, setP2Inicio] = useState('')
  const [p2Fim, setP2Fim] = useState('')

  // Filtro de período local da aba Chefias
  const [periodMode, setPeriodMode] = useState<PeriodMode>('all')
  const [selectedAnos, setSelectedAnos] = useState<number[]>([])
  const [periodoInicio, setPeriodoInicio] = useState('')
  const [periodoFim, setPeriodoFim] = useState('')

  const chefiaPeriodParams = useMemo((): FilterParams => {
    if (periodMode === 'anos' && selectedAnos.length > 0) {
      return { anos: selectedAnos.map(String) }
    }
    if (periodMode === 'periodo') {
      const p: FilterParams = {}
      if (periodoInicio) p.data_inicio = periodoInicio
      if (periodoFim) p.data_fim = periodoFim
      return p
    }
    return {}
  }, [periodMode, selectedAnos, periodoInicio, periodoFim])

  const periodSummary = useMemo(() => {
    if (periodMode === 'all') return 'Exibindo dados de todo o período disponível'
    if (periodMode === 'anos') {
      if (selectedAnos.length === 0) return 'Selecione ao menos um ano'
      const sorted = [...selectedAnos].sort()
      return `Anos: ${sorted.join(', ')}`
    }
    if (!periodoInicio && !periodoFim) return 'Defina as datas do intervalo'
    const fmt = (d: string) => d ? new Date(d + 'T00:00').toLocaleDateString('pt-BR') : '...'
    return `Período: ${fmt(periodoInicio)} a ${fmt(periodoFim)}`
  }, [periodMode, selectedAnos, periodoInicio, periodoFim])

  const { data: options } = useFilterOptions()
  const { crSet } = useCargaReduzida()
  const chefiasQuery = useCompararChefias(selectedChefias, chefiaPeriodParams)
  const procsQuery = useCompararProcuradores(selectedProcs)
  const periodosQuery = useCompararPeriodos(p1Inicio, p1Fim, p2Inicio, p2Fim)

  const tabs: { key: TabType; label: string }[] = [
    { key: 'chefias', label: 'Chefias' },
    { key: 'procuradores', label: 'Procuradores' },
    { key: 'periodos', label: 'Períodos' },
  ]

  return (
      <div className="space-y-4 p-4 sm:space-y-6 sm:p-6">
        <div className="flex flex-wrap gap-1">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`rounded-lg px-4 py-2 text-sm transition-colors ${
                activeTab === tab.key
                  ? 'bg-primary text-white font-medium'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {activeTab === 'chefias' && (
          <div className="space-y-4">
            {/* Filtros: período + chefias */}
            <Card>
              <div className="space-y-4">
                {/* Período */}
                <div className="space-y-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-sm font-medium text-gray-700">Período</span>
                    {PERIOD_MODES.map(({ key, label }) => (
                      <button
                        key={key}
                        onClick={() => setPeriodMode(key)}
                        className={`rounded-md px-3 py-1.5 text-xs transition-colors ${
                          periodMode === key
                            ? 'bg-primary/10 text-primary font-medium ring-1 ring-primary/30'
                            : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                        }`}
                      >
                        {label}
                      </button>
                    ))}
                  </div>

                  {periodMode === 'anos' && options && (
                    <div className="flex items-center gap-2">
                      <SelectFilter
                        label="Anos"
                        options={options.anos.map(String)}
                        value={selectedAnos.map(String)}
                        onChange={(v) => setSelectedAnos(v.map(Number))}
                        showSelectAll
                      />
                      {selectedAnos.length > 0 && (
                        <button
                          onClick={() => setSelectedAnos([])}
                          className="text-xs text-gray-500 hover:text-gray-700 transition-colors"
                        >
                          Limpar
                        </button>
                      )}
                    </div>
                  )}

                  {periodMode === 'periodo' && (
                    <div className="flex flex-wrap items-center gap-2">
                      <input
                        type="date"
                        value={periodoInicio}
                        onChange={(e) => setPeriodoInicio(e.target.value)}
                        className="min-w-0 rounded border border-gray-300 px-2 py-1 text-xs focus:border-primary focus:outline-none"
                      />
                      <span className="text-xs text-gray-400">a</span>
                      <input
                        type="date"
                        value={periodoFim}
                        onChange={(e) => setPeriodoFim(e.target.value)}
                        className="min-w-0 rounded border border-gray-300 px-2 py-1 text-xs focus:border-primary focus:outline-none"
                      />
                      {(periodoInicio || periodoFim) && (
                        <button
                          onClick={() => { setPeriodoInicio(''); setPeriodoFim('') }}
                          className="text-xs text-gray-500 hover:text-gray-700 transition-colors"
                        >
                          Limpar
                        </button>
                      )}
                    </div>
                  )}
                </div>

                {/* Separador */}
                <div className="border-t border-gray-100" />

                {/* Chefias */}
                <div className="space-y-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-sm font-medium text-gray-700">Chefias</span>
                    {options && (
                      <>
                        <SelectFilter
                          label="Selecione uma ou mais chefias"
                          options={options.chefias}
                          value={selectedChefias}
                          onChange={setSelectedChefias}
                        />
                        <button
                          onClick={() => setSelectedChefias([...options.chefias])}
                          className="rounded px-2 py-1 text-xs text-primary hover:bg-primary/5 transition-colors"
                        >
                          Incluir todas
                        </button>
                        <button
                          onClick={() => setSelectedChefias([])}
                          className="rounded px-2 py-1 text-xs text-gray-500 hover:bg-gray-100 transition-colors"
                        >
                          Excluir todas
                        </button>
                      </>
                    )}
                    {options && selectedChefias.length > 0 && (
                      <span className="text-xs text-gray-400">
                        {selectedChefias.length} de {options.chefias.length} selecionadas
                      </span>
                    )}
                  </div>
                </div>

                {/* Resumo do período ativo */}
                <div className="rounded-md bg-gray-50 px-3 py-2 text-xs text-gray-600">
                  {periodSummary}
                </div>
              </div>
            </Card>

            {/* Resultados */}
            {chefiasQuery.isLoading && <Spinner />}
            {chefiasQuery.data && (
              <>
                <ComparisonChart data={chefiasQuery.data} labelKey="chefia" />
                <ComparisonTable data={chefiasQuery.data} labelKey="chefia" />
              </>
            )}
            {selectedChefias.length < 2 && !chefiasQuery.isLoading && (
              <EmptyState message="Selecione ao menos 2 chefias para comparar" />
            )}
          </div>
        )}

        {activeTab === 'procuradores' && (
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <span className="text-sm text-gray-600">Selecione procuradores:</span>
              {options && (
                <SelectFilter
                  label="Procuradores"
                  options={options.procuradores}
                  value={selectedProcs}
                  onChange={setSelectedProcs}
                />
              )}
            </div>
            {procsQuery.isLoading && <Spinner />}
            {procsQuery.data && <ComparisonTable data={procsQuery.data} labelKey="procurador" cargaReduzidaSet={crSet} />}
            {selectedProcs.length < 2 && <EmptyState message="Selecione ao menos 2 procuradores para comparar" />}
          </div>
        )}

        {activeTab === 'periodos' && (
          <div className="space-y-4">
            <Card title="Comparar Períodos">
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 sm:gap-6">
                <div className="space-y-2">
                  <p className="text-sm font-medium text-gray-600">Período 1</p>
                  <div className="flex gap-2">
                    <input type="date" value={p1Inicio} onChange={(e) => setP1Inicio(e.target.value)} className="min-w-0 flex-1 rounded border border-gray-300 px-2 py-1 text-sm" />
                    <input type="date" value={p1Fim} onChange={(e) => setP1Fim(e.target.value)} className="min-w-0 flex-1 rounded border border-gray-300 px-2 py-1 text-sm" />
                  </div>
                </div>
                <div className="space-y-2">
                  <p className="text-sm font-medium text-gray-600">Período 2</p>
                  <div className="flex gap-2">
                    <input type="date" value={p2Inicio} onChange={(e) => setP2Inicio(e.target.value)} className="min-w-0 flex-1 rounded border border-gray-300 px-2 py-1 text-sm" />
                    <input type="date" value={p2Fim} onChange={(e) => setP2Fim(e.target.value)} className="min-w-0 flex-1 rounded border border-gray-300 px-2 py-1 text-sm" />
                  </div>
                </div>
              </div>
            </Card>
            {periodosQuery.isLoading && <Spinner />}
            {periodosQuery.data && (
              <Card title="Resultado da Comparação">
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 sm:gap-6">
                  {['periodo_1', 'periodo_2'].map((key, idx) => {
                    const periodo = periodosQuery.data[key]
                    return (
                      <div key={key} className="space-y-3">
                        <p className="text-sm font-semibold text-primary">
                          Período {idx + 1}: {periodo.inicio} a {periodo.fim}
                        </p>
                        {periodo.metricas.map((m: { label: string; valor: number }) => (
                          <div key={m.label} className="flex justify-between border-b border-gray-100 pb-1 text-sm">
                            <span className="text-gray-600">{m.label}</span>
                            <span className="font-medium">{formatNumber(m.valor)}</span>
                          </div>
                        ))}
                      </div>
                    )
                  })}
                </div>
              </Card>
            )}
          </div>
        )}
      </div>
  )
}

/** Cores semânticas das 3 métricas. */
const METRIC_COLORS: Record<string, string> = {
  'Processos Novos': '#D4A843',
  'Peças Finalizadas': '#2E7D32',
  'Pendências': '#C62828',
}

/** Transforma resposta da API em formato Recharts. */
function toChartData(data: Array<Record<string, unknown>>, labelKey: string) {
  return data.map((row) => {
    const metricas = row.metricas as Array<{ label: string; valor: number }>
    const fullName = row[labelKey] as string
    const item: Record<string, string | number> = {
      name: fullName.length > 28 ? fullName.slice(0, 28) + '…' : fullName,
      fullName,
    }
    for (const m of metricas) {
      item[m.label] = m.valor
    }
    return item
  })
}

/** Gráfico de barras agrupadas comparando métricas entre entidades. */
function ComparisonChart({
  data,
  labelKey,
}: {
  data: Array<Record<string, unknown>>
  labelKey: string
}) {
  const chartData = toChartData(data, labelKey)
  const metricKeys = Object.keys(METRIC_COLORS)
  const chartHeight = Math.max(320, data.length * 60)

  return (
    <Card title="Comparativo">
      <ResponsiveContainer width="100%" height={chartHeight}>
        <BarChart
          data={chartData}
          layout="vertical"
          margin={{ top: 5, right: 30, bottom: 5, left: 10 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" horizontal={false} />
          <XAxis
            type="number"
            tick={{ fontSize: 11 }}
            tickFormatter={(value) => formatNumber(Number(value))}
          />
          <YAxis
            type="category"
            dataKey="name"
            width={200}
            tick={{ fontSize: 12 }}
          />
          <Tooltip
            formatter={(value) => [formatNumber(Number(value)), '']}
            labelFormatter={(_, payload) =>
              (payload?.[0]?.payload as Record<string, string>)?.fullName ?? ''
            }
            contentStyle={{ fontSize: 12, borderRadius: 8 }}
          />
          <Legend
            wrapperStyle={{ fontSize: 12, paddingTop: 8 }}
          />
          {metricKeys.map((key) => (
            <Bar
              key={key}
              dataKey={key}
              name={key}
              fill={METRIC_COLORS[key]}
              radius={[0, 4, 4, 0]}
              barSize={14}
            />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </Card>
  )
}

function ComparisonTable({
  data,
  labelKey,
  cargaReduzidaSet,
}: {
  data: Array<Record<string, unknown>>
  labelKey: string
  cargaReduzidaSet?: Set<string>
}) {
  return (
    <Card>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-100">
              <th className="px-4 py-2 text-left text-xs font-semibold text-gray-500 uppercase">
                {labelKey === 'chefia' ? 'Chefia' : 'Procurador'}
              </th>
              <th className="px-4 py-2 text-right text-xs font-semibold text-gray-500 uppercase">Processos Novos</th>
              <th className="px-4 py-2 text-right text-xs font-semibold text-gray-500 uppercase">Peças Finalizadas</th>
              <th className="px-4 py-2 text-right text-xs font-semibold text-gray-500 uppercase">Pendências</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {data.map((row) => {
              const metricas = row.metricas as Array<{ label: string; valor: number }>
              const label = row[labelKey] as string
              return (
                <tr key={label} className="hover:bg-gray-50/50">
                  <td className="px-4 py-2 font-medium text-gray-700">
                    {label}
                    {cargaReduzidaSet?.has(label) && (
                      <span className="ml-1.5 inline-flex items-center rounded-full bg-amber-100 px-1.5 py-0.5 text-[10px] font-bold text-amber-700" title="Carga Reduzida">
                        CR
                      </span>
                    )}
                  </td>
                  {metricas.map((m) => (
                    <td key={m.label} className="px-4 py-2 text-right">{formatNumber(m.valor)}</td>
                  ))}
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </Card>
  )
}
