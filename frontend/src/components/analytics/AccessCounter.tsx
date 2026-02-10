import { useEffect } from 'react'
import { Eye } from 'lucide-react'
import { useAccessCounter } from '../../api/hooks/useAccessCounter'

/**
 * Contador de acessos fixo no canto inferior esquerdo da tela.
 * Registra um acesso ao carregar e exibe o total.
 */
export function AccessCounter() {
  const { totalAccesses, isLoading, trackAccess } = useAccessCounter()

  useEffect(() => {
    // Registra acesso ao montar o componente
    trackAccess()
  }, [trackAccess])

  if (isLoading) {
    return null
  }

  return (
    <div className="fixed bottom-4 left-4 z-50 flex items-center gap-2 rounded-lg border border-zinc-700 bg-zinc-800/90 px-3 py-2 text-sm shadow-lg backdrop-blur-sm md:bottom-6 md:left-6">
      <Eye className="size-4 text-zinc-400" />
      <span className="text-zinc-300">
        <span className="font-semibold text-zinc-100">{totalAccesses.toLocaleString('pt-BR')}</span>
        {' acessos'}
      </span>
    </div>
  )
}
