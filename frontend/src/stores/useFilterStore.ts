import { create } from 'zustand'

interface FilterState {
  anos: number[]
  mes: number | null
  dataInicio: string | null
  dataFim: string | null
  chefias: string[]
  procuradores: string[]
  categorias: string[]
  areas: string[]

  setAnos: (anos: number[]) => void
  setMes: (mes: number | null) => void
  setDataInicio: (data: string | null) => void
  setDataFim: (data: string | null) => void
  setChefias: (chefias: string[]) => void
  setProcuradores: (procuradores: string[]) => void
  setCategorias: (categorias: string[]) => void
  setAreas: (areas: string[]) => void
  clearAll: () => void
  toQueryParams: () => Record<string, string | string[]>
}

const initialState = {
  anos: [] as number[],
  mes: null as number | null,
  dataInicio: null as string | null,
  dataFim: null as string | null,
  chefias: [] as string[],
  procuradores: [] as string[],
  categorias: [] as string[],
  areas: [] as string[],
}

export const useFilterStore = create<FilterState>((set, get) => ({
  ...initialState,

  setAnos: (anos) => set({ anos }),
  setMes: (mes) => set({ mes }),
  setDataInicio: (dataInicio) => set({ dataInicio }),
  setDataFim: (dataFim) => set({ dataFim }),
  setChefias: (chefias) => set({ chefias }),
  setProcuradores: (procuradores) => set({ procuradores }),
  setCategorias: (categorias) => set({ categorias }),
  setAreas: (areas) => set({ areas }),

  clearAll: () => set(initialState),

  toQueryParams: () => {
    const state = get()
    const params: Record<string, string | string[]> = {}

    if (state.anos.length) params.anos = state.anos.map(String)
    if (state.mes) params.mes = String(state.mes)
    if (state.dataInicio) params.data_inicio = state.dataInicio
    if (state.dataFim) params.data_fim = state.dataFim
    if (state.chefias.length) params.chefia = state.chefias
    if (state.procuradores.length) params.procurador = state.procuradores
    if (state.categorias.length) params.categoria = state.categorias
    if (state.areas.length) params.area = state.areas

    return params
  },
}))
