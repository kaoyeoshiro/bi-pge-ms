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
    <div className="fixed bottom-3 left-3 z-50 flex items-center gap-1.5 text-xs text-zinc-500">
      <Eye className="size-3.5" />
      <span>{totalAccesses.toLocaleString('pt-BR')}</span>
    </div>
  )
}
