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

export interface AssessorComparativo {
  assessor: string
  pecas_elaboradas: number
  pecas_finalizadas: number
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

export interface AssuntoResumo {
  nome: string
  codigo: number
  kpis: KPIValue[]
  top_filhos: GroupCount[]
  timeline: TimelineSeries[]
}

export interface AssuntoNode {
  codigo: number
  nome: string
  nivel: number
  filhos: AssuntoNode[]
}

// --- Partes / Demandantes ---

export interface ParteNormalizada {
  id: number
  nome: string
  cpf: string | null
  cnpj: string | null
  oab: string | null
  tipo_pessoa: string | null
  qtd_processos: number
  qtd_contra_estado: number
  qtd_executado_estado: number
  qtd_advogado: number
  qtd_coreu_estado: number
  valor_total: number
  valor_medio: number
}

export interface PartesKPIs {
  total_pessoas: number
  total_demandantes: number
  total_executados: number
  total_advogados: number
  total_coreus: number
  valor_total_causas: number
  total_processos_com_partes: number
}

export interface ParteProcessoItem {
  cd_processo: string
  numero_processo: string | null
  numero_formatado: string | null
  nome: string
  tipo_parte: string | null
  polo: number | null
  valor_acao: number | null
}

// --- Valores da Causa ---

export interface ValorFaixaItem {
  faixa: string
  qtd: number
  percentual: number
  valor_total: number
  valor_medio: number
}

export interface ValorGroupItem {
  grupo: string
  qtd_processos: number
  valor_total: number
  valor_medio: number
}
