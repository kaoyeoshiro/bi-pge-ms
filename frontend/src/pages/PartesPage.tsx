import { useState, useCallback } from 'react'
import { TopBar } from '../components/layout/TopBar'
import { Spinner } from '../components/ui/Spinner'
import { ErrorAlert } from '../components/ui/ErrorAlert'
import { EmptyState } from '../components/ui/EmptyState'
import { usePartesKPIs, usePartesRanking, useParteProcessos } from '../api/hooks/usePartes'
import { formatNumber, formatCurrency } from '../utils/formatters'
import type { PaginationParams } from '../types'

const ROLES = [
  { key: 'demandante', label: 'Demandantes' },
  { key: 'executado', label: 'Executados' },
  { key: 'advogado', label: 'Advogados' },
  { key: 'coreu', label: 'Co-Réus' },
] as const

/** Colunas exibidas na tabela por papel selecionado. */
function getRoleColumn(role: string | null) {
  switch (role) {
    case 'demandante':
      return { key: 'qtd_contra_estado', label: 'Processos (Demandante)' }
    case 'executado':
      return { key: 'qtd_executado_estado', label: 'Processos (Executado)' }
    case 'advogado':
      return { key: 'qtd_advogado', label: 'Processos (Advogado)' }
    case 'coreu':
      return { key: 'qtd_coreu_estado', label: 'Processos (Co-Réu)' }
    default:
      return { key: 'qtd_processos', label: 'Total Processos' }
  }
}

