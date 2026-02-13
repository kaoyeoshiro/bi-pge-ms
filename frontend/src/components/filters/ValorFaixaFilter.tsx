import { useFilterStore } from '../../stores/useFilterStore'

const FAIXAS = [
  { label: 'Todas', min: null, max: null },
  { label: 'Até R$ 10 mil', min: null, max: 9_999.99 },
  { label: 'R$ 10 mil – 100 mil', min: 10_000, max: 99_999.99 },
  { label: 'R$ 100 mil – 1 mi', min: 100_000, max: 999_999.99 },
  { label: 'Acima de R$ 1 mi', min: 1_000_000, max: null },
] as const

export function ValorFaixaFilter() {
  const valorMin = useFilterStore((s) => s.valorMin)
  const valorMax = useFilterStore((s) => s.valorMax)
  const setValorFaixa = useFilterStore((s) => s.setValorFaixa)

  const isActive = (faixa: (typeof FAIXAS)[number]) =>
    valorMin === faixa.min && valorMax === faixa.max

  return (
    <div className="flex flex-wrap items-center gap-1.5 sm:gap-2">
      <span className="text-xs font-medium text-gray-500">Valor da causa:</span>
      {FAIXAS.map((faixa) => (
        <button
          key={faixa.label}
          onClick={() => setValorFaixa(faixa.min, faixa.max)}
          className={`rounded-lg px-2.5 py-1 text-xs font-medium transition-colors ${
            isActive(faixa)
              ? 'bg-primary text-white shadow-sm'
              : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
          }`}
        >
          {faixa.label}
        </button>
      ))}
    </div>
  )
}
