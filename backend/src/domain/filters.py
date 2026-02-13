"""Definições de filtros globais e parâmetros de paginação."""

from dataclasses import dataclass, field
from datetime import date


@dataclass
class GlobalFilters:
    """Filtros globais compartilhados por todos os endpoints de agregação."""

    anos: list[int] = field(default_factory=list)
    mes: int | None = None
    data_inicio: date | None = None
    data_fim: date | None = None
    chefia: list[str] = field(default_factory=list)
    procurador: list[str] = field(default_factory=list)
    categoria: list[str] = field(default_factory=list)
    area: list[str] = field(default_factory=list)
    assessor: list[str] = field(default_factory=list)
    assunto: list[int] = field(default_factory=list)
    valor_min: float | None = None
    valor_max: float | None = None
    exclude_hidden: bool = True
    exclude_no_pendencias: bool = True


@dataclass
class PaginationParams:
    """Parâmetros de paginação server-side."""

    page: int = 1
    page_size: int = 25
    sort_by: str | None = None
    sort_order: str = "desc"
    search: str | None = None
