import { useState } from 'react'
import { TopBar } from '../components/layout/TopBar'
import { FilterBar } from '../components/filters/FilterBar'
import { Card } from '../components/ui/Card'
import { Spinner } from '../components/ui/Spinner'
import { EmptyState } from '../components/ui/EmptyState'
import { useCargaReduzida, useFilterOptions } from '../api/hooks/useFilters'
import { useCompararChefias, useCompararProcuradores, useCompararPeriodos } from '../api/hooks/useComparativos'
import { SelectFilter } from '../components/filters/SelectFilter'
import { formatNumber } from '../utils/formatters'

type TabType = 'chefias' | 'procuradores' | 'periodos'

export function ComparativosPage() {
  const [activeTab, setActiveTab] = useState<TabType>('chefias')
  const [selectedChefias, setSelectedChefias] = useState<string[]>([])
  const [selectedProcs, setSelectedProcs] = useState<string[]>([])
  const [p1Inicio, setP1Inicio] = useState('')
  const [p1Fim, setP1Fim] = useState('')
  const [p2Inicio, setP2Inicio] = useState('')
  const [p2Fim, setP2Fim] = useState('')

  const { data: options } = useFilterOptions()
  const { crSet } = useCargaReduzida()
  const chefiasQuery = useCompararChefias(selectedChefias)
  const procsQuery = useCompararProcuradores(selectedProcs)
  const periodosQuery = useCompararPeriodos(p1Inicio, p1Fim, p2Inicio, p2Fim)

  const tabs: { key: TabType; label: string }[] = [
    { key: 'chefias', label: 'Chefias' },
    { key: 'procuradores', label: 'Procuradores' },
    { key: 'periodos', label: 'Períodos' },
  ]

  return (
    <>
      <TopBar title="Comparativos" />
      <FilterBar />
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
            <div className="flex items-center gap-3">
              <span className="text-sm text-gray-600">Selecione chefias:</span>
              {options && (
                <SelectFilter
                  label="Chefias"
                  options={options.chefias}
                  value={selectedChefias}
                  onChange={setSelectedChefias}
                />
              )}
            </div>
            {chefiasQuery.isLoading && <Spinner />}
            {chefiasQuery.data && <ComparisonTable data={chefiasQuery.data} labelKey="chefia" />}
            {selectedChefias.length < 2 && <EmptyState message="Selecione ao menos 2 chefias para comparar" />}
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
    </>
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
