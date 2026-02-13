"""Repositório base com operações genéricas de filtro, contagem e paginação."""

import math
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, Select, case, func, literal, select, or_, String, cast, desc, asc, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase

from src.domain.constants import ASSESSORES_ADMINISTRATIVOS, CATEGORIAS_NAO_PRODUTIVAS
from src.domain.enums import Granularity
from src.domain.filters import GlobalFilters, PaginationParams
from src.domain.models import HiddenProcuradorProducao, PecaFinalizada, Pendencia, ProcessoAssunto, ProcessoNovo, UserRole
from src.domain.schemas import GroupCount, PaginatedResponse, TimelinePoint
from src.services.normalization import normalize_chefia_expr, normalize_procurador_expr


# Mapeamento de coluna de usuário (assessor) por tabela
ASSESSOR_COL_MAP: dict[str, str] = {
    "pecas_elaboradas": "usuario_criacao",
    "pecas_finalizadas": "usuario_finalizacao",
    "pendencias": "usuario_cumpridor_pendencia",
}

# Tabelas que participam da ocultação de produção (métricas de procurador)
HIDDEN_TABLES = {"processos_novos", "pecas_finalizadas", "pendencias"}

# Coluna real de "procurador" por tabela.
# Em pecas_finalizadas, o campo `procurador` é o dono do caso, mas quem
# realmente finalizou a peça é `usuario_finalizacao`. Para rankings por
# procurador, usamos a coluna de atribuição correta.
PROCURADOR_COL_MAP: dict[str, str] = {
    "pecas_finalizadas": "usuario_finalizacao",
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

    def _get_year_expr(self):
        """Retorna expressão SQL para o 'ano' do registro.

        Para processos_novos, o ano é extraído do número CNJ (numero_formatado).
        Suporta dois formatos: NNNNNNN-DD.YYYY.J.TT.OOOO e NNNNNNNNN.YYYY.J.TT.OOOO.
        Usa SPLIT_PART(numero_formatado, '.', 2) para extrair o ano (segundo segmento).
        Registros sem formato CNJ válido usam o ano da coluna data como fallback.
        Para demais tabelas, usa EXTRACT(YEAR FROM date_col).
        """
        date_col = self._get_date_column()
        if self.model.__tablename__ == "processos_novos":
            # Verifica se o numero_formatado tem formato CNJ (contém .YYYY.)
            has_cnj_year = self.model.numero_formatado.op("~")(r"\.\d{4}\.")
            # Extrai ano como segundo segmento separado por ponto
            cnj_year = cast(
                func.split_part(self.model.numero_formatado, ".", 2), Integer
            )
            return case(
                (has_cnj_year, cnj_year),
                else_=cast(func.extract("year", date_col), Integer),
            )
        return func.extract("year", date_col)

    def _apply_global_filters(
        self, stmt: Select, filters: GlobalFilters
    ) -> Select:
        """Aplica filtros globais condicionalmente ao statement."""
        date_col = self._get_date_column()
        year_expr = self._get_year_expr()

        if filters.anos:
            if len(filters.anos) == 1:
                stmt = stmt.where(year_expr == filters.anos[0])
            else:
                stmt = stmt.where(year_expr.in_(filters.anos))

        if filters.mes:
            stmt = stmt.where(func.extract("month", date_col) == filters.mes)

        if filters.data_inicio:
            dt_inicio = datetime.combine(filters.data_inicio, datetime.min.time())
            stmt = stmt.where(date_col >= dt_inicio)

        if filters.data_fim:
            dt_fim = datetime.combine(filters.data_fim, datetime.max.time())
            stmt = stmt.where(date_col <= dt_fim)

        if filters.chefia:
            chefia_expr = self._get_filter_expr("chefia")
            stmt = stmt.where(chefia_expr.in_(filters.chefia))

        if filters.procurador:
            # Usa coluna resolvida (PROCURADOR_COL_MAP): em pecas_finalizadas
            # filtra por usuario_finalizacao (quem finalizou), não por procurador
            # (dono do caso). Sem isso, KPIs mostram peças finalizadas por OUTROS
            # nos processos do procurador, inflando/deflando a métrica.
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

        # Filtro por assunto: subquery em processo_assuntos
        # Só aplicado a processos_novos — assunto é propriedade do processo
        if filters.assunto and self.model.__tablename__ == "processos_novos":
            assunto_subq = (
                select(ProcessoAssunto.numero_processo)
                .where(ProcessoAssunto.codigo_assunto.in_(filters.assunto))
                .distinct()
                .scalar_subquery()
            )
            stmt = stmt.where(self.model.numero_processo.in_(assunto_subq))

        # Filtro por faixa de valor da causa
        # Regra: sem valor_min → inclui NULLs (processos sem valor informado)
        #         com valor_min → exclui NULLs (só processos com valor no range)
        if filters.valor_min is not None or filters.valor_max is not None:
            if self.model is ProcessoNovo:
                if filters.valor_min is not None:
                    stmt = stmt.where(ProcessoNovo.valor_acao >= filters.valor_min)
                if filters.valor_max is not None:
                    if filters.valor_min is None:
                        # "Até X" — inclui processos sem valor informado
                        stmt = stmt.where(or_(
                            ProcessoNovo.valor_acao <= filters.valor_max,
                            ProcessoNovo.valor_acao.is_(None),
                        ))
                    else:
                        stmt = stmt.where(ProcessoNovo.valor_acao <= filters.valor_max)
            elif hasattr(self.model, "numero_processo"):
                valor_subq = select(ProcessoNovo.numero_processo)
                if filters.valor_min is not None:
                    valor_subq = valor_subq.where(
                        ProcessoNovo.valor_acao >= filters.valor_min
                    )
                if filters.valor_max is not None:
                    if filters.valor_min is None:
                        valor_subq = valor_subq.where(or_(
                            ProcessoNovo.valor_acao <= filters.valor_max,
                            ProcessoNovo.valor_acao.is_(None),
                        ))
                    else:
                        valor_subq = valor_subq.where(
                            ProcessoNovo.valor_acao <= filters.valor_max
                        )
                else:
                    valor_subq = valor_subq.where(
                        ProcessoNovo.valor_acao.isnot(None)
                    )
                stmt = stmt.where(
                    self.model.numero_processo.in_(valor_subq.distinct().scalar_subquery())
                )

        # Excluir categorias não-produtivas de pecas_finalizadas
        if self.model is PecaFinalizada:
            stmt = stmt.where(
                PecaFinalizada.categoria.notin_(CATEGORIAS_NAO_PRODUTIVAS)
            )

        # Excluir registros de assessores administrativos (trabalho não-jurídico)
        assessor_col_name = ASSESSOR_COL_MAP.get(self.model.__tablename__)
        if assessor_col_name and hasattr(self.model, assessor_col_name):
            assessor_col = getattr(self.model, assessor_col_name)
            stmt = stmt.where(
                or_(
                    assessor_col.is_(None),
                    normalize_procurador_expr(assessor_col).notin_(
                        list(ASSESSORES_ADMINISTRATIVOS)
                    ),
                )
            )

        # Excluir produção oculta por regras administrativas
        if filters.exclude_hidden and self.model.__tablename__ in HIDDEN_TABLES:
            stmt = self._apply_hidden_filter(stmt)

        return stmt

    def _apply_hidden_filter(self, stmt: Select) -> Select:
        """Adiciona NOT EXISTS para excluir registros de procuradores ocultos."""
        hidden = HiddenProcuradorProducao.__table__
        date_col = self._get_date_column()

        # Coluna resolvida (mesma lógica dos rankings)
        resolved = self._resolve_column("procurador")
        proc_col = normalize_procurador_expr(getattr(self.model, resolved))
        chefia_col = normalize_chefia_expr(self.model.chefia)

        exists_subq = (
            select(literal(1))
            .select_from(hidden)
            .where(
                hidden.c.is_active.is_(True),
                hidden.c.procurador_name == proc_col,
                or_(
                    hidden.c.chefia.is_(None),
                    hidden.c.chefia == chefia_col,
                ),
                date_col >= func.cast(hidden.c.start_date, DateTime),
                date_col < func.cast(
                    hidden.c.end_date + text("INTERVAL '1 day'"), DateTime
                ),
            )
            .correlate(self.model)
            .exists()
        )
        return stmt.where(~exists_subq)

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

    def _resolve_column(self, group_column: str) -> str:
        """Resolve o nome real da coluna considerando mapeamentos por tabela.

        Para 'procurador' em pecas_finalizadas, usa 'usuario_finalizacao'
        (quem de fato finalizou a peça, não o dono do caso).
        """
        if group_column == "procurador":
            mapped = PROCURADOR_COL_MAP.get(self.model.__tablename__)
            if mapped and hasattr(self.model, mapped):
                return mapped
        return group_column

    def _procurador_names_subquery(self) -> Select:
        """Subquery com nomes classificados como procurador em user_roles."""
        return (
            select(UserRole.name)
            .where(UserRole.role == "procurador")
            .scalar_subquery()
        )

    @staticmethod
    def _has_pendencias_subquery() -> Select:
        """Subquery com procuradores que possuem ao menos 1 pendência no histórico."""
        return (
            select(func.distinct(Pendencia.procurador))
            .where(Pendencia.procurador.isnot(None))
            .where(Pendencia.procurador != "")
            .scalar_subquery()
        )

    def _get_filter_expr(self, column_name: str) -> Column:
        """Retorna expressão de filtro com normalização (sem resolução de coluna).

        Usado apenas para chefia em _apply_global_filters.
        Para procurador, usar _get_group_expr (com resolução via PROCURADOR_COL_MAP).
        """
        col = getattr(self.model, column_name)
        if column_name in ("chefia",):
            return normalize_chefia_expr(col)
        if column_name in ("procurador",):
            return normalize_procurador_expr(col)
        return col

    def _get_group_expr(self, group_column: str) -> Column:
        """Retorna expressão de agrupamento com resolução e normalização.

        Usado em count_by_group e distinct_values. Resolve a coluna real
        (ex: procurador → usuario_finalizacao em pecas_finalizadas).
        """
        real_column = self._resolve_column(group_column)
        col = getattr(self.model, real_column)
        if group_column in ("chefia",):
            return normalize_chefia_expr(col)
        if group_column in ("procurador",):
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
        real_column = self._resolve_column(group_column)
        col = getattr(self.model, real_column)
        group_expr = self._get_group_expr(group_column)

        stmt = (
            select(group_expr.label("grupo"), func.count().label("total"))
            .select_from(self.model)
            .where(col.isnot(None))
            .group_by(group_expr)
            .order_by(func.count().desc())
            .limit(limit)
        )

        # Filtrar por role de procurador quando agrupando por "procurador"
        if group_column == "procurador":
            stmt = stmt.where(col.in_(self._procurador_names_subquery()))

            # Excluir procuradores sem nenhuma pendência no histórico
            if filters.exclude_no_pendencias:
                stmt = stmt.where(col.in_(self._has_pendencias_subquery()))

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
        real_column = self._resolve_column(column)
        col = getattr(self.model, real_column)
        group_expr = self._get_group_expr(column)

        stmt = (
            select(group_expr.label("valor"))
            .where(col.isnot(None))
            .distinct()
            .order_by(group_expr)
            .limit(limit)
        )

        # Filtrar por role de procurador quando listando "procurador"
        if column == "procurador":
            stmt = stmt.where(col.in_(self._procurador_names_subquery()))

        result = await self.session.execute(stmt)
        return [str(row[0]) for row in result.all()]
