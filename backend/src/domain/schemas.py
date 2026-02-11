"""Schemas Pydantic v2 para respostas da API."""

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, model_validator


class KPIValue(BaseModel):
    """Valor de um indicador-chave com variação percentual."""

    label: str
    valor: float
    formato: str = "inteiro"  # "inteiro", "percentual", "decimal"
    variacao_percentual: float | None = None


class TimelinePoint(BaseModel):
    """Ponto em uma série temporal."""

    periodo: str
    valor: int


class TimelineSeries(BaseModel):
    """Série temporal nomeada."""

    nome: str
    dados: list[TimelinePoint]


class GroupCount(BaseModel):
    """Contagem agrupada por uma dimensão."""

    grupo: str
    total: int


class PaginatedResponse(BaseModel):
    """Resposta paginada genérica."""

    items: list[dict[str, Any]]
    total: int
    page: int
    page_size: int
    total_pages: int


class FilterOptions(BaseModel):
    """Opções disponíveis para os filtros globais."""

    chefias: list[str]
    procuradores: list[str]
    categorias: list[str]
    areas: list[str]
    anos: list[int]


class ProcuradorComparativo(BaseModel):
    """Métricas de procurador para comparativo dentro de uma chefia.

    Apenas pecas_finalizadas e pendencias.
    Processos novos removido: titularidade muda ao longo do tempo.
    Peças elaboradas é métrica de assessor e não aparece aqui.
    """

    procurador: str
    pecas_finalizadas: int = 0
    pendencias: int = 0
    total: int = 0


class AssessorComparativo(BaseModel):
    """Métricas de assessor para comparativo dentro de uma chefia.

    Peças elaboradas (usuario_criacao) e finalizadas (usuario_finalizacao).
    Assessores não pegam pendências.
    """

    assessor: str
    pecas_elaboradas: int = 0
    pecas_finalizadas: int = 0
    total: int = 0


class ColumnSchema(BaseModel):
    """Schema de uma coluna para o Data Explorer."""

    name: str
    label: str
    type: str


class TableSchema(BaseModel):
    """Schema de uma tabela para o Data Explorer."""

    table: str
    label: str
    columns: list[ColumnSchema]
    total_rows: int


class ChefiaMediaKPI(BaseModel):
    """KPI com total e média para visão de chefia."""

    label: str
    total: int
    media: float


class ChefiaMediasResponse(BaseModel):
    """Resposta com KPIs em totais/médias e timeline filtrada."""

    kpis: list[ChefiaMediaKPI]
    timeline: list[TimelineSeries]
    units_count: int
    unit_label: str
    person_count: int = 1


# --- Ocultação de Produção ---


class HiddenProcuradorCreate(BaseModel):
    """Dados para criar regra de ocultação de produção."""

    procurador_name: str
    chefia: str | None = None
    start_date: date
    end_date: date
    reason: str | None = None

    @model_validator(mode="after")
    def validate_dates(self):
        if self.start_date > self.end_date:
            raise ValueError("start_date deve ser anterior ou igual a end_date")
        return self


class HiddenProcuradorUpdate(BaseModel):
    """Dados para atualizar regra de ocultação."""

    start_date: date | None = None
    end_date: date | None = None
    is_active: bool | None = None
    reason: str | None = None


class HiddenProcuradorResponse(BaseModel):
    """Resposta com dados de uma regra de ocultação."""

    id: int
    procurador_name: str
    chefia: str | None
    start_date: date
    end_date: date
    is_active: bool
    reason: str | None
    created_by: str
    created_at: datetime
    updated_at: datetime | None


# --- Assuntos ---


class AssuntoGroupCount(GroupCount):
    """Contagem agrupada com código do assunto e flag de filhos."""

    codigo: int
    has_children: bool


class AssuntoNode(BaseModel):
    """Nó da árvore hierárquica de assuntos."""

    codigo: int
    nome: str
    nivel: int
    filhos: list["AssuntoNode"] = []


class AssuntoResumoResponse(BaseModel):
    """Resumo completo de um nó de assunto: KPIs, filhos e timeline."""

    nome: str
    codigo: int
    kpis: dict[str, KPIValue]
    top_filhos: list[AssuntoGroupCount] = []
    timeline: list[TimelineSeries] = []
