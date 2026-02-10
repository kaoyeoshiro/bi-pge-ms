import { useAssuntoPath } from '../../api/hooks/useAssuntoExplorer'

interface AssuntoHierarchyProps {
  codigo: number
  showAsTooltip?: boolean
}

/**
 * Exibe a hierarquia completa de um assunto (da raiz até ele).
 * Formato: Raiz > Área > Subárea > ... > Assunto
 */
export function AssuntoHierarchy({ codigo, showAsTooltip = false }: AssuntoHierarchyProps) {
  const { data: path, isLoading, isError } = useAssuntoPath(codigo)

  if (isLoading) {
    return (
      <div className="text-[10px] text-gray-400 italic">
        Carregando hierarquia...
      </div>
    )
  }

  if (isError || !path || path.length === 0) {
    return (
      <div className="text-[10px] text-gray-400 italic">
        Hierarquia não disponível
      </div>
    )
  }

  const breadcrumb = path.map((node) => node.nome).join(' > ')

  if (showAsTooltip) {
    return (
      <div className="text-[10px] text-gray-500 italic truncate" title={breadcrumb}>
        {breadcrumb}
      </div>
    )
  }

  return (
    <div className="flex items-center gap-1 text-[10px] text-gray-600">
      <svg
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 20 20"
        fill="currentColor"
        className="h-3 w-3 shrink-0 text-gray-400"
      >
        <path
          fillRule="evenodd"
          d="M2 3.5A1.5 1.5 0 0 1 3.5 2h9A1.5 1.5 0 0 1 14 3.5v11.75A2.75 2.75 0 0 0 16.75 18h.5a.75.75 0 0 1 0 1.5h-.5A4.25 4.25 0 0 1 12.5 15.25V3.5a.5.5 0 0 0-.5-.5h-9a.5.5 0 0 0-.5.5v12a.5.5 0 0 0 .5.5h2.25a.75.75 0 0 1 0 1.5H3.5A1.5 1.5 0 0 1 2 15.5v-12Z"
          clipRule="evenodd"
        />
      </svg>
      <div className="flex-1 overflow-hidden">
        <div className="truncate" title={breadcrumb}>
          {path.map((node, index) => (
            <span key={node.codigo}>
              {index > 0 && <span className="mx-1 text-gray-400">›</span>}
              <span className={index === path.length - 1 ? 'font-medium text-gray-700' : 'text-gray-500'}>
                {node.nome}
              </span>
            </span>
          ))}
        </div>
      </div>
    </div>
  )
}
