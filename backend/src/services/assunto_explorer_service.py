"""Serviço para exploração interativa da árvore de assuntos."""

import logging

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.filters import GlobalFilters, PaginationParams
from src.domain.models import (
    Assunto,
    PecaFinalizada,
    Pendencia,
    ProcessoAssunto,
    ProcessoNovo,
)
from src.domain.schemas import (
    AssuntoGroupCount,
    AssuntoNode,
    AssuntoResumoResponse,
    GroupCount,
    KPIValue,
    PaginatedResponse,
    TimelinePoint,
    TimelineSeries,
)
from src.repositories.base_repository import BaseRepository
from src.services.cache import cached

logger = logging.getLogger(__name__)


class AssuntoExplorerService:
    """Explora a árvore hierárquica de assuntos com KPIs cross-table."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo_processos = BaseRepository(session, ProcessoNovo)
        self.repo_pecas = BaseRepository(session, PecaFinalizada)
        self.repo_pendencias = BaseRepository(session, Pendencia)

    def _build_descendentes_cte(self, assunto_pai: int | None):
        """Constrói CTE recursivo: filhos diretos → todos os descendentes.

        Retorna CTE com colunas (codigo, filho_direto).
        """
        if assunto_pai is not None:
            children_filter = Assunto.codigo_pai == assunto_pai
        else:
            children_filter = Assunto.codigo_pai.is_(None)

        # Âncora: filhos diretos do nó selecionado
        descendentes = (
            select(
                Assunto.codigo.label("codigo"),
                Assunto.codigo.label("filho_direto"),
            )
            .where(children_filter)
            .cte(name="descendentes", recursive=True)
        )

        # Parte recursiva: descendentes dos filhos
        assunto_alias = Assunto.__table__.alias("a_rec")
        descendentes = descendentes.union_all(
            select(
                assunto_alias.c.codigo,
                descendentes.c.filho_direto,
            ).where(assunto_alias.c.codigo_pai == descendentes.c.codigo)
        )

        return descendentes

    def _build_all_descendentes_cte(self, codigo: int):
        """Constrói CTE recursivo com TODOS os descendentes de um nó (inclusive ele).

        Retorna CTE com coluna (codigo).
        """
        descendentes = (
            select(Assunto.codigo.label("codigo"))
            .where(Assunto.codigo == codigo)
            .cte(name="all_desc", recursive=True)
        )

        assunto_alias = Assunto.__table__.alias("a_all")
        descendentes = descendentes.union_all(
            select(assunto_alias.c.codigo)
            .where(assunto_alias.c.codigo_pai == descendentes.c.codigo)
        )

        return descendentes

    @cached(ttl=300)
    async def drill_down(
        self,
        assunto_pai: int | None,
        filters: GlobalFilters,
        limit: int = 50,
    ) -> list[AssuntoGroupCount]:
        """Retorna filhos diretos com contagem acumulada de descendentes."""
        selected_assuntos = list(filters.assunto)
        filters.assunto = []  # limpar para _apply_global_filters não aplicar

        # Modo filtrado: mostra apenas os assuntos selecionados
        if selected_assuntos:
            return await self._drill_down_filtered(
                selected_assuntos, filters, limit
            )

        descendentes = self._build_descendentes_cte(assunto_pai)

        total_col = func.count(func.distinct(ProcessoNovo.id)).label("total")

        stmt = (
            select(
                descendentes.c.filho_direto.label("filho_direto"),
                Assunto.nome.label("nome"),
                total_col,
            )
            .select_from(ProcessoNovo)
            .join(
                ProcessoAssunto,
                ProcessoAssunto.numero_processo == ProcessoNovo.numero_processo,
            )
            .join(
                descendentes,
                descendentes.c.codigo == ProcessoAssunto.codigo_assunto,
            )
            .join(
                Assunto,
                Assunto.codigo == descendentes.c.filho_direto,
            )
            .where(ProcessoAssunto.assunto_principal.is_(True))
            .group_by(descendentes.c.filho_direto, Assunto.nome)
            .order_by(total_col.desc())
            .limit(limit)
        )

        stmt = self.repo_processos._apply_global_filters(stmt, filters)

        result = await self.session.execute(stmt)
        rows = result.all()

        if not rows:
            return []

        # Verificar quais filhos têm sub-filhos
        filho_codigos = [row.filho_direto for row in rows]
        has_children_stmt = (
            select(Assunto.codigo_pai)
            .where(Assunto.codigo_pai.in_(filho_codigos))
            .group_by(Assunto.codigo_pai)
        )
        hc_result = await self.session.execute(has_children_stmt)
        parents_with_children = {row[0] for row in hc_result.all()}

        return [
            AssuntoGroupCount(
                grupo=row.nome or f"Código {row.filho_direto}",
                total=row.total,
                codigo=row.filho_direto,
                has_children=row.filho_direto in parents_with_children,
            )
            for row in rows
        ]

    @cached(ttl=300)
    async def get_resumo(
        self,
        codigo: int,
        filters: GlobalFilters,
    ) -> AssuntoResumoResponse:
        """Retorna resumo completo de um nó: KPIs, filhos diretos e timeline por filho."""
        # Limpa filtro de assunto para não conflitar
        filters.assunto = []

        # Nome do assunto
        nome_result = await self.session.execute(
            select(Assunto.nome).where(Assunto.codigo == codigo)
        )
        nome = nome_result.scalar() or f"Código {codigo}"

        # CTE com todos os descendentes (inclusive o próprio nó) — para KPIs
        desc_cte = self._build_all_descendentes_cte(codigo)

        # Subquery: numero_processo dos processos com assunto nos descendentes
        processos_subq = (
            select(ProcessoAssunto.numero_processo)
            .join(desc_cte, desc_cte.c.codigo == ProcessoAssunto.codigo_assunto)
            .where(ProcessoAssunto.assunto_principal.is_(True))
            .distinct()
            .scalar_subquery()
        )

        # KPI processos novos
        kpi_proc_stmt = (
            select(func.count(func.distinct(ProcessoNovo.id)))
            .select_from(ProcessoNovo)
            .join(
                ProcessoAssunto,
                ProcessoAssunto.numero_processo == ProcessoNovo.numero_processo,
            )
            .join(
                desc_cte,
                desc_cte.c.codigo == ProcessoAssunto.codigo_assunto,
            )
            .where(ProcessoAssunto.assunto_principal.is_(True))
        )
        kpi_proc_stmt = self.repo_processos._apply_global_filters(
            kpi_proc_stmt, filters
        )
        proc_count = (await self.session.execute(kpi_proc_stmt)).scalar() or 0

        # KPI peças finalizadas (via numero_processo)
        kpi_pecas_stmt = (
            select(func.count())
            .select_from(PecaFinalizada)
            .where(PecaFinalizada.numero_processo.in_(processos_subq))
        )
        kpi_pecas_stmt = self.repo_pecas._apply_global_filters(
            kpi_pecas_stmt, filters
        )
        pecas_count = (await self.session.execute(kpi_pecas_stmt)).scalar() or 0

        # KPI pendências (via numero_processo)
        kpi_pend_stmt = (
            select(func.count())
            .select_from(Pendencia)
            .where(Pendencia.numero_processo.in_(processos_subq))
        )
        kpi_pend_stmt = self.repo_pendencias._apply_global_filters(
            kpi_pend_stmt, filters
        )
        pend_count = (await self.session.execute(kpi_pend_stmt)).scalar() or 0

        kpis = [
            KPIValue(label="Processos Novos", valor=proc_count),
            KPIValue(label="Peças Finalizadas", valor=pecas_count),
            KPIValue(label="Pendências", valor=pend_count),
        ]

        # --- Gráficos por filhos diretos ---
        filhos_desc = self._build_descendentes_cte(codigo)

        # Bar chart: contagem de processos por filho direto
        total_col = func.count(func.distinct(ProcessoNovo.id)).label("total")
        top_filhos_stmt = (
            select(
                filhos_desc.c.filho_direto,
                Assunto.nome.label("grupo"),
                total_col,
            )
            .select_from(ProcessoNovo)
            .join(
                ProcessoAssunto,
                ProcessoAssunto.numero_processo == ProcessoNovo.numero_processo,
            )
            .join(
                filhos_desc,
                filhos_desc.c.codigo == ProcessoAssunto.codigo_assunto,
            )
            .join(
                Assunto,
                Assunto.codigo == filhos_desc.c.filho_direto,
            )
            .where(ProcessoAssunto.assunto_principal.is_(True))
            .group_by(filhos_desc.c.filho_direto, Assunto.nome)
            .order_by(total_col.desc())
            .limit(15)
        )
        top_filhos_stmt = self.repo_processos._apply_global_filters(
            top_filhos_stmt, filters
        )
        filhos_result = await self.session.execute(top_filhos_stmt)
        filhos_rows = filhos_result.all()

        top_filhos = [
            GroupCount(grupo=row.grupo or f"Código {row.filho_direto}", total=row.total)
            for row in filhos_rows
        ]

        # Timeline: evolução mensal por filho direto (top 5)
        top_codigos = [row.filho_direto for row in filhos_rows[:5]]
        timeline: list[TimelineSeries] = []

        if top_codigos:
            filhos_desc_tl = self._build_descendentes_cte(codigo)
            date_col = ProcessoNovo.data
            period_expr = func.to_char(date_col, "YYYY-MM")

            timeline_stmt = (
                select(
                    filhos_desc_tl.c.filho_direto,
                    Assunto.nome.label("nome_filho"),
                    period_expr.label("periodo"),
                    func.count(func.distinct(ProcessoNovo.id)).label("total"),
                )
                .select_from(ProcessoNovo)
                .join(
                    ProcessoAssunto,
                    ProcessoAssunto.numero_processo == ProcessoNovo.numero_processo,
                )
                .join(
                    filhos_desc_tl,
                    filhos_desc_tl.c.codigo == ProcessoAssunto.codigo_assunto,
                )
                .join(
                    Assunto,
                    Assunto.codigo == filhos_desc_tl.c.filho_direto,
                )
                .where(ProcessoAssunto.assunto_principal.is_(True))
                .where(filhos_desc_tl.c.filho_direto.in_(top_codigos))
                .where(date_col.isnot(None))
                .group_by(
                    filhos_desc_tl.c.filho_direto, Assunto.nome, period_expr
                )
                .order_by(period_expr)
            )
            timeline_stmt = self.repo_processos._apply_global_filters(
                timeline_stmt, filters
            )
            tl_result = await self.session.execute(timeline_stmt)
            tl_rows = tl_result.all()

            # Agrupa por nome do filho
            series_map: dict[str, list[TimelinePoint]] = {}
            for row in tl_rows:
                nome_filho = row.nome_filho or f"Código {row.filho_direto}"
                if nome_filho not in series_map:
                    series_map[nome_filho] = []
                series_map[nome_filho].append(
                    TimelinePoint(periodo=row.periodo, valor=row.total)
                )

            # Mantém ordem do bar chart (top → bottom)
            for fr in filhos_rows[:5]:
                nome_filho = fr.grupo or f"Código {fr.filho_direto}"
                if nome_filho in series_map:
                    timeline.append(
                        TimelineSeries(nome=nome_filho, dados=series_map[nome_filho])
                    )

        return AssuntoResumoResponse(
            nome=nome,
            codigo=codigo,
            kpis=kpis,
            top_filhos=top_filhos,
            timeline=timeline,
        )

    @cached(ttl=600)
    async def search_assuntos(
        self,
        query: str,
        limit: int = 20,
    ) -> list[AssuntoNode]:
        """Busca textual de assuntos por nome (case-insensitive, sem acentos).

        Args:
            query: Termo de busca (mínimo 2 caracteres)
            limit: Limite de resultados

        Returns:
            Lista de assuntos ordenados por relevância (mais rasos primeiro)
        """
        # Remove acentos e converte para maiúsculas para busca insensitive
        # UNACCENT requer extensão unaccent habilitada no PostgreSQL
        search_term = f"%{query}%"

        stmt = (
            select(
                Assunto.codigo,
                Assunto.nome,
                Assunto.nivel,
            )
            .where(Assunto.nome.isnot(None))
            .where(
                func.unaccent(Assunto.nome).ilike(func.unaccent(search_term))
            )
            .order_by(
                Assunto.nivel.asc().nullslast(),  # Níveis mais rasos primeiro
                Assunto.nome.asc(),
            )
            .limit(limit)
        )

        result = await self.session.execute(stmt)
        rows = result.all()

        return [
            AssuntoNode(
                codigo=row.codigo,
                nome=row.nome or f"Código {row.codigo}",
                nivel=row.nivel or 0,
                filhos=[],
            )
            for row in rows
        ]

    async def _drill_down_filtered(
        self,
        assunto_codes: list[int],
        filters: GlobalFilters,
        limit: int,
    ) -> list[AssuntoGroupCount]:
        """Modo filtrado: mostra apenas os assuntos selecionados com contagens.

        Para cada assunto selecionado, expande descendentes via CTE recursivo
        e conta processos distintos agrupados pelo assunto-raiz selecionado.
        """
        # CTE: para cada assunto selecionado, expandir descendentes
        descendentes = (
            select(
                Assunto.codigo.label("codigo"),
                Assunto.codigo.label("assunto_raiz"),
            )
            .where(Assunto.codigo.in_(assunto_codes))
            .cte(name="desc_filtro", recursive=True)
        )

        assunto_alias = Assunto.__table__.alias("a_filt")
        descendentes = descendentes.union_all(
            select(
                assunto_alias.c.codigo,
                descendentes.c.assunto_raiz,
            ).where(assunto_alias.c.codigo_pai == descendentes.c.codigo)
        )

        total_col = func.count(func.distinct(ProcessoNovo.id)).label("total")

        # Nome do assunto-raiz via join com alias da tabela Assunto
        assunto_raiz = Assunto.__table__.alias("a_raiz")

        stmt = (
            select(
                descendentes.c.assunto_raiz.label("filho_direto"),
                assunto_raiz.c.nome.label("nome"),
                total_col,
            )
            .select_from(ProcessoNovo)
            .join(
                ProcessoAssunto,
                ProcessoAssunto.numero_processo == ProcessoNovo.numero_processo,
            )
            .join(
                descendentes,
                descendentes.c.codigo == ProcessoAssunto.codigo_assunto,
            )
            .join(
                assunto_raiz,
                assunto_raiz.c.codigo == descendentes.c.assunto_raiz,
            )
            .where(ProcessoAssunto.assunto_principal.is_(True))
            .group_by(descendentes.c.assunto_raiz, assunto_raiz.c.nome)
            .order_by(total_col.desc())
            .limit(limit)
        )

        stmt = self.repo_processos._apply_global_filters(stmt, filters)

        result = await self.session.execute(stmt)
        rows = result.all()

        if not rows:
            return []

        # Verificar quais têm sub-filhos
        codigos = [row.filho_direto for row in rows]
        has_children_stmt = (
            select(Assunto.codigo_pai)
            .where(Assunto.codigo_pai.in_(codigos))
            .group_by(Assunto.codigo_pai)
        )
        hc_result = await self.session.execute(has_children_stmt)
        parents_with_children = {row[0] for row in hc_result.all()}

        return [
            AssuntoGroupCount(
                grupo=row.nome or f"Código {row.filho_direto}",
                total=row.total,
                codigo=row.filho_direto,
                has_children=row.filho_direto in parents_with_children,
            )
            for row in rows
        ]

    async def _expand_assunto_descendants(
        self, codes: list[int]
    ) -> list[int]:
        """Expande códigos de assunto para incluir todos os descendentes."""
        all_desc = (
            select(Assunto.codigo.label("codigo"))
            .where(Assunto.codigo.in_(codes))
            .cte(name="all_desc_expand", recursive=True)
        )
        assunto_alias = Assunto.__table__.alias("a_expand")
        all_desc = all_desc.union_all(
            select(assunto_alias.c.codigo).where(
                assunto_alias.c.codigo_pai == all_desc.c.codigo
            )
        )

        result = await self.session.execute(select(all_desc.c.codigo))
        return [row[0] for row in result.all()]

    async def list_processos(
        self,
        filters: GlobalFilters,
        pagination: PaginationParams,
    ) -> PaginatedResponse:
        """Lista paginada de processos filtrados pelos assuntos selecionados.

        Expande os códigos de assunto para incluir descendentes antes de
        delegar ao list_paginated padrão do BaseRepository.
        """
        if filters.assunto:
            filters.assunto = await self._expand_assunto_descendants(
                filters.assunto
            )
        return await self.repo_processos.list_paginated(filters, pagination)

    @cached(ttl=3600)
    async def get_assunto_path(self, codigo: int) -> list[AssuntoNode]:
        """Retorna o caminho hierárquico completo até o assunto (da raiz até ele).

        Args:
            codigo: Código do assunto de destino

        Returns:
            Lista de assuntos no path, da raiz até o assunto (sem incluir a raiz NULL)

        Example:
            Para código 123 com path: None → 1 → 10 → 123
            Retorna: [AssuntoNode(1), AssuntoNode(10), AssuntoNode(123)]
        """
        # CTE recursivo: constrói path de baixo para cima
        path_cte = (
            select(
                Assunto.codigo,
                Assunto.codigo_pai,
                Assunto.nome,
                Assunto.nivel,
            )
            .where(Assunto.codigo == codigo)
            .cte(name="assunto_path", recursive=True)
        )

        # Parte recursiva: sobe pelos pais
        parent_alias = Assunto.__table__.alias("a_parent")
        path_cte = path_cte.union_all(
            select(
                parent_alias.c.codigo,
                parent_alias.c.codigo_pai,
                parent_alias.c.nome,
                parent_alias.c.nivel,
            ).where(parent_alias.c.codigo == path_cte.c.codigo_pai)
        )

        # Busca todos os nós do path
        stmt = (
            select(
                path_cte.c.codigo,
                path_cte.c.nome,
                path_cte.c.nivel,
            )
            .select_from(path_cte)
            .order_by(path_cte.c.nivel.asc().nullslast())
        )

        result = await self.session.execute(stmt)
        rows = result.all()

        return [
            AssuntoNode(
                codigo=row.codigo,
                nome=row.nome or f"Código {row.codigo}",
                nivel=row.nivel or 0,
                filhos=[],
            )
            for row in rows
        ]
