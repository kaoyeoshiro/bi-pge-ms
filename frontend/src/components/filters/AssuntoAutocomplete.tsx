import { useState, useRef, useEffect } from 'react'
import { useAssuntoSearch, useAssuntoPath } from '../../api/hooks/useAssuntoExplorer'
import type { AssuntoNode } from '../../types'

interface AssuntoAutocompleteProps {
  value: AssuntoNode[]
  onChange: (assuntos: AssuntoNode[]) => void
  placeholder?: string
}

interface AssuntoChipProps {
  assunto: AssuntoNode
  onRemove: (codigo: number) => void
}

/**
 * Chip de assunto selecionado com hierarquia em tooltip.
 */
function AssuntoChip({ assunto, onRemove }: AssuntoChipProps) {
  const { data: path } = useAssuntoPath(assunto.codigo)
  const hierarchyText = path?.map((n) => n.nome).join(' > ') || assunto.nome

  return (
    <span
      className="group inline-flex items-center gap-1 rounded bg-primary/10 px-2 py-0.5 text-[11px] text-primary"
      title={hierarchyText}
    >
      <span className="max-w-[200px] truncate">{assunto.nome}</span>
      <button
        type="button"
        onClick={() => onRemove(assunto.codigo)}
        className="hover:text-primary-dark transition-colors"
        title="Remover"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 20 20"
          fill="currentColor"
          className="h-3 w-3"
        >
          <path d="M6.28 5.22a.75.75 0 0 0-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 1 0 1.06 1.06L10 11.06l3.72 3.72a.75.75 0 1 0 1.06-1.06L11.06 10l3.72-3.72a.75.75 0 0 0-1.06-1.06L10 8.94 6.28 5.22Z" />
        </svg>
      </button>
    </span>
  )
}

/**
 * Mostra hierarquia do assunto inline.
 */
function AssuntoPathInline({ codigo }: { codigo: number }) {
  const { data: path } = useAssuntoPath(codigo)
  if (!path || path.length <= 1) return null

  return (
    <div className="text-[10px] text-gray-500">
      {path.slice(0, -1).map((n) => n.nome).join(' > ')}
    </div>
  )
}

/**
 * Autocomplete multi-select para busca textual de assuntos.
 * Permite selecionar múltiplos assuntos e mostra-os como chips/tags.
 * Só permite seleção de assuntos existentes (não aceita texto livre).
 */
