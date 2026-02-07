import { useState, useMemo, useCallback } from 'react'
import { TopBar } from '../components/layout/TopBar'
import { useAdminStore } from '../stores/useAdminStore'
import {
  useAdminLotacoes,
  useAdminUsers,
  useChefiaOptions,
  usePopulateRoles,
  useTableStats,
  useUpdateCargaReduzida,
  useUpdateLotacao,
  useUpdateUserRole,
  useUploadExcel,
} from '../api/hooks/useAdmin'
import type { ProcuradorLotacao, TableStat } from '../types'

const TABELA_OPTIONS = [
  { value: 'processos_novos', label: 'Processos Novos' },
  { value: 'pecas_elaboradas', label: 'Peças Elaboradas' },
  { value: 'pecas_finalizadas', label: 'Peças Finalizadas' },
  { value: 'pendencias', label: 'Pendências' },
]

// --- Tela de Login ---

function AdminLogin() {
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const login = useAdminStore((s) => s.login)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    const ok = await login(password)
    setLoading(false)
    if (!ok) setError('Senha incorreta.')
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-sm rounded-xl border border-gray-200 bg-white p-8 shadow-lg"
      >
        <h2 className="mb-6 text-center text-xl font-bold text-primary">
          Painel Administrativo
        </h2>
        <label className="mb-2 block text-sm font-medium text-gray-700">
          Senha
        </label>
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="mb-4 w-full rounded-lg border border-gray-300 px-4 py-2 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
          placeholder="Digite a senha de admin"
          autoFocus
        />
        {error && (
          <p className="mb-3 text-sm text-red-600">{error}</p>
        )}
        <button
          type="submit"
          disabled={loading || !password}
          className="w-full rounded-lg bg-primary px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-primary-dark disabled:opacity-50"
        >
          {loading ? 'Verificando...' : 'Entrar'}
        </button>
      </form>
    </div>
  )
}

// --- Tab Classificação de Usuários ---

type RoleFilter = '' | 'procurador' | 'assessor'

const ROLE_FILTER_OPTIONS: { value: RoleFilter; label: string }[] = [
  { value: '', label: 'Todos' },
  { value: 'procurador', label: 'Procuradores' },
  { value: 'assessor', label: 'Assessores' },
]

