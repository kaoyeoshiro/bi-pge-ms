import { useState } from 'react'
import { useFilterParams } from '../../api/hooks/useFilterParams'
import api, { buildQueryString } from '../../api/client'

interface ExportButtonProps {
  table: string
}

interface ExportInfo {
  total_rows: number
  max_rows_per_file: number
  will_be_limited: boolean
  exported_rows: number
  warning: string | null
}

export function ExportButton({ table }: ExportButtonProps) {
  const params = useFilterParams()
  const [isChecking, setIsChecking] = useState(false)
  const [isDownloading, setIsDownloading] = useState(false)

  const download = async (format: 'csv' | 'excel') => {
    try {
      setIsChecking(true)

      // Buscar informações sobre o export
      const qs = buildQueryString(params)
      const { data: info } = await api.get<ExportInfo>(`/export/${table}/info${qs}`)

      // Avisar usuário se houver muitas linhas
      if (info.will_be_limited) {
        const confirmed = window.confirm(
          `⚠️ ATENÇÃO: Export com Volume Grande\n\n` +
          `Total de linhas: ${info.total_rows.toLocaleString('pt-BR')}\n` +
          `Linhas que serão exportadas: ${info.exported_rows.toLocaleString('pt-BR')}\n\n` +
          `${info.warning}\n\n` +
          `Deseja continuar com o download?`
        )
        if (!confirmed) return
      }

      // Avisar sobre Excel especificamente
      if (format === 'excel' && info.total_rows > 50000) {
        const switchToCsv = window.confirm(
          `⚠️ RECOMENDAÇÃO: Use CSV para exports grandes\n\n` +
          `Excel tem limite de ${info.max_rows_per_file.toLocaleString('pt-BR')} linhas e pode travar.\n` +
          `CSV suporta volumes maiores e é mais rápido.\n\n` +
          `Deseja baixar em CSV ao invés de Excel?`
        )
        if (switchToCsv) {
          format = 'csv'
        }
      }

      setIsChecking(false)
      setIsDownloading(true)

      // Iniciar download
      window.open(`/api/export/${table}/${format}${qs}`, '_blank')

      // Reset após delay (tempo estimado de download)
      setTimeout(() => setIsDownloading(false), 3000)

    } catch (error) {
      console.error('Erro ao verificar export:', error)
      // Fallback: fazer download direto mesmo sem informações
      const qs = buildQueryString(params)
      window.open(`/api/export/${table}/${format}${qs}`, '_blank')
    } finally {
      setIsChecking(false)
      setIsDownloading(false)
    }
  }

  return (
    <div className="flex items-center gap-1">
      <button
        onClick={() => download('csv')}
        disabled={isChecking || isDownloading}
        className="rounded border border-gray-300 px-2 py-1 text-xs text-gray-600 hover:bg-gray-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        title="Exportar em CSV (recomendado para volumes grandes)"
      >
        {isChecking ? (
          <span className="flex items-center gap-1">
            <div className="h-3 w-3 animate-spin rounded-full border-2 border-gray-400 border-t-transparent" />
            CSV
          </span>
        ) : isDownloading ? (
          <span className="flex items-center gap-1">
            <svg className="h-3 w-3 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
            CSV
          </span>
        ) : (
          'CSV'
        )}
      </button>
      <button
        onClick={() => download('excel')}
        disabled={isChecking || isDownloading}
        className="rounded border border-gray-300 px-2 py-1 text-xs text-gray-600 hover:bg-gray-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        title="Exportar em Excel (limite de 100.000 linhas)"
      >
        {isChecking ? (
          <span className="flex items-center gap-1">
            <div className="h-3 w-3 animate-spin rounded-full border-2 border-gray-400 border-t-transparent" />
            Excel
          </span>
        ) : isDownloading ? (
          <span className="flex items-center gap-1">
            <svg className="h-3 w-3 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
            Excel
          </span>
        ) : (
          'Excel'
        )}
      </button>
    </div>
  )
}
