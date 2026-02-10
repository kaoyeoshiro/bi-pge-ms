import { useState } from 'react'
import { TopBar } from '../components/layout/TopBar'
import { PageFilterBar } from '../components/filters/PageFilterBar'
import { FilterParamsProvider } from '../api/hooks/useFilterParams'
import { AssuntoAutocomplete } from '../components/filters/AssuntoAutocomplete'
import { AssuntoExplorerCard } from '../components/charts/AssuntoExplorerCard'
import { usePageFilters } from '../hooks/usePageFilters'
import { useAssuntoPath } from '../api/hooks/useAssuntoExplorer'
import type { AssuntoNode } from '../types'

/**
 * Wrapper que isola os filtros da página do store global.
 * O FilterParamsProvider faz com que os hooks de API usem filtros locais.
 */
export function AssuntosPage() {
  const { params, ...filterBarProps } = usePageFilters()

  return (
    <>
      <TopBar title="Explorar Assuntos" />
      <PageFilterBar {...filterBarProps} />
      <FilterParamsProvider value={params}>
        <AssuntosPageContent />
      </FilterParamsProvider>
    </>
  )
}

/**
 * Conteúdo interno da página de exploração de assuntos.
 * Os hooks de API resolvem useFilterParams() via contexto local.
 */
function AssuntosPageContent() {
  const [selectedAssuntos, setSelectedAssuntos] = useState<AssuntoNode[]>([])

  // Busca o path hierárquico do primeiro assunto selecionado
  const selectedCodigo = selectedAssuntos.length > 0 ? selectedAssuntos[0].codigo : null
  const { data: pathData } = useAssuntoPath(selectedCodigo)

  // Quando há assuntos selecionados, passa com o path completo para auto-navegar no drill-down
  const filterAssunto = selectedAssuntos.length > 0 && pathData
    ? {
        codigo: selectedAssuntos[0].codigo,
        nome: selectedAssuntos[0].nome,
        path: pathData,
      }
    : null

  return (
    <div className="space-y-4 p-4 sm:space-y-6 sm:p-6">
      {/* Campo de busca de assuntos */}
      <div className="rounded-lg bg-white p-4 shadow-sm">
        <label className="mb-2 block text-sm font-medium text-gray-700">
          Filtrar por assuntos específicos
        </label>
        <AssuntoAutocomplete
          value={selectedAssuntos}
          onChange={setSelectedAssuntos}
          placeholder="Digite para buscar assuntos..."
        />
        {selectedAssuntos.length > 0 && (
          <div className="mt-3 rounded-md bg-blue-50 p-3 text-sm text-blue-700">
            <strong>Filtro ativo:</strong> Mostrando apenas dados dos {selectedAssuntos.length} assunto(s) selecionado(s).
            {selectedAssuntos.length > 1 && ' Os dados estão agregados.'}
          </div>
        )}
      </div>

      {/* Card de drill-down hierárquico */}
      <AssuntoExplorerCard
        title="Assuntos Jurídicos (Hierarquia Completa)"
        filterAssunto={filterAssunto}
      />
    </div>
  )
}
