"""Serviço do Data Explorer genérico."""

from datetime import datetime

from sqlalchemy import BigInteger, Integer, String, Text, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.enums import TableName
from src.domain.filters import GlobalFilters, PaginationParams
from src.domain.models import TABLE_MODEL_MAP
from src.domain.schemas import ColumnSchema, PaginatedResponse, TableSchema
from src.repositories.base_repository import BaseRepository
from src.services.cache import cached

# Labels amigáveis em pt-BR para colunas
COLUMN_LABELS: dict[str, str] = {
    "id": "ID",
    "chefia": "Chefia",
    "data": "Data",
    "data_finalizacao": "Data de Finalização",
    "codigo_processo": "Código do Processo",
    "numero_processo": "Nº Processo",
    "numero_formatado": "Nº Formatado",
    "procurador": "Procurador",
    "usuario_criacao": "Usuário Criação",
    "usuario_finalizacao": "Usuário Finalização",
    "usuario_cumpridor_pendencia": "Usuário Cumpridor",
    "categoria": "Categoria",
    "categoria_pendencia": "Categoria Pendência",
    "modelo": "Modelo",
    "area": "Área",
    "cd_pendencia": "Cód. Pendência",
}

TABLE_LABELS: dict[str, str] = {
    "processos_novos": "Processos Novos",
    "pecas_elaboradas": "Peças Elaboradas",
    "pendencias": "Pendências",
    "pecas_finalizadas": "Peças Finalizadas",
}


def _get_column_type(col_type) -> str:
    """Converte tipo SQLAlchemy para string amigável."""
    if isinstance(col_type, (BigInteger, Integer)):
        return "number"
    if isinstance(col_type, (String, Text)):
        return "text"
    return "datetime"


class ExplorerService:
    """Explorador genérico de tabelas."""

    def __init__(self, session: AsyncSession):
        self.session = session

    @cached(ttl=86400)
    async def get_schema(self, table: TableName) -> TableSchema:
        """Retorna o schema de uma tabela com labels pt-BR."""
        model = TABLE_MODEL_MAP[table.value]

        count_stmt = select(func.count()).select_from(model)
        result = await self.session.execute(count_stmt)
        total = result.scalar() or 0

        columns = []
        for col in model.__table__.columns:
            columns.append(
                ColumnSchema(
                    name=col.name,
                    label=COLUMN_LABELS.get(col.name, col.name),
                    type=_get_column_type(col.type),
                )
            )

        return TableSchema(
            table=table.value,
            label=TABLE_LABELS.get(table.value, table.value),
            columns=columns,
            total_rows=total,
        )

    async def get_data(
        self,
        table: TableName,
        filters: GlobalFilters,
        pagination: PaginationParams,
    ) -> PaginatedResponse:
        """Retorna dados paginados de uma tabela."""
        model = TABLE_MODEL_MAP[table.value]
        repo = BaseRepository(self.session, model)
        return await repo.list_paginated(filters, pagination)

    async def get_distinct(
        self, table: TableName, column: str, limit: int = 500
    ) -> list[str]:
        """Retorna valores distintos de uma coluna."""
        model = TABLE_MODEL_MAP[table.value]
        repo = BaseRepository(self.session, model)
        return await repo.distinct_values(column, limit)
