import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import api from '../client'
import type {
  PopulateResult,
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
