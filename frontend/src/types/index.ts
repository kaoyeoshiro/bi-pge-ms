export interface KPIValue {
  label: string
  valor: number
  formato?: 'inteiro' | 'percentual' | 'decimal'
  variacao_percentual: number | null
}

export interface TimelinePoint {
  periodo: string
  valor: number
}

export interface TimelineSeries {
  nome: string
  dados: TimelinePoint[]
}

export interface GroupCount {
  grupo: string
  total: number
}

export interface PaginatedResponse<T = Record<string, unknown>> {
  items: T[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface FilterOptions {
  chefias: string[]
  procuradores: string[]
  categorias: string[]
  areas: string[]
  anos: number[]
}

export interface ColumnSchema {
  name: string
  label: string
  type: string
}

export interface TableSchema {
  table: string
  label: string
  columns: ColumnSchema[]
  total_rows: number
}

export interface PaginationParams {
  page: number
  page_size: number
  sort_by?: string
  sort_order?: 'asc' | 'desc'
  search?: string
}

export interface GlobalFilters {
  ano?: number | null
  mes?: number | null
  data_inicio?: string | null
  data_fim?: string | null
  chefia?: string[]
  procurador?: string[]
  categoria?: string[]
  area?: string[]
}

// --- Comparativo Procuradores ---

export interface ProcuradorComparativo {
  procurador: string
  processos_novos: number
  pecas_elaboradas: number
  pecas_finalizadas: number
  pendencias: number
  total: number
}

// --- Admin ---

export interface UserRoleItem {
  name: string
  role: 'procurador' | 'assessor'
}

export interface UserRoleListResponse {
  users: UserRoleItem[]
  counts: { procurador: number; assessor: number }
}

export interface UploadResult {
  linhas_importadas: number
  linhas_total_tabela: number
}

export interface TableStat {
  tabela: string
  total: number
}

export interface PopulateResult {
  procuradores: number
  assessores: number
}