export function AssuntoAutocomplete({
  value,
  onChange,
  placeholder = 'Buscar assunto...',
}: AssuntoAutocompleteProps) {
  const [query, setQuery] = useState('')
  const [isOpen, setIsOpen] = useState(false)
  const [selectedIndex, setSelectedIndex] = useState(-1)
  const inputRef = useRef<HTMLInputElement>(null)
  const dropdownRef = useRef<HTMLDivElement>(null)

  const { data: assuntos, isLoading } = useAssuntoSearch(query)

  // Filtra assuntos já selecionados
  const availableAssuntos = assuntos?.filter(
    (a) => !value.some((v) => v.codigo === a.codigo)
  )

  // Fecha dropdown ao clicar fora
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(e.target as Node) &&
        !inputRef.current?.contains(e.target as Node)
      ) {
        setIsOpen(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // Abre dropdown quando há resultados
  useEffect(() => {
    if (availableAssuntos && availableAssuntos.length > 0 && query.length >= 2) {
      setIsOpen(true)
      setSelectedIndex(-1)
    } else {
      setIsOpen(false)
    }
  }, [availableAssuntos, query])

  function handleSelect(assunto: AssuntoNode) {
    onChange([...value, assunto])
    setQuery('')
    setIsOpen(false)
    inputRef.current?.focus()
  }

  function handleRemove(codigo: number) {
    onChange(value.filter((a) => a.codigo !== codigo))
    inputRef.current?.focus()
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    // Backspace remove o último chip se input estiver vazio
    if (e.key === 'Backspace' && query === '' && value.length > 0) {
      e.preventDefault()
      onChange(value.slice(0, -1))
      return
    }

    if (!isOpen || !availableAssuntos) return

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault()
        setSelectedIndex((prev) =>
          prev < availableAssuntos.length - 1 ? prev + 1 : prev
        )
        break
      case 'ArrowUp':
        e.preventDefault()
        setSelectedIndex((prev) => (prev > 0 ? prev - 1 : -1))
        break
      case 'Enter':
        e.preventDefault()
        if (selectedIndex >= 0 && availableAssuntos[selectedIndex]) {
          handleSelect(availableAssuntos[selectedIndex])
        }
        break
      case 'Escape':
        setIsOpen(false)
        inputRef.current?.blur()
        break
    }
  }

  return (
    <div className="relative">
      {/* Input com chips */}
      <div className="relative">
        <div className="flex min-h-[30px] flex-wrap items-center gap-1 rounded border border-gray-300 px-2 py-1 focus-within:border-primary">
          {/* Chips dos assuntos selecionados */}
          {value.map((assunto) => (
            <AssuntoChip
              key={assunto.codigo}
              assunto={assunto}
              onRemove={handleRemove}
            />
          ))}

          {/* Input de busca */}
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            onFocus={() => query.length >= 2 && availableAssuntos && setIsOpen(true)}
            placeholder={value.length === 0 ? placeholder : ''}
            className="min-w-[120px] flex-1 border-none px-1 py-0.5 text-xs outline-none"
          />

          {/* Loading indicator */}
          {isLoading && (
            <div className="shrink-0">
              <div className="h-3 w-3 animate-spin rounded-full border-2 border-primary/20 border-t-primary" />
            </div>
          )}
        </div>

        {/* Botão para limpar tudo */}
        {value.length > 0 && (
          <button
            type="button"
            onClick={() => onChange([])}
            className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
            title="Limpar todos"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 20 20"
              fill="currentColor"
              className="h-4 w-4"
            >
              <path d="M6.28 5.22a.75.75 0 0 0-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 1 0 1.06 1.06L10 11.06l3.72 3.72a.75.75 0 1 0 1.06-1.06L11.06 10l3.72-3.72a.75.75 0 0 0-1.06-1.06L10 8.94 6.28 5.22Z" />
            </svg>
          </button>
        )}
      </div>

      {/* Dropdown de sugestões */}
      {isOpen && (
        <div
          ref={dropdownRef}
          className="absolute z-50 mt-1 max-h-[400px] w-full overflow-auto rounded-lg border border-gray-200 bg-white shadow-lg"
        >
          {availableAssuntos && availableAssuntos.length > 0 ? (
            <ul className="py-1">
              {availableAssuntos.map((assunto, index) => (
                <li key={assunto.codigo}>
                  <button
                    type="button"
                    onClick={() => handleSelect(assunto)}
                    onMouseEnter={() => setSelectedIndex(index)}
                    className={`w-full px-3 py-2 text-left text-xs transition-colors ${
                      index === selectedIndex
                        ? 'bg-primary/10 text-primary'
                        : 'text-gray-700 hover:bg-gray-50'
                    }`}
                  >
                    <div className="font-medium">{assunto.nome}</div>
                    <div className="mt-1">
                      <AssuntoPathInline codigo={assunto.codigo} />
                    </div>
                    <div className="mt-1 text-[10px] text-gray-400">
                      Código: {assunto.codigo} • Nível: {assunto.nivel}
                    </div>
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <div className="px-3 py-2 text-xs text-gray-500">
              {query.length < 2
                ? 'Digite ao menos 2 caracteres'
                : value.length > 0 && assuntos?.length === value.length
                ? 'Todos os resultados já foram selecionados'
                : 'Nenhum assunto encontrado'}
            </div>
          )}
        </div>
      )}

      {/* Hint de validação */}
      <p className="mt-1 text-[10px] text-gray-500">
        {value.length > 0
          ? `${value.length} assunto${value.length > 1 ? 's' : ''} selecionado${value.length > 1 ? 's' : ''} • Backspace para remover`
          : 'Digite ao menos 2 caracteres • Somente assuntos cadastrados'}
      </p>
    </div>
  )
}
