import { useState, useRef, useEffect, useCallback, useMemo } from 'react'
import type { AssuntoNode } from '../../types'

interface TreeSelectFilterProps {
  label: string
  tree: AssuntoNode[]
  value: number[]
  onChange: (value: number[]) => void
}

/** Coleta todos os códigos de um nó e seus descendentes. */
function collectCodes(node: AssuntoNode): number[] {
  const codes = [node.codigo]
  for (const filho of node.filhos) {
    codes.push(...collectCodes(filho))
  }
  return codes
}

/** Coleta todos os códigos de toda a árvore. */
function collectAllCodes(tree: AssuntoNode[]): number[] {
  const codes: number[] = []
  for (const node of tree) {
    codes.push(...collectCodes(node))
  }
  return codes
}

/** Filtra a árvore preservando hierarquia (pais de nós que batem). */
function filterTree(nodes: AssuntoNode[], search: string): AssuntoNode[] {
  const lower = search.toLowerCase()
  const result: AssuntoNode[] = []
  for (const node of nodes) {
    const matches = node.nome.toLowerCase().includes(lower)
    const filteredChildren = filterTree(node.filhos, search)
    if (matches || filteredChildren.length > 0) {
      result.push({
        ...node,
        filhos: matches ? node.filhos : filteredChildren,
      })
    }
  }
  return result
}

function TreeNode({
  node,
  selected,
  onToggle,
  expandedSet,
  toggleExpanded,
  depth,
}: {
  node: AssuntoNode
  selected: Set<number>
  onToggle: (codes: number[], add: boolean) => void
  expandedSet: Set<number>
  toggleExpanded: (codigo: number) => void
  depth: number
}) {
  const allCodes = useMemo(() => collectCodes(node), [node])
  const isChecked = allCodes.every((c) => selected.has(c))
  const isPartial = !isChecked && allCodes.some((c) => selected.has(c))
  const hasChildren = node.filhos.length > 0
  const isExpanded = expandedSet.has(node.codigo)

  const handleCheck = () => {
    onToggle(allCodes, !isChecked)
  }

  const checkIcon = (
    <svg className="h-2.5 w-2.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
    </svg>
  )

  const minusIcon = (
    <svg className="h-2.5 w-2.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M5 12h14" />
    </svg>
  )

  return (
    <div>
      <div
        className="flex items-center gap-1 rounded px-1 py-1 text-xs hover:bg-gray-50 transition-colors"
        style={{ paddingLeft: `${depth * 16 + 4}px` }}
      >
        {/* Seta de expandir/colapsar */}
        {hasChildren ? (
          <button
            onClick={() => toggleExpanded(node.codigo)}
            className="flex h-4 w-4 shrink-0 items-center justify-center text-gray-400 hover:text-gray-600"
          >
            <svg
              className={`h-3 w-3 transition-transform ${isExpanded ? 'rotate-90' : ''}`}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
            </svg>
          </button>
        ) : (
          <span className="w-4 shrink-0" />
        )}

        {/* Checkbox */}
        <button
          onClick={handleCheck}
          className={`flex h-3.5 w-3.5 shrink-0 items-center justify-center rounded border ${
            isChecked
              ? 'border-primary bg-primary text-white'
              : isPartial
                ? 'border-primary bg-primary/30 text-white'
                : 'border-gray-300'
          }`}
        >
          {isChecked && checkIcon}
          {isPartial && !isChecked && minusIcon}
        </button>

        {/* Nome */}
        <span
          className={`truncate cursor-pointer ${
            isChecked ? 'text-primary font-medium' : 'text-gray-700'
          }`}
          onClick={handleCheck}
          title={node.nome}
        >
          {node.nome}
        </span>
      </div>

      {/* Filhos */}
      {hasChildren && isExpanded && (
        <div>
          {node.filhos.map((filho) => (
            <TreeNode
              key={filho.codigo}
              node={filho}
              selected={selected}
              onToggle={onToggle}
              expandedSet={expandedSet}
              toggleExpanded={toggleExpanded}
              depth={depth + 1}
            />
          ))}
        </div>
      )}
    </div>
  )
}

