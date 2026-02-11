import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../client'

interface AccessCountResponse {
  total_accesses: number
}

interface TrackAccessResponse {
  success: boolean
  total_accesses: number
}

/**
 * Hook para rastrear e obter contagem de acessos ao sistema.
 */
export function useAccessCounter() {
  const queryClient = useQueryClient()

  const { data: countData, isLoading } = useQuery<AccessCountResponse>({
    queryKey: ['accessCount'],
    queryFn: async () => {
      const response = await api.get<AccessCountResponse>('/analytics/access-count')
      return response.data
    },
    staleTime: 1000 * 60 * 5, // 5 minutos
    refetchOnWindowFocus: false,
  })

  const trackAccess = useMutation<TrackAccessResponse>({
    mutationFn: async () => {
      const response = await api.post<TrackAccessResponse>('/analytics/track-access')
      return response.data
    },
    onSuccess: (data) => {
      // Atualiza cache com novo total
      queryClient.setQueryData<AccessCountResponse>(['accessCount'], {
        total_accesses: data.total_accesses,
      })
    },
  })

  return {
    totalAccesses: countData?.total_accesses ?? 0,
    isLoading,
    trackAccess: trackAccess.mutate,
  }
}
