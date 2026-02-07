"""Repositório base com operações genéricas de filtro, contagem e paginação."""

import math
from datetime import datetime

from sqlalchemy import Column, Select, func, literal, select, or_, String, cast, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase

from src.domain.enums import Granularity
from src.domain.filters import GlobalFilters, PaginationParams
from src.domain.schemas import GroupCount, PaginatedResponse, TimelinePoint
from src.services.normalization import normalize_chefia_expr, normalize_procurador_expr


# Mapeamento de coluna de usuário (assessor) por tabela
ASSESSOR_COL_MAP: dict[str, str] = {
    "pecas_elaboradas": "usuario_criacao",
    "pecas_finalizadas": "usuario_finalizacao",
    "pendencias": "usuario_cumpridor_pendencia",
}


class BaseRepository:
    """Repositório genérico para operações comuns sobre tabelas do BI."""

    def __init__(self, session: AsyncSession, model: type[DeclarativeBase]):
        self.session = session
        self.model = model

    def _get_date_column(self) -> Column:
        """Retorna a coluna de data do modelo (data ou data_finalizacao)."""
        if hasattr(self.model, "data_finalizacao"):
            return self.model.data_finalizacao
        return self.model.data

    def _apply_global_filters(
        self, stmt: Select, filters: GlobalFilters
    ) -> Select:
        """Aplica filtros globais condicionalmente ao statement."""
        date_col = self._get_date_column()

        if filters.ano:
            stmt = stmt.where(func.extract("year", date_col) == filters.ano)

        if filters.mes:
            stmt = stmt.where(func.extract("month", date_col) == filters.mes)

        if filters.data_inicio:
            dt_inicio = datetime.combine(filters.data_inicio, datetime.min.time())
            stmt = stmt.where(date_col >= dt_inicio)

        if filters.data_fim:
            dt_fim = datetime.combine(filters.data_fim, datetime.max.time())
            stmt = stmt.where(date_col <= dt_fim)

        if filters.chefia:
            chefia_expr = self._get_group_expr("chefia")
            stmt = stmt.where(chefia_expr.in_(filters.chefia))

        if filters.procurador:
            proc_expr = self._get_group_expr("procurador")
            stmt = stmt.where(proc_expr.in_(filters.procurador))

        if filters.categoria and hasattr(self.model, "categoria"):
            stmt = stmt.where(self.model.categoria.in_(filters.categoria))

        if filters.area and hasattr(self.model, "area"):
            stmt = stmt.where(self.model.area.in_(filters.area))

        if filters.assessor:
            col_name = ASSESSOR_COL_MAP.get(self.model.__tablename__)
            if col_name and hasattr(self.model, col_name):
                stmt = stmt.where(
                    getattr(self.model, col_name).in_(filters.assessor)
                )
            else:
                # Tabela sem coluna de assessor (ex: processos_novos) → 0 resultados
                stmt = stmt.where(literal(False))

        return stmt

    async def total_count(self, filters: GlobalFilters) -> int:
        """Conta total de registros com filtros aplicados."""
        stmt = select(func.count()).select_from(self.model)
        stmt = self._apply_global_filters(stmt, filters)
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def count_by_period(
        self,
        filters: GlobalFilters,
        granularity: Granularity = Granularity.MENSAL,
    ) -> list[TimelinePoint]:
        """Conta registros agrupados por período temporal."""
        date_col = self._get_date_column()

        if granularity == Granularity.ANUAL:
            period_expr = func.to_char(date_col, "YYYY")
        else:
            period_expr = func.to_char(date_col, "YYYY-MM")

        stmt = (
            select(period_expr.label("periodo"), func.count().label("total"))
            .select_from(self.model)
            .where(date_col.isnot(None))
            .group_by(period_expr)
            .order_by(period_expr)
        )
        stmt = self._apply_global_filters(stmt, filters)

        result = await self.session.execute(stmt)
        return [
            TimelinePoint(periodo=row.periodo, valor=row.total)
            for row in result.all()
        ]

    def _get_group_expr(self, group_column: str) -> Column:
        """Retorna expressão de agrupamento com normalização quando necessário."""
        col = getattr(self.model, group_column)
        if group_column == "chefia":
            return normalize_chefia_expr(col)
        if group_column == "procurador":
            return normalize_procurador_expr(col)
        return col

    async def count_by_group(
        self,
        filters: GlobalFilters,
        group_column: str,
        limit: int = 10,
    ) -> list[GroupCount]:
        """Conta registros agrupados por uma dimensão com normalização."""
        if not hasattr(self.model, group_column):
            return []
        col = getattr(self.model, group_column)
        group_expr = self._get_group_expr(group_column)

        stmt = (
            select(group_expr.label("grupo"), func.count().label("total"))
            .select_from(self.model)
            .where(col.isnot(None))
            .group_by(group_expr)
            .order_by(func.count().desc())
            .limit(limit)
        )
        stmt = self._apply_global_filters(stmt, filters)

        result = await self.session.execute(stmt)
        return [
            GroupCount(grupo=row.grupo, total=row.total)
            for row in result.all()
        ]

    async def list_paginated(
        self,
        filters: GlobalFilters,
        pagination: PaginationParams,
    ) -> PaginatedResponse:
        """Lista registros com paginação server-side, ordenação e busca."""
        # Query de contagem
        count_stmt = select(func.count()).select_from(self.model)
        count_stmt = self._apply_global_filters(count_stmt, filters)

        # Busca textual (busca em todas as colunas de texto)
        if pagination.search:
            text_columns = [
                col for col in self.model.__table__.columns
                if isinstance(col.type, (String,))
            ]
            if text_columns:
                search_filter = or_(
                    *[
                        cast(col, String).ilike(f"%{pagination.search}%")
                        for col in text_columns
                    ]
                )
                count_stmt = count_stmt.where(search_filter)

        count_result = await self.session.execute(count_stmt)
        total = count_result.scalar() or 0

        # Query de dados
        stmt = select(self.model)
        stmt = self._apply_global_filters(stmt, filters)

        if pagination.search and text_columns:
            stmt = stmt.where(search_filter)

        # Ordenação
        if pagination.sort_by and hasattr(self.model, pagination.sort_by):
            sort_col = getattr(self.model, pagination.sort_by)
            stmt = stmt.order_by(
                desc(sort_col) if pagination.sort_order == "desc" else asc(sort_col)
            )
        else:
            stmt = stmt.order_by(desc(self.model.id))

        # Paginação
        offset = (pagination.page - 1) * pagination.page_size
        stmt = stmt.offset(offset).limit(pagination.page_size)

        result = await self.session.execute(stmt)
        rows = result.scalars().all()

        # Converter para dicts
        items = []
        for row in rows:
            item = {}
            for col in self.model.__table__.columns:
                val = getattr(row, col.name)
                if isinstance(val, datetime):
                    val = val.isoformat()
                item[col.name] = val
            items.append(item)

        return PaginatedResponse(
            items=items,
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
            total_pages=math.ceil(total / pagination.page_size) if total > 0 else 0,
        )

    async def distinct_values(self, column: str, limit: int = 500) -> list[str]:
        """Retorna valores distintos de uma coluna com normalização."""
        col = getattr(self.model, column)
        group_expr = self._get_group_expr(column)

        stmt = (
            select(group_expr.label("valor"))
            .where(col.isnot(None))
            .distinct()
            .order_by(group_expr)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return [str(row[0]) for row in result.all()]