export function TreeSelectFilter({ label, tree, value, onChange }: TreeSelectFilterProps) {
  const [open, setOpen] = useState(false)
  const [search, setSearch] = useState('')
  const [expanded, setExpanded] = useState<Set<number>>(new Set())
  const ref = useRef<HTMLDivElement>(null)

  const selectedSet = useMemo(() => new Set(value), [value])

  // Fechar ao clicar fora
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  // Filtrar árvore por busca
  const displayTree = useMemo(() => {
    if (!search) return tree
    return filterTree(tree, search)
  }, [tree, search])

  // Auto-expandir todos os nós quando buscando
  useEffect(() => {
    if (search) {
      const allCodes = collectAllCodes(displayTree)
      setExpanded(new Set(allCodes))
    }
  }, [search, displayTree])

  const toggleExpanded = useCallback((codigo: number) => {
    setExpanded((prev) => {
      const next = new Set(prev)
      if (next.has(codigo)) {
        next.delete(codigo)
      } else {
        next.add(codigo)
      }
      return next
    })
  }, [])

  const handleToggle = useCallback(
    (codes: number[], add: boolean) => {
      const next = new Set(value)
      for (const c of codes) {
        if (add) {
          next.add(c)
        } else {
          next.delete(c)
        }
      }
      onChange(Array.from(next))
    },
    [value, onChange]
  )

  // Texto do botão
  let displayValue: string
  if (value.length === 0) {
    displayValue = label
  } else if (value.length === 1) {
    // Buscar nome do assunto selecionado
    const findName = (nodes: AssuntoNode[]): string | null => {
      for (const n of nodes) {
        if (n.codigo === value[0]) return n.nome
        const child = findName(n.filhos)
        if (child) return child
      }
      return null
    }
    const name = findName(tree)
    displayValue = name
      ? name.length > 20
        ? name.slice(0, 20) + '...'
        : name
      : `${value.length} assunto`
  } else {
    displayValue = `${value.length} assuntos`
  }

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(!open)}
        className={`flex items-center gap-1 rounded-lg border px-3 py-1.5 text-xs transition-colors ${
          value.length > 0
            ? 'border-primary bg-primary/5 text-primary font-medium'
            : 'border-gray-300 text-gray-600 hover:border-gray-400'
        }`}
      >
        {displayValue}
        <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {open && (
        <div className="absolute left-0 top-full z-50 mt-1 w-80 overflow-hidden rounded-lg border border-gray-200 bg-surface shadow-lg">
          {/* Busca */}
          <div className="border-b border-gray-100 p-2">
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Buscar assunto..."
              className="w-full rounded border border-gray-200 px-2 py-1 text-xs focus:border-primary focus:outline-none"
              autoFocus
            />
          </div>

          {/* Árvore */}
          <div className="max-h-72 overflow-y-auto p-1">
            {displayTree.length === 0 ? (
              <p className="px-2 py-3 text-center text-xs text-gray-400">Nenhum resultado</p>
            ) : (
              displayTree.map((node) => (
                <TreeNode
                  key={node.codigo}
                  node={node}
                  selected={selectedSet}
                  onToggle={handleToggle}
                  expandedSet={expanded}
                  toggleExpanded={toggleExpanded}
                  depth={0}
                />
              ))
            )}
          </div>

          {/* Rodapé com contador e limpar */}
          {value.length > 0 && (
            <div className="flex items-center justify-between border-t border-gray-100 px-3 py-1.5">
              <span className="text-xs text-gray-500">{value.length} selecionado(s)</span>
              <button
                onClick={() => onChange([])}
                className="text-xs text-gray-400 hover:text-gray-600"
              >
                Limpar
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
