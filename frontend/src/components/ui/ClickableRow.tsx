import type { ReactNode, KeyboardEvent } from 'react'

interface ClickableRowProps {
  /** Indica se a linha é clicável */
  isClickable: boolean
  /** Handler de click */
  onClick?: () => void
  /** Conteúdo da linha */
  children: ReactNode
  /** Texto alternativo para acessibilidade */
  ariaLabel?: string
  /** Texto do tooltip */
  title?: string
  /** Classes CSS adicionais */
  className?: string
  /** Mostra ícone de navegação mesmo sem hover (útil para mobile) */
  showIconAlways?: boolean
}

/**
 * Componente reutilizável para linhas clicáveis com feedback visual claro.
 *
 * Features:
 * - Cursor pointer no hover
 * - Background hover suave
 * - Transições suaves
 * - Ícone de navegação (chevron) à direita
 * - Suporte a navegação por teclado (Tab + Enter/Space)
 * - Estados de foco visíveis para acessibilidade
 * - Ícone visível em mobile (sem necessidade de hover)
 *
 * @example
 * ```tsx
 * <ClickableRow
 *   isClickable={hasChildren}
 *   onClick={() => navigate(id)}
 *   ariaLabel="Ver detalhes do item"
 *   title="Clique para ver mais detalhes"
 * >
 *   <div>Conteúdo da linha</div>
 * </ClickableRow>
 * ```
 */
export function ClickableRow({
  isClickable,
  onClick,
  children,
  ariaLabel,
  title,
  className = '',
  showIconAlways = false,
}: ClickableRowProps) {
  const handleKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
    // Suporte para Enter e Space (padrão de acessibilidade)
    if (isClickable && onClick && (e.key === 'Enter' || e.key === ' ')) {
      e.preventDefault()
      onClick()
    }
  }

  const baseClasses = 'group relative transition-all duration-200'

  const clickableClasses = isClickable
    ? 'cursor-pointer hover:bg-gray-50/80 hover:shadow-sm rounded-md -mx-1 px-1 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-1'
    : ''

  return (
    <div
      className={`${baseClasses} ${clickableClasses} ${className}`}
      onClick={isClickable ? onClick : undefined}
      onKeyDown={handleKeyDown}
      role={isClickable ? 'button' : undefined}
      tabIndex={isClickable ? 0 : undefined}
      aria-label={ariaLabel}
      title={title}
    >
      <div className="flex items-center gap-2">
        {/* Conteúdo principal */}
        <div className="flex-1 min-w-0">
          {children}
        </div>

        {/* Ícone de navegação (chevron) */}
        {isClickable && (
          <div
            className={`shrink-0 transition-all duration-200 ${
              showIconAlways
                ? 'opacity-40 group-hover:opacity-100'
                : 'opacity-0 group-hover:opacity-100 group-focus-visible:opacity-100'
            }`}
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 20 20"
              fill="currentColor"
              className="h-5 w-5 text-blue-500 transition-transform group-hover:translate-x-0.5"
            >
              <path
                fillRule="evenodd"
                d="M8.22 5.22a.75.75 0 0 1 1.06 0l4.25 4.25a.75.75 0 0 1 0 1.06l-4.25 4.25a.75.75 0 0 1-1.06-1.06L11.94 10 8.22 6.28a.75.75 0 0 1 0-1.06Z"
                clipRule="evenodd"
              />
            </svg>
          </div>
        )}
      </div>
    </div>
  )
}
