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
  assuntos: number[]
  valorMin: number | null
  valorMax: number | null

  setAnos: (anos: number[]) => void
  setMes: (mes: number | null) => void
  setDataInicio: (data: string | null) => void
  setDataFim: (data: string | null) => void
  setChefias: (chefias: string[]) => void
  setProcuradores: (procuradores: string[]) => void
  setCategorias: (categorias: string[]) => void
  setAreas: (areas: string[]) => void
  setAssuntos: (assuntos: number[]) => void
  setValorFaixa: (min: number | null, max: number | null) => void
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
  assuntos: [] as number[],
  valorMin: null as number | null,
  valorMax: null as number | null,
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
  setAssuntos: (assuntos) => set({ assuntos }),
  setValorFaixa: (valorMin, valorMax) => set({ valorMin, valorMax }),

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
    if (state.assuntos.length) params.assunto = state.assuntos.join(',')
    if (state.valorMin !== null) params.valor_min = String(state.valorMin)
    if (state.valorMax !== null) params.valor_max = String(state.valorMax)

    return params
  },
}))
