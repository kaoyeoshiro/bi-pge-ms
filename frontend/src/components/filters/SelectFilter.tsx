import { useState, useRef, useEffect } from 'react'

interface SelectFilterProps {
  label: string
  options: string[]
  value: string[]
  onChange: (value: string[]) => void
  single?: boolean
  /** Exibe opção "Selecionar todos" no topo da lista. */
  showSelectAll?: boolean
}

export function SelectFilter({
  label,
  options,
  value,
  onChange,
  single,
  showSelectAll,
}: SelectFilterProps) {
  const [open, setOpen] = useState(false)
  const [search, setSearch] = useState('')
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const filtered = options.filter((o) =>
    o.toLowerCase().includes(search.toLowerCase())
  )

  const allSelected = options.length > 0 && value.length === options.length

  const toggle = (item: string) => {
    if (single) {
      onChange(value.includes(item) ? [] : [item])
      setOpen(false)
    } else {
      onChange(
        value.includes(item)
          ? value.filter((v) => v !== item)
          : [...value, item]
      )
    }
  }

  const toggleAll = () => {
    if (allSelected) {
      onChange([])
    } else {
      onChange([...options])
    }
  }

  // Display inteligente
  let displayValue: string
  if (value.length === 0) {
    displayValue = label
  } else if (showSelectAll && allSelected) {
    displayValue = `Todos ${label.toLowerCase()}`
  } else if (value.length === 1) {
    displayValue = value[0].length > 15 ? value[0].slice(0, 15) + '...' : value[0]
  } else {
    // Para anos, tentar exibir range (ex: "2024-2026")
    const nums = value.map(Number).filter((n) => !isNaN(n))
    if (nums.length === value.length && nums.length > 1) {
      nums.sort((a, b) => a - b)
      const isConsecutive = nums.every((n, i) => i === 0 || n === nums[i - 1] + 1)
      if (isConsecutive) {
        displayValue = `${nums[0]}–${nums[nums.length - 1]}`
      } else {
        displayValue = `${value.length} selecionados`
      }
    } else {
      displayValue = `${value.length} selecionados`
    }
  }

  const checkIcon = (
    <svg className="h-2.5 w-2.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
    </svg>
  )

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
        <div className="absolute left-0 top-full z-50 mt-1 max-h-64 w-64 overflow-hidden rounded-lg border border-gray-200 bg-surface shadow-lg">
          {options.length > 8 && (
            <div className="border-b border-gray-100 p-2">
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Buscar..."
                className="w-full rounded border border-gray-200 px-2 py-1 text-xs focus:border-primary focus:outline-none"
                autoFocus
              />
            </div>
          )}
          <div className="max-h-48 overflow-y-auto p-1">
            {/* Opção "Selecionar todos" */}
            {showSelectAll && !single && !search && (
              <button
                onClick={toggleAll}
                className={`flex w-full items-center gap-2 rounded px-2 py-1.5 text-left text-xs font-medium transition-colors border-b border-gray-100 mb-0.5 ${
                  allSelected
                    ? 'bg-primary/10 text-primary'
                    : 'text-gray-700 hover:bg-gray-50'
                }`}
              >
                <span className={`flex h-3.5 w-3.5 shrink-0 items-center justify-center rounded border ${
                  allSelected ? 'border-primary bg-primary text-white' : 'border-gray-300'
                }`}>
                  {allSelected && checkIcon}
                </span>
                <span>Selecionar todos</span>
              </button>
            )}
            {filtered.map((option) => (
              <button
                key={option}
                onClick={() => toggle(option)}
                className={`flex w-full items-center gap-2 rounded px-2 py-1.5 text-left text-xs transition-colors ${
                  value.includes(option)
                    ? 'bg-primary/10 text-primary font-medium'
                    : 'text-gray-600 hover:bg-gray-50'
                }`}
              >
                {!single && (
                  <span className={`flex h-3.5 w-3.5 shrink-0 items-center justify-center rounded border ${
                    value.includes(option) ? 'border-primary bg-primary text-white' : 'border-gray-300'
                  }`}>
                    {value.includes(option) && checkIcon}
                  </span>
                )}
                <span className="truncate">{option}</span>
              </button>
            ))}
            {filtered.length === 0 && (
              <p className="px-2 py-3 text-center text-xs text-gray-400">Nenhum resultado</p>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