export function PartesPage() {
  const [role, setRole] = useState<string | null>('demandante')
  const [pagination, setPagination] = useState<PaginationParams>({
    page: 1,
    page_size: 25,
    sort_by: 'qtd_contra_estado',
    sort_order: 'desc',
  })
  const [searchInput, setSearchInput] = useState('')
  const [selectedParteId, setSelectedParteId] = useState<number | null>(null)

  const kpis = usePartesKPIs()
  const ranking = usePartesRanking(role, pagination)

  const handleRoleChange = useCallback((newRole: string | null) => {
    setRole(newRole)
    setPagination((prev) => ({ ...prev, page: 1, sort_by: 'qtd_processos', sort_order: 'desc' }))
  }, [])

  const handleSearch = useCallback(() => {
    setPagination((prev) => ({ ...prev, search: searchInput || undefined, page: 1 }))
  }, [searchInput])

  const handleSort = useCallback((column: string) => {
    setPagination((prev) => {
      if (prev.sort_by === column) {
        return { ...prev, sort_order: prev.sort_order === 'asc' ? 'desc' : 'asc' }
      }
      return { ...prev, sort_by: column, sort_order: 'desc' }
    })
  }, [])

  const handlePagination = useCallback((p: Partial<PaginationParams>) => {
    setPagination((prev) => ({ ...prev, ...p }))
  }, [])

  const roleCol = getRoleColumn(role)

  return (
    <>
      <TopBar title="Partes e Demandantes" />

      <div className="space-y-4 p-4 sm:space-y-6 sm:p-6">
        {/* KPIs */}
        <PartesKPICards kpis={kpis} />

        {/* Abas de papel */}
        <div className="flex flex-wrap items-center gap-2">
          {ROLES.map((r) => (
            <button
              key={r.key ?? 'all'}
              onClick={() => handleRoleChange(r.key)}
              className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
                role === r.key
                  ? 'bg-primary text-white shadow-sm'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {r.label}
            </button>
          ))}
        </div>

        {/* Tabela de ranking */}
        <div className="rounded-xl border border-gray-100 bg-surface shadow-sm">
          {/* Busca */}
          <div className="flex flex-wrap items-center gap-2 border-b border-gray-100 px-3 py-2 sm:gap-3 sm:px-5 sm:py-3">
            <div className="relative min-w-0 flex-1">
              <input
                type="text"
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                placeholder="Buscar por nome..."
                className="w-full rounded-lg border border-gray-300 px-3 py-1.5 text-sm focus:border-primary focus:outline-none sm:max-w-md"
              />
            </div>
            <button
              onClick={handleSearch}
              className="rounded-lg bg-primary px-3 py-1.5 text-xs font-medium text-white hover:bg-primary-light transition-colors"
            >
              Buscar
            </button>
          </div>

          {/* Conteúdo */}
          {ranking.isLoading ? (
            <Spinner />
          ) : ranking.isError ? (
            <ErrorAlert />
          ) : !ranking.data?.items.length ? (
            <EmptyState />
          ) : (
            <>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead className="border-b border-gray-100 bg-gray-50/50">
                    <tr>
                      <th className="px-4 py-2.5 text-xs font-semibold text-gray-500 uppercase tracking-wide w-8">
                        #
                      </th>
                      <SortableHeader
                        label="Nome"
                        column="nome"
                        current={pagination.sort_by}
                        order={pagination.sort_order}
                        onSort={handleSort}
                      />
                      <SortableHeader
                        label={roleCol.label}
                        column={roleCol.key}
                        current={pagination.sort_by}
                        order={pagination.sort_order}
                        onSort={handleSort}
                        align="right"
                      />
                      <SortableHeader
                        label="Valor Total"
                        column="valor_total"
                        current={pagination.sort_by}
                        order={pagination.sort_order}
                        onSort={handleSort}
                        align="right"
                      />
                      <SortableHeader
                        label="Valor Médio"
                        column="valor_medio"
                        current={pagination.sort_by}
                        order={pagination.sort_order}
                        onSort={handleSort}
                        align="right"
                      />
                      <th className="px-4 py-2.5 text-xs font-semibold text-gray-500 uppercase tracking-wide text-center">
                        Detalhes
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-50">
                    {ranking.data.items.map((parte, idx) => {
                      const rowNum = (ranking.data!.page - 1) * ranking.data!.page_size + idx + 1
                      const roleCount = role
                        ? (parte[roleCol.key as keyof typeof parte] as number)
                        : parte.qtd_processos

                      return (
                        <tr key={parte.id} className="hover:bg-gray-50/50 transition-colors">
                          <td className="px-4 py-2.5 text-xs text-gray-400 font-mono">{rowNum}</td>
                          <td className="px-4 py-2.5 text-sm text-gray-700 max-w-xs truncate" title={parte.nome}>
                            <span className="font-medium">{parte.nome}</span>
                            {parte.tipo_pessoa && (
                              <span className="ml-2 text-[10px] text-gray-400 uppercase">
                                {parte.tipo_pessoa === 'J' ? 'PJ' : 'PF'}
                              </span>
                            )}
                          </td>
                          <td className="px-4 py-2.5 text-sm text-gray-700 text-right font-semibold">
                            {formatNumber(roleCount)}
                          </td>
                          <td className="px-4 py-2.5 text-sm text-gray-700 text-right">
                            {formatCurrency(parte.valor_total)}
                          </td>
                          <td className="px-4 py-2.5 text-sm text-gray-700 text-right">
                            {formatCurrency(parte.valor_medio)}
                          </td>
                          <td className="px-4 py-2.5 text-center">
                            <button
                              onClick={() => setSelectedParteId(parte.id)}
                              className="rounded px-2 py-1 text-xs text-primary hover:bg-primary/10 transition-colors"
                              title="Ver processos vinculados"
                            >
                              Ver
                            </button>
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>

              {/* Paginação */}
              <div className="flex flex-wrap items-center justify-between gap-2 border-t border-gray-100 px-3 py-2 sm:px-5 sm:py-3">
                <p className="text-xs text-gray-500">
                  {ranking.data.total.toLocaleString('pt-BR')} registros | Pág.{' '}
                  {ranking.data.page}/{ranking.data.total_pages}
                </p>
                <div className="flex items-center gap-2">
                  <button
                    disabled={ranking.data.page <= 1}
                    onClick={() => handlePagination({ page: ranking.data!.page - 1 })}
                    className="rounded border border-gray-300 px-3 py-1 text-xs text-gray-600 hover:bg-gray-50 disabled:opacity-40 transition-colors"
                  >
                    Anterior
                  </button>
                  <button
                    disabled={ranking.data.page >= ranking.data.total_pages}
                    onClick={() => handlePagination({ page: ranking.data!.page + 1 })}
                    className="rounded border border-gray-300 px-3 py-1 text-xs text-gray-600 hover:bg-gray-50 disabled:opacity-40 transition-colors"
                  >
                    Próxima
                  </button>
                </div>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Modal de processos */}
      {selectedParteId !== null && (
        <ProcessosModal parteId={selectedParteId} onClose={() => setSelectedParteId(null)} />
      )}
    </>
  )
}

/* ===== Componentes auxiliares ===== */

function PartesKPICards({ kpis }: { kpis: ReturnType<typeof usePartesKPIs> }) {
  if (kpis.isLoading) return <Spinner />
  if (kpis.isError) return <ErrorAlert />
  if (!kpis.data) return null

  const cards = [
    { label: 'Total de Pessoas', value: formatNumber(kpis.data.total_pessoas) },
    { label: 'Demandantes', value: formatNumber(kpis.data.total_demandantes) },
    { label: 'Executados', value: formatNumber(kpis.data.total_executados) },
    { label: 'Advogados', value: formatNumber(kpis.data.total_advogados) },
    { label: 'Co-Réus', value: formatNumber(kpis.data.total_coreus) },
    { label: 'Valor Total Causas', value: formatCurrency(kpis.data.valor_total_causas) },
    { label: 'Processos com Partes', value: formatNumber(kpis.data.total_processos_com_partes) },
  ]

  return (
    <div className="grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-4 xl:grid-cols-7">
      {cards.map((c) => (
        <div key={c.label} className="rounded-xl border border-gray-100 bg-surface p-3 shadow-sm sm:p-4">
          <p className="text-[10px] font-medium text-gray-500 uppercase tracking-wide sm:text-xs">
            {c.label}
          </p>
          <p className="mt-1 text-lg font-bold text-primary sm:mt-2 sm:text-xl">{c.value}</p>
        </div>
      ))}
    </div>
  )
}

function SortableHeader({
  label,
  column,
  current,
  order,
  onSort,
  align = 'left',
}: {
  label: string
  column: string
  current?: string
  order?: string
  onSort: (col: string) => void
  align?: 'left' | 'right'
}) {
  const isActive = current === column
  return (
    <th
      onClick={() => onSort(column)}
      className={`cursor-pointer whitespace-nowrap px-4 py-2.5 text-xs font-semibold text-gray-500 uppercase tracking-wide hover:text-primary transition-colors ${
        align === 'right' ? 'text-right' : ''
      }`}
    >
      {label}
      {isActive && <span className="ml-1">{order === 'asc' ? '\u2191' : '\u2193'}</span>}
    </th>
  )
}

function ProcessosModal({ parteId, onClose }: { parteId: number; onClose: () => void }) {
  const [page, setPage] = useState(1)
  const processos = useParteProcessos(parteId, page, 10)

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={onClose}>
      <div
        className="mx-4 max-h-[85vh] w-full max-w-4xl overflow-hidden rounded-2xl bg-white shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-gray-100 px-5 py-3">
          <h3 className="text-sm font-semibold text-gray-700">Processos Vinculados</h3>
          <button
            onClick={onClose}
            className="rounded-lg p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600 transition-colors"
          >
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Conteúdo */}
        <div className="overflow-y-auto" style={{ maxHeight: 'calc(85vh - 110px)' }}>
          {processos.isLoading ? (
            <Spinner />
          ) : processos.isError ? (
            <ErrorAlert />
          ) : !processos.data?.items.length ? (
            <EmptyState message="Nenhum processo encontrado para esta parte." />
          ) : (
            <table className="w-full text-left text-sm">
              <thead className="border-b border-gray-100 bg-gray-50/50 sticky top-0">
                <tr>
                  <th className="px-4 py-2.5 text-xs font-semibold text-gray-500 uppercase">N. Formatado</th>
                  <th className="px-4 py-2.5 text-xs font-semibold text-gray-500 uppercase">Nome no Processo</th>
                  <th className="px-4 py-2.5 text-xs font-semibold text-gray-500 uppercase">Tipo Parte</th>
                  <th className="px-4 py-2.5 text-xs font-semibold text-gray-500 uppercase text-center">Polo</th>
                  <th className="px-4 py-2.5 text-xs font-semibold text-gray-500 uppercase text-right">Valor Ação</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {processos.data.items.map((proc, i) => (
                  <tr key={i} className="hover:bg-gray-50/50 transition-colors">
                    <td className="px-4 py-2.5 text-xs font-mono text-gray-600">
                      {proc.numero_formatado || proc.cd_processo}
                    </td>
                    <td className="px-4 py-2.5 text-sm text-gray-700 max-w-xs truncate" title={proc.nome}>
                      {proc.nome}
                    </td>
                    <td className="px-4 py-2.5 text-xs text-gray-500">{proc.tipo_parte || '-'}</td>
                    <td className="px-4 py-2.5 text-xs text-center">
                      <PoloBadge polo={proc.polo} />
                    </td>
                    <td className="px-4 py-2.5 text-sm text-right text-gray-700">
                      {proc.valor_acao ? formatCurrency(proc.valor_acao) : '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Paginação do modal */}
        {processos.data && processos.data.total_pages > 1 && (
          <div className="flex items-center justify-between border-t border-gray-100 px-5 py-2">
            <p className="text-xs text-gray-500">
              {processos.data.total.toLocaleString('pt-BR')} processos | Pág. {processos.data.page}/
              {processos.data.total_pages}
            </p>
            <div className="flex gap-2">
              <button
                disabled={page <= 1}
                onClick={() => setPage((p) => p - 1)}
                className="rounded border border-gray-300 px-3 py-1 text-xs text-gray-600 hover:bg-gray-50 disabled:opacity-40"
              >
                Anterior
              </button>
              <button
                disabled={page >= processos.data.total_pages}
                onClick={() => setPage((p) => p + 1)}
                className="rounded border border-gray-300 px-3 py-1 text-xs text-gray-600 hover:bg-gray-50 disabled:opacity-40"
              >
                Próxima
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

function PoloBadge({ polo }: { polo: number | null }) {
  if (!polo) return <span className="text-gray-400">-</span>

  const config: Record<number, { label: string; color: string }> = {
    1: { label: 'Ativo', color: 'bg-blue-100 text-blue-700' },
    2: { label: 'Passivo', color: 'bg-orange-100 text-orange-700' },
    3: { label: 'Terceiro', color: 'bg-gray-100 text-gray-600' },
    4: { label: 'Advogado', color: 'bg-purple-100 text-purple-700' },
  }

  const c = config[polo] || { label: `Polo ${polo}`, color: 'bg-gray-100 text-gray-600' }

  return (
    <span className={`inline-block rounded-full px-2 py-0.5 text-[10px] font-medium ${c.color}`}>
      {c.label}
    </span>
  )
}