function UsersTab() {
  const [search, setSearch] = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')
  const [roleFilter, setRoleFilter] = useState<RoleFilter>('')

  const { data, isLoading } = useAdminUsers(
    debouncedSearch || undefined,
    roleFilter || undefined,
  )
  const updateRole = useUpdateUserRole()
  const updateCR = useUpdateCargaReduzida()
  const populateRoles = usePopulateRoles()

  // Debounce simples
  const handleSearchChange = useCallback((value: string) => {
    setSearch(value)
    const timer = setTimeout(() => setDebouncedSearch(value), 300)
    return () => clearTimeout(timer)
  }, [])

  const users = data?.users ?? []
  const counts = data?.counts ?? { procurador: 0, assessor: 0 }

  return (
    <div className="space-y-4">
      {/* Cabeçalho com contadores e botão popular */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex gap-4 text-sm">
          <span className="rounded-full bg-blue-100 px-3 py-1 font-medium text-blue-800">
            {counts.procurador} procuradores
          </span>
          <span className="rounded-full bg-green-100 px-3 py-1 font-medium text-green-800">
            {counts.assessor} assessores
          </span>
        </div>
        <button
          onClick={() => {
            if (confirm('Isso vai recarregar todos os roles a partir dos dados. Continuar?')) {
              populateRoles.mutate()
            }
          }}
          disabled={populateRoles.isPending}
          className="rounded-lg bg-amber-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-amber-700 disabled:opacity-50"
        >
          {populateRoles.isPending ? 'Populando...' : 'Popular Tabela'}
        </button>
      </div>

      {populateRoles.isSuccess && (
        <div className="rounded-lg bg-green-50 p-3 text-sm text-green-800">
          Tabela populada: {populateRoles.data.procuradores} procuradores,{' '}
          {populateRoles.data.assessores} assessores.
        </div>
      )}

      {/* Busca + filtro por tipo */}
      <div className="flex flex-wrap items-center gap-3">
        <input
          type="text"
          value={search}
          onChange={(e) => handleSearchChange(e.target.value)}
          placeholder="Buscar por nome..."
          className="min-w-0 flex-1 rounded-lg border border-gray-300 px-4 py-2 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
        />
        <div className="flex rounded-lg border border-gray-300 bg-gray-50 p-0.5">
          {ROLE_FILTER_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              onClick={() => setRoleFilter(opt.value)}
              className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                roleFilter === opt.value
                  ? 'bg-white text-primary shadow-sm'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {/* Tabela de usuários */}
      <div className="max-h-[60vh] overflow-auto rounded-lg border border-gray-200">
        <table className="w-full text-left text-sm">
          <thead className="sticky top-0 bg-gray-50 text-xs uppercase text-gray-500">
            <tr>
              <th className="px-4 py-3">Nome</th>
              <th className="px-4 py-3 w-40">Classificação</th>
              <th className="px-4 py-3 w-28 text-center">Carga Red.</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {isLoading ? (
              <tr>
                <td colSpan={3} className="px-4 py-8 text-center text-gray-400">
                  Carregando...
                </td>
              </tr>
            ) : users.length === 0 ? (
              <tr>
                <td colSpan={3} className="px-4 py-8 text-center text-gray-400">
                  {debouncedSearch
                    ? 'Nenhum usuário encontrado.'
                    : 'Tabela vazia. Clique em "Popular Tabela" para carregar.'}
                </td>
              </tr>
            ) : (
              users.map((user) => (
                <tr key={user.name} className="hover:bg-gray-50">
                  <td className="px-4 py-2 font-medium text-gray-900">{user.name}</td>
                  <td className="px-4 py-2">
                    <select
                      value={user.role}
                      onChange={(e) =>
                        updateRole.mutate({
                          name: user.name,
                          role: e.target.value,
                        })
                      }
                      className={`rounded-md border px-2 py-1 text-sm font-medium ${
                        user.role === 'procurador'
                          ? 'border-blue-200 bg-blue-50 text-blue-800'
                          : 'border-green-200 bg-green-50 text-green-800'
                      }`}
                    >
                      <option value="procurador">Procurador</option>
                      <option value="assessor">Assessor</option>
                    </select>
                  </td>
                  <td className="px-4 py-2 text-center">
                    <input
                      type="checkbox"
                      checked={user.carga_reduzida}
                      onChange={(e) =>
                        updateCR.mutate({
                          name: user.name,
                          carga_reduzida: e.target.checked,
                        })
                      }
                      className="h-4 w-4 rounded border-gray-300 text-amber-600 accent-amber-600"
                    />
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// --- Tab Atualização de Dados ---

function formatNumber(n: number) {
  return n.toLocaleString('pt-BR')
}

function UploadTab() {
  const [tabela, setTabela] = useState('processos_novos')
  const [modo, setModo] = useState<'substituir' | 'adicionar'>('adicionar')
  const [file, setFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<string[][]>([])

  const uploadExcel = useUploadExcel()
  const { data: stats } = useTableStats()

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0] ?? null
    setFile(selectedFile)
    setPreview([])
    uploadExcel.reset()

    if (!selectedFile) return

    // Preview local usando FileReader (limitado, mas útil para validação visual)
    const reader = new FileReader()
    reader.onload = async () => {
      try {
        // Importar xlsx dinamicamente para preview local
        const XLSX = await import('xlsx')
        const wb = XLSX.read(reader.result, { type: 'array' })
        const ws = wb.Sheets[wb.SheetNames[0]]
        const data = XLSX.utils.sheet_to_json<string[]>(ws, { header: 1 })
        // Primeiras 6 linhas (cabeçalho + 5 dados)
        setPreview(data.slice(0, 6).map((row) => row.map(String)))
      } catch {
        setPreview([])
      }
    }
    reader.readAsArrayBuffer(selectedFile)
  }

  const handleUpload = () => {
    if (!file) return
    if (
      modo === 'substituir' &&
      !confirm(
        `ATENÇÃO: Todos os dados da tabela "${tabela}" serão substituídos. Continuar?`
      )
    ) {
      return
    }
    uploadExcel.mutate({ file, tabela, modo })
  }

  const tabelaLabel = useMemo(
    () => TABELA_OPTIONS.find((t) => t.value === tabela)?.label ?? tabela,
    [tabela]
  )

  return (
    <div className="space-y-6">
      {/* Estatísticas das tabelas */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {(stats ?? []).map((s: TableStat) => {
          const label = TABELA_OPTIONS.find((t) => t.value === s.tabela)?.label ?? s.tabela
          return (
            <div
              key={s.tabela}
              className="rounded-lg border border-gray-200 bg-white p-4 text-center"
            >
              <p className="text-xs text-gray-500">{label}</p>
              <p className="mt-1 text-lg font-bold text-primary">
                {formatNumber(s.total)}
              </p>
            </div>
          )
        })}
      </div>

      {/* Formulário de upload */}
      <div className="rounded-xl border border-gray-200 bg-white p-6 space-y-4">
        <h3 className="text-sm font-semibold text-gray-700">Importar Planilha</h3>

        {/* Seletor de tabela */}
        <div>
          <label className="mb-1 block text-xs font-medium text-gray-600">
            Tabela destino
          </label>
          <select
            value={tabela}
            onChange={(e) => setTabela(e.target.value)}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
          >
            {TABELA_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        {/* Modo de importação */}
        <div>
          <label className="mb-2 block text-xs font-medium text-gray-600">
            Modo de importação
          </label>
          <div className="flex gap-4">
            <label className="flex items-center gap-2 text-sm">
              <input
                type="radio"
                name="modo"
                value="adicionar"
                checked={modo === 'adicionar'}
                onChange={() => setModo('adicionar')}
                className="accent-primary"
              />
              Adicionar ao existente
            </label>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="radio"
                name="modo"
                value="substituir"
                checked={modo === 'substituir'}
                onChange={() => setModo('substituir')}
                className="accent-primary"
              />
              <span className="text-red-600 font-medium">Substituir tudo</span>
            </label>
          </div>
        </div>

        {/* File input */}
        <div>
          <label className="mb-1 block text-xs font-medium text-gray-600">
            Arquivo Excel (.xlsx)
          </label>
          <input
            type="file"
            accept=".xlsx,.xls"
            onChange={handleFileChange}
            className="w-full text-sm file:mr-3 file:rounded-lg file:border-0 file:bg-primary file:px-4 file:py-2 file:text-sm file:font-medium file:text-white hover:file:bg-primary-dark"
          />
        </div>

        {/* Preview */}
        {preview.length > 0 && (
          <div className="overflow-auto rounded-lg border border-gray-200">
            <table className="w-full text-left text-xs">
              <thead className="bg-gray-50 text-gray-500">
                <tr>
                  {preview[0].map((col, i) => (
                    <th key={i} className="px-3 py-2 whitespace-nowrap">
                      {col}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {preview.slice(1).map((row, ri) => (
                  <tr key={ri}>
                    {row.map((cell, ci) => (
                      <td key={ci} className="px-3 py-1.5 whitespace-nowrap text-gray-700">
                        {cell}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="px-3 py-2 text-xs text-gray-400">
              Mostrando primeiras 5 linhas do arquivo
            </p>
          </div>
        )}

        {/* Botão importar */}
        <button
          onClick={handleUpload}
          disabled={!file || uploadExcel.isPending}
          className="rounded-lg bg-primary px-6 py-2.5 text-sm font-medium text-white transition-colors hover:bg-primary-dark disabled:opacity-50"
        >
          {uploadExcel.isPending
            ? 'Importando...'
            : `Importar para ${tabelaLabel}`}
        </button>

        {/* Resultado */}
        {uploadExcel.isSuccess && (
          <div className="rounded-lg bg-green-50 p-4 text-sm text-green-800">
            Importação concluída! {formatNumber(uploadExcel.data.linhas_importadas)}{' '}
            linhas importadas. Total na tabela:{' '}
            {formatNumber(uploadExcel.data.linhas_total_tabela)}.
          </div>
        )}

        {uploadExcel.isError && (
          <div className="rounded-lg bg-red-50 p-4 text-sm text-red-800">
            Erro: {(uploadExcel.error as Error).message}
          </div>
        )}
      </div>
    </div>
  )
}

// --- Tab Lotação de Procuradores ---

function LotacaoTab() {
  const [search, setSearch] = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')
  const [editing, setEditing] = useState<string | null>(null)
  const [editChefias, setEditChefias] = useState<string[]>([])

  const { data: lotacoes, isLoading } = useAdminLotacoes(debouncedSearch || undefined)
  const { data: chefiaOptions } = useChefiaOptions()
  const updateLotacao = useUpdateLotacao()

  const handleSearchChange = useCallback((value: string) => {
    setSearch(value)
    const timer = setTimeout(() => setDebouncedSearch(value), 300)
    return () => clearTimeout(timer)
  }, [])

  const handleStartEdit = (lotacao: ProcuradorLotacao) => {
    setEditing(lotacao.procurador)
    setEditChefias([...lotacao.chefias])
  }

  const handleSave = () => {
    if (!editing) return
    updateLotacao.mutate(
      { name: editing, chefias: editChefias },
      { onSuccess: () => setEditing(null) }
    )
  }

  const handleToggleChefia = (chefia: string) => {
    setEditChefias((prev) =>
      prev.includes(chefia)
        ? prev.filter((c) => c !== chefia)
        : [...prev, chefia]
    )
  }

  return (
    <div className="space-y-4">
      <input
        type="text"
        value={search}
        onChange={(e) => handleSearchChange(e.target.value)}
        placeholder="Buscar procurador..."
        className="w-full rounded-lg border border-gray-300 px-4 py-2 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
      />

      {/* Modal de edição inline */}
      {editing && (
        <div className="rounded-xl border border-blue-200 bg-blue-50 p-4 space-y-3">
          <div className="flex items-center justify-between">
            <p className="text-sm font-semibold text-blue-900">
              Editando: {editing}
            </p>
            <div className="flex gap-2">
              <button
                onClick={handleSave}
                disabled={updateLotacao.isPending}
                className="rounded-lg bg-primary px-4 py-1.5 text-xs font-medium text-white transition-colors hover:bg-primary-dark disabled:opacity-50"
              >
                {updateLotacao.isPending ? 'Salvando...' : 'Salvar'}
              </button>
              <button
                onClick={() => setEditing(null)}
                className="rounded-lg border border-gray-300 px-4 py-1.5 text-xs text-gray-600 hover:bg-gray-100"
              >
                Cancelar
              </button>
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            {(chefiaOptions ?? []).map((chefia) => (
              <button
                key={chefia}
                onClick={() => handleToggleChefia(chefia)}
                className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
                  editChefias.includes(chefia)
                    ? 'bg-primary text-white'
                    : 'bg-white text-gray-600 border border-gray-300 hover:bg-gray-100'
                }`}
              >
                {chefia}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Tabela de lotações */}
      <div className="max-h-[60vh] overflow-auto rounded-lg border border-gray-200">
        <table className="w-full text-left text-sm">
          <thead className="sticky top-0 bg-gray-50 text-xs uppercase text-gray-500">
            <tr>
              <th className="px-4 py-3">Procurador</th>
              <th className="px-4 py-3">Chefias</th>
              <th className="px-4 py-3 w-24">Ação</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {isLoading ? (
              <tr>
                <td colSpan={3} className="px-4 py-8 text-center text-gray-400">
                  Carregando...
                </td>
              </tr>
            ) : !lotacoes?.length ? (
              <tr>
                <td colSpan={3} className="px-4 py-8 text-center text-gray-400">
                  {debouncedSearch
                    ? 'Nenhum procurador encontrado.'
                    : 'Nenhuma lotação cadastrada.'}
                </td>
              </tr>
            ) : (
              lotacoes.map((lot) => (
                <tr key={lot.procurador} className="hover:bg-gray-50">
                  <td className="px-4 py-2 font-medium text-gray-900">{lot.procurador}</td>
                  <td className="px-4 py-2">
                    <div className="flex flex-wrap gap-1">
                      {lot.chefias.map((c) => (
                        <span
                          key={c}
                          className="rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-700"
                        >
                          {c}
                        </span>
                      ))}
                    </div>
                  </td>
                  <td className="px-4 py-2">
                    <button
                      onClick={() => handleStartEdit(lot)}
                      className="text-xs font-medium text-primary hover:text-primary-dark"
                    >
                      Editar
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// --- Página Principal Admin ---

export function AdminPage() {
  const isAuthenticated = useAdminStore((s) => s.isAuthenticated)
  const logout = useAdminStore((s) => s.logout)
  const [activeTab, setActiveTab] = useState<'users' | 'lotacao' | 'upload'>('users')

  if (!isAuthenticated) {
    return <AdminLogin />
  }

  return (
    <>
      <TopBar title="Painel Administrativo" />
      <div className="space-y-4 p-4 sm:p-6">
        {/* Header com tabs e botão sair */}
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex gap-1 rounded-lg bg-gray-100 p-1">
            <button
              onClick={() => setActiveTab('users')}
              className={`rounded-md px-3 py-1.5 text-xs font-medium transition-colors sm:px-4 sm:py-2 sm:text-sm ${
                activeTab === 'users'
                  ? 'bg-white text-primary shadow-sm'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              Usuários
            </button>
            <button
              onClick={() => setActiveTab('lotacao')}
              className={`rounded-md px-3 py-1.5 text-xs font-medium transition-colors sm:px-4 sm:py-2 sm:text-sm ${
                activeTab === 'lotacao'
                  ? 'bg-white text-primary shadow-sm'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              Lotação
            </button>
            <button
              onClick={() => setActiveTab('upload')}
              className={`rounded-md px-3 py-1.5 text-xs font-medium transition-colors sm:px-4 sm:py-2 sm:text-sm ${
                activeTab === 'upload'
                  ? 'bg-white text-primary shadow-sm'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              Dados
            </button>
          </div>
          <button
            onClick={logout}
            className="rounded-lg border border-gray-300 px-3 py-1.5 text-xs text-gray-600 transition-colors hover:bg-gray-50 sm:px-4 sm:py-2 sm:text-sm"
          >
            Sair
          </button>
        </div>

        {/* Conteúdo da tab */}
        {activeTab === 'users' && <UsersTab />}
        {activeTab === 'lotacao' && <LotacaoTab />}
        {activeTab === 'upload' && <UploadTab />}
      </div>
    </>
  )
}
