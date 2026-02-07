import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import api from '../client'
import type {
  HiddenProcuradorCreate,
  HiddenProcuradorRule,
  HiddenProcuradorUpdate,
  PopulateResult,
  ProcuradorLotacao,
  TableStat,
  UploadResult,
  UserRoleListResponse,
} from '../../types'

function getAuthHeader() {
  const token = sessionStorage.getItem('admin_token')
  return { Authorization: `Bearer ${token}` }
}

/** Lista usuários com roles e contagens, com filtro opcional por tipo. */
export function useAdminUsers(search?: string, role?: string) {
  return useQuery<UserRoleListResponse>({
    queryKey: ['admin-users', search, role],
    queryFn: async () => {
      const params = new URLSearchParams()
      if (search) params.set('search', search)
      if (role) params.set('role', role)
      const qs = params.toString()
      const { data } = await api.get(`/admin/users${qs ? `?${qs}` : ''}`, {
        headers: getAuthHeader(),
      })
      return data
    },
    staleTime: 30_000,
  })
}

/** Mutation para atualizar role de um usuário. */
export function useUpdateUserRole() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ name, role }: { name: string; role: string }) => {
      const { data } = await api.put(
        `/admin/users/${encodeURIComponent(name)}/role`,
        { role },
        { headers: getAuthHeader() }
      )
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-users'] })
    },
  })
}

/** Mutation para atualizar roles em lote. */
export function useUpdateUserRolesBulk() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (users: { name: string; role: string }[]) => {
      const { data } = await api.put(
        '/admin/users/bulk',
        { users },
        { headers: getAuthHeader() }
      )
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-users'] })
    },
  })
}

/** Mutation para popular tabela de roles. */
export function usePopulateRoles() {
  const queryClient = useQueryClient()
  return useMutation<PopulateResult>({
    mutationFn: async () => {
      const { data } = await api.post('/admin/populate-roles', null, {
        headers: getAuthHeader(),
      })
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-users'] })
    },
  })
}

/** Mutation para upload de planilha Excel. */
export function useUploadExcel() {
  const queryClient = useQueryClient()
  return useMutation<UploadResult, Error, { file: File; tabela: string; modo: string }>({
    mutationFn: async ({ file, tabela, modo }) => {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('tabela', tabela)
      formData.append('modo', modo)

      const { data } = await api.post('/admin/upload', formData, {
        headers: {
          ...getAuthHeader(),
          'Content-Type': 'multipart/form-data',
        },
        timeout: 300_000, // 5 minutos para uploads grandes
      })
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-table-stats'] })
    },
  })
}

/** Contagem de linhas por tabela. */
export function useTableStats() {
  return useQuery<TableStat[]>({
    queryKey: ['admin-table-stats'],
    queryFn: async () => {
      const { data } = await api.get('/admin/tables/stats', {
        headers: getAuthHeader(),
      })
      return data
    },
    staleTime: 30_000,
  })
}

/** Mutation para atualizar carga reduzida de um usuário. */
export function useUpdateCargaReduzida() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ name, carga_reduzida }: { name: string; carga_reduzida: boolean }) => {
      const { data } = await api.put(
        `/admin/users/${encodeURIComponent(name)}/carga-reduzida`,
        { carga_reduzida },
        { headers: getAuthHeader() }
      )
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-users'] })
      queryClient.invalidateQueries({ queryKey: ['carga-reduzida'] })
    },
  })
}

/** Lista lotações agrupadas por procurador. */
export function useAdminLotacoes(search?: string) {
  return useQuery<ProcuradorLotacao[]>({
    queryKey: ['admin-lotacoes', search],
    queryFn: async () => {
      const params = new URLSearchParams()
      if (search) params.set('search', search)
      const qs = params.toString()
      const { data } = await api.get(`/admin/lotacoes${qs ? `?${qs}` : ''}`, {
        headers: getAuthHeader(),
      })
      return data
    },
    staleTime: 30_000,
  })
}

/** Mutation para atualizar lotação de um procurador. */
export function useUpdateLotacao() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ name, chefias }: { name: string; chefias: string[] }) => {
      const { data } = await api.put(
        `/admin/lotacoes/${encodeURIComponent(name)}`,
        { chefias },
        { headers: getAuthHeader() }
      )
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-lotacoes'] })
    },
  })
}

/** Lista de chefias disponíveis (normalizadas). */
export function useChefiaOptions() {
  return useQuery<string[]>({
    queryKey: ['admin-chefias-disponiveis'],
    queryFn: async () => {
      const { data } = await api.get('/admin/chefias-disponiveis', {
        headers: getAuthHeader(),
      })
      return data
    },
    staleTime: 5 * 60 * 1000,
  })
}

// --- Ocultação de Produção ---

/** Lista regras de ocultação de produção. */
export function useHiddenProducaoRules(onlyActive = true) {
  return useQuery<HiddenProcuradorRule[]>({
    queryKey: ['admin-hidden-producao', onlyActive],
    queryFn: async () => {
      const { data } = await api.get(
        `/admin/hidden-producao?only_active=${onlyActive}`,
        { headers: getAuthHeader() }
      )
      return data
    },
    staleTime: 30_000,
  })
}

/** Mutation para criar regra de ocultação. */
export function useCreateHiddenRule() {
  const queryClient = useQueryClient()
  return useMutation<HiddenProcuradorRule, Error, HiddenProcuradorCreate>({
    mutationFn: async (body) => {
      const { data } = await api.post('/admin/hidden-producao', body, {
        headers: getAuthHeader(),
      })
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-hidden-producao'] })
    },
  })
}

/** Mutation para atualizar regra de ocultação. */
export function useUpdateHiddenRule() {
  const queryClient = useQueryClient()
  return useMutation<
    HiddenProcuradorRule,
    Error,
    { id: number; data: HiddenProcuradorUpdate }
  >({
    mutationFn: async ({ id, data: body }) => {
      const { data } = await api.put(`/admin/hidden-producao/${id}`, body, {
        headers: getAuthHeader(),
      })
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-hidden-producao'] })
    },
  })
}

/** Mutation para remover regra de ocultação. */
export function useDeleteHiddenRule() {
  const queryClient = useQueryClient()
  return useMutation<void, Error, number>({
    mutationFn: async (id) => {
      await api.delete(`/admin/hidden-producao/${id}`, {
        headers: getAuthHeader(),
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-hidden-producao'] })
    },
  })
}
