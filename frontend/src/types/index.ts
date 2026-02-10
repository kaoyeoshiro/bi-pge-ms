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
  anos?: number[]
  mes?: number | null
  data_inicio?: string | null
  data_fim?: string | null
  chefia?: string[]
  procurador?: string[]
  categoria?: string[]
  area?: string[]
}

export interface AssuntoGroupCount extends GroupCount {
  codigo: number
  has_children: boolean
}

export interface AssuntoResumo {
  nome: string
  codigo: number
  kpis: KPIValue[]
  top_filhos: GroupCount[]
  timeline: TimelineSeries[]
}

// --- Médias Chefia ---

export interface ChefiaMediaKPI {
  label: string
  total: number
  media: number
}

export interface ChefiaMediasResponse {
  kpis: ChefiaMediaKPI[]
  timeline: TimelineSeries[]
  units_count: number
  unit_label: string
  person_count: number
}

// --- Comparativo Procuradores ---

export interface ProcuradorComparativo {
  procurador: string
  pecas_finalizadas: number
  pendencias: number
  total: number
}

// --- Admin ---

export interface UserRoleItem {
  name: string
  role: 'procurador' | 'assessor'
  carga_reduzida: boolean
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

export interface ProcuradorLotacao {
  procurador: string
  chefias: string[]
}

// --- Ocultação de Produção ---

export interface HiddenProcuradorRule {
  id: number
  procurador_name: string
  chefia: string | null
  start_date: string
  end_date: string
  is_active: boolean
  reason: string | null
  created_by: string
  created_at: string
  updated_at: string | null
}

export interface HiddenProcuradorCreate {
  procurador_name: string
  chefia?: string | null
  start_date: string
  end_date: string
  reason?: string | null
}

export interface HiddenProcuradorUpdate {
  start_date?: string
  end_date?: string
  is_active?: boolean
  reason?: string
}

// --- Assuntos ---

export interface AssuntoNode {
  codigo: number
  nome: string
  nivel: number
  filhos: AssuntoNode[]
}
