"""Schemas Pydantic v2 para respostas da API."""

from typing import Any

from pydantic import BaseModel


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
    """Métricas de um procurador para comparativo dentro de uma chefia."""

    procurador: str
    processos_novos: int = 0
    pecas_elaboradas: int = 0
    pecas_finalizadas: int = 0
    pendencias: int = 0
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
