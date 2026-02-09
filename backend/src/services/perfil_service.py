"""Serviço para análise individualizada de procurador ou chefia."""

import calendar
import logging
from collections import defaultdict
from dataclasses import asdict
from datetime import date, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

from src.domain.filters import GlobalFilters, PaginationParams
from src.domain.models import (
    PecaElaborada,
    PecaFinalizada,
    Pendencia,
    ProcessoNovo,
    TABLE_MODEL_MAP,
    UserRole,
)
from src.domain.schemas import (
    ChefiaMediaKPI,
    ChefiaMediasResponse,
    GroupCount,
    KPIValue,
    PaginatedResponse,
    ProcuradorComparativo,
    TimelinePoint,
    TimelineSeries,
)
from src.repositories.base_repository import BaseRepository
from src.services.cache import cached
from src.domain.constants import CATEGORIAS_NAO_PRODUTIVAS
from src.services.normalization import normalize_chefia_expr, normalize_procurador_expr

# Métricas de procurador (usadas em visão geral, chefia, perfil procurador)
PROCURADOR_TABLES = ["processos_novos", "pecas_finalizadas", "pendencias"]

# Métricas de assessor (usadas apenas em /perfil-assessor)
ASSESSOR_TABLES = ["pecas_elaboradas"]

# Coluna de atribuição de pessoa por tabela no comparativo.
# `procurador` = dono do caso (para processos_novos e pendencias)
# `usuario_finalizacao` = procurador que finalizou a peça (para pecas_finalizadas)
# Nota: `procurador` em pecas_finalizadas é o dono do caso, não quem finalizou.
COMPARATIVO_PERSON_COL: dict[str, str] = {
    "processos_novos": "procurador",
    "pecas_finalizadas": "usuario_finalizacao",
    "pendencias": "procurador",
}


class PerfilService:
    """Analisa dados individuais de um procurador ou chefia."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repos = {
            name: BaseRepository(session, model)
            for name, model in TABLE_MODEL_MAP.items()
        }

    def _build_filters(
        self, dimensao: str, valor: str, filters: GlobalFilters
    ) -> GlobalFilters:
        """Cria filtros globais com a dimensão selecionada preenchida."""
        data = asdict(filters)
        if dimensao == "assessor":
            data["assessor"] = [valor]
        else:
            data[dimensao] = [valor]
        return GlobalFilters(**data)

    @cached(ttl=300)
    async def get_kpis(
        self, dimensao: str, valor: str, filters: GlobalFilters
    ) -> list[KPIValue]:
        """KPIs para o indivíduo selecionado.

        Procurador/Chefia: processos_novos, pecas_finalizadas, pendencias.
        Assessor: inclui também pecas_elaboradas (sua métrica de produção).
        """
        f = self._build_filters(dimensao, valor, filters)

        processos = await self.repos["processos_novos"].total_count(f)
        finalizadas = await self.repos["pecas_finalizadas"].total_count(f)
        pendencias = await self.repos["pendencias"].total_count(f)

        kpis = [
            KPIValue(label="Processos Novos", valor=processos),
            KPIValue(label="Peças Finalizadas", valor=finalizadas),
            KPIValue(label="Pendências", valor=pendencias),
        ]

        if dimensao == "assessor":
            elaboradas = await self.repos["pecas_elaboradas"].total_count(f)
            kpis.insert(1, KPIValue(label="Peças Elaboradas", valor=elaboradas))

        return kpis

    @cached(ttl=300)
    async def get_timeline(
        self, dimensao: str, valor: str, filters: GlobalFilters
    ) -> list[TimelineSeries]:
        """Séries temporais mensais.

        Procurador/Chefia: 3 séries (sem pecas_elaboradas).
        Assessor: inclui pecas_elaboradas.
        """
        f = self._build_filters(dimensao, valor, filters)

        labels: dict[str, str] = {
            "processos_novos": "Processos Novos",
            "pecas_finalizadas": "Peças Finalizadas",
            "pendencias": "Pendências",
        }
        if dimensao == "assessor":
            labels["pecas_elaboradas"] = "Peças Elaboradas"

        series = []
        for table_name, label in labels.items():
            dados = await self.repos[table_name].count_by_period(f)
            series.append(TimelineSeries(nome=label, dados=dados))

        return series

    @cached(ttl=300)
    async def get_por_categoria(
        self,
        dimensao: str,
        valor: str,
        filters: GlobalFilters,
        tabela: str = "pecas_elaboradas",
        limit: int = 15,
    ) -> list[GroupCount]:
        """Ranking por categoria de peça para o indivíduo."""
        f = self._build_filters(dimensao, valor, filters)
        repo = self.repos[tabela]
        return await repo.count_by_group(f, "categoria", limit)

    @cached(ttl=300)
    async def get_por_modelo(
        self,
        dimensao: str,
        valor: str,
        filters: GlobalFilters,
        tabela: str = "pecas_elaboradas",
        limit: int = 15,
    ) -> list[GroupCount]:
        """Ranking por modelo de peça para o indivíduo."""
        f = self._build_filters(dimensao, valor, filters)
        repo = self.repos[tabela]
        return await repo.count_by_group(f, "modelo", limit)

    @cached(ttl=300)
    async def get_por_procurador(
        self,
        dimensao: str,
        valor: str,
        filters: GlobalFilters,
        tabela: str = "pecas_elaboradas",
        limit: int = 15,
    ) -> list[GroupCount]:
        """Ranking por procurador: quais procuradores o assessor atendeu.

        Para assessor + pecas_elaboradas: vincula à pecas_finalizadas
        por (numero_processo, categoria) e agrupa por usuario_finalizacao
        (procurador que finalizou a peça = procurador da pendência).
        Para demais combinações: agrupa pela coluna procurador da tabela.
        """
        if dimensao == "assessor" and tabela == "pecas_elaboradas":
            return await self._get_por_procurador_finalizador(
                valor, filters, limit
            )

        f = self._build_filters(dimensao, valor, filters)
        repo = self.repos[tabela]
        return await repo.count_by_group(f, "procurador", limit)

    async def _get_por_procurador_finalizador(
        self,
        assessor_name: str,
        filters: GlobalFilters,
        limit: int = 15,
    ) -> list[GroupCount]:
        """Ranking: quais procuradores finalizaram as peças elaboradas pelo assessor.

        Vincula pecas_elaboradas → pecas_finalizadas por (numero_processo, categoria)
        e agrupa por usuario_finalizacao (procurador da pendência).
        """
        finalizador_expr = normalize_procurador_expr(
            PecaFinalizada.usuario_finalizacao
        )

        # Apenas nomes classificados como procurador
        proc_names_sq = (
            select(UserRole.name)
            .where(UserRole.role == "procurador")
            .scalar_subquery()
        )

        stmt = (
            select(
                finalizador_expr.label("grupo"),
                func.count(func.distinct(PecaElaborada.id)).label("total"),
            )
            .select_from(PecaElaborada)
            .join(
                PecaFinalizada,
                (PecaElaborada.numero_processo == PecaFinalizada.numero_processo)
                & (PecaElaborada.categoria == PecaFinalizada.categoria),
            )
            .where(PecaElaborada.usuario_criacao == assessor_name)
            .where(PecaFinalizada.usuario_finalizacao.isnot(None))
            .where(PecaFinalizada.usuario_finalizacao != "")
            .where(PecaFinalizada.usuario_finalizacao.in_(proc_names_sq))
            .where(PecaFinalizada.categoria.notin_(CATEGORIAS_NAO_PRODUTIVAS))
            .group_by(finalizador_expr)
            .order_by(func.count(func.distinct(PecaElaborada.id)).desc())
            .limit(limit)
        )

        # Filtros de data sobre pecas_elaboradas
        if filters.anos:
            if len(filters.anos) == 1:
                stmt = stmt.where(
                    func.extract("year", PecaElaborada.data) == filters.anos[0]
                )
            else:
                stmt = stmt.where(
                    func.extract("year", PecaElaborada.data).in_(filters.anos)
                )

        if filters.mes:
            stmt = stmt.where(
                func.extract("month", PecaElaborada.data) == filters.mes
            )

        if filters.data_inicio:
            dt_inicio = datetime.combine(
                filters.data_inicio, datetime.min.time()
            )
            stmt = stmt.where(PecaElaborada.data >= dt_inicio)

        if filters.data_fim:
            dt_fim = datetime.combine(filters.data_fim, datetime.max.time())
            stmt = stmt.where(PecaElaborada.data <= dt_fim)

        if filters.chefia:
            chefia_expr = normalize_chefia_expr(PecaElaborada.chefia)
            stmt = stmt.where(chefia_expr.in_(filters.chefia))

        if filters.categoria:
            stmt = stmt.where(PecaElaborada.categoria.in_(filters.categoria))

        if filters.procurador:
            proc_expr = normalize_procurador_expr(PecaElaborada.procurador)
            stmt = stmt.where(proc_expr.in_(filters.procurador))

        result = await self.session.execute(stmt)
        return [
            GroupCount(grupo=row.grupo, total=row.total)
            for row in result.all()
        ]

    async def get_lista(
        self,
        dimensao: str,
        valor: str,
        filters: GlobalFilters,
        tabela: str,
        pagination: PaginationParams,
    ) -> PaginatedResponse:
        """Lista paginada de registros do indivíduo em uma tabela."""
        f = self._build_filters(dimensao, valor, filters)
        repo = self.repos[tabela]
        return await repo.list_paginated(f, pagination)

    @cached(ttl=300)
    async def get_comparativo_procuradores(
        self, chefia: str, filters: GlobalFilters
    ) -> list[ProcuradorComparativo]:
        """Comparativo de métricas de procurador dentro de uma chefia.

        Agrupa cada tabela pela coluna de atribuição correta:
        - processos_novos / pendencias → `procurador` (dono do caso)
        - pecas_finalizadas → `usuario_finalizacao` (quem finalizou)

        Peças elaboradas é métrica de assessor e não aparece aqui.
        """
        f = self._build_filters("chefia", chefia, filters)
        totais: dict[str, dict[str, int]] = defaultdict(
            lambda: {
                "processos_novos": 0,
                "pecas_finalizadas": 0,
                "pendencias": 0,
            }
        )

        table_models = {
            "processos_novos": ProcessoNovo,
            "pecas_finalizadas": PecaFinalizada,
            "pendencias": Pendencia,
        }

        logger.info(
            "Comparativo procuradores: chefia=%s, filtros=%s",
            chefia, f,
        )

        # Subquery: apenas nomes classificados como procurador
        proc_names_sq = (
            select(UserRole.name)
            .where(UserRole.role == "procurador")
            .scalar_subquery()
        )

        for table_name, model in table_models.items():
            repo = self.repos[table_name]

            # Usa a coluna de atribuição correta por tabela
            person_col_name = COMPARATIVO_PERSON_COL[table_name]
            raw_col = getattr(model, person_col_name)
            person_expr = normalize_procurador_expr(raw_col)

            stmt = (
                select(
                    person_expr.label("procurador"),
                    func.count().label("total"),
                )
                .select_from(model)
                .where(raw_col.isnot(None))
                .where(raw_col != "")
                .where(raw_col.in_(proc_names_sq))
                .group_by(person_expr)
            )
            stmt = repo._apply_global_filters(stmt, f)

            result = await self.session.execute(stmt)
            rows = result.all()

            logger.info(
                "  %s (col=%s): %d procuradores encontrados",
                table_name, person_col_name, len(rows),
            )

            for row in rows:
                totais[row.procurador][table_name] = row.total

        comparativo = []
        for proc, metricas in totais.items():
            # Excluir procuradores sem nenhuma pendência no histórico
            if filters.exclude_no_pendencias and metricas["pendencias"] == 0:
                continue
            total = sum(metricas.values())
            comparativo.append(
                ProcuradorComparativo(
                    procurador=proc,
                    **metricas,
                    total=total,
                )
            )

        comparativo.sort(key=lambda x: x.total, reverse=True)

        logger.info(
            "Comparativo finalizado: %d procuradores, top 3: %s",
            len(comparativo),
            [(c.procurador, c.total) for c in comparativo[:3]],
        )

        return comparativo

    # --- Helpers para médias de chefia ---

    @staticmethod
    def _compute_units_from_timelines(
        timelines: dict[str, list[TimelinePoint]],
        unit: str,
    ) -> tuple[int, str]:
        """Deriva o número de unidades temporais a partir das timelines coletadas.

        Extrai min/max período ("YYYY-MM") da união de todas as timelines
        e calcula a contagem de unidades via compute_units_count().
        Garante mínimo de 1 para evitar divisão por zero.
        """
        all_periods: set[str] = set()
        for points in timelines.values():
            for p in points:
                all_periods.add(p.periodo)

        if not all_periods:
            label_map = {"day": "dias", "month": "meses", "year": "anos"}
            return 1, label_map.get(unit, unit)

        min_period = min(all_periods)
        max_period = max(all_periods)

        start = date(int(min_period[:4]), int(min_period[5:7]), 1)

        max_year = int(max_period[:4])
        max_month = int(max_period[5:7])
        _, last_day = calendar.monthrange(max_year, max_month)
        end = date(max_year, max_month, last_day)

        return PerfilService.compute_units_count(start, end, unit)

    @staticmethod
    def compute_units_count(
        start: date, end: date, unit: str
    ) -> tuple[int, str]:
        """Calcula número de unidades temporais no intervalo.

        Retorna (contagem, rótulo). Mínimo de 1 para evitar divisão por zero.
        """
        if unit == "day":
            count = (end - start).days + 1
            label = "dias"
        elif unit == "month":
            count = (end.year - start.year) * 12 + (end.month - start.month) + 1
            label = "meses"
        elif unit == "year":
            count = end.year - start.year + 1
            label = "anos"
        else:
            count = 1
            label = unit

        return max(1, count), label

    async def _count_filtered_by_persons(
        self,
        table_name: str,
        filters: GlobalFilters,
        person_names: list[str],
    ) -> int:
        """Conta registros filtrados por lista de procuradores.

        Usa a coluna de atribuição correta (COMPARATIVO_PERSON_COL).
        """
        model = TABLE_MODEL_MAP[table_name]
        repo = self.repos[table_name]

        person_col_name = COMPARATIVO_PERSON_COL[table_name]
        raw_col = getattr(model, person_col_name)
        person_expr = normalize_procurador_expr(raw_col)

        stmt = (
            select(func.count())
            .select_from(model)
            .where(raw_col.isnot(None))
            .where(person_expr.in_(person_names))
        )
        stmt = repo._apply_global_filters(stmt, filters)

        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def _timeline_filtered_by_persons(
        self,
        table_name: str,
        filters: GlobalFilters,
        person_names: list[str],
    ) -> list[TimelinePoint]:
        """Timeline mensal filtrada por lista de procuradores."""
        model = TABLE_MODEL_MAP[table_name]
        repo = self.repos[table_name]

        person_col_name = COMPARATIVO_PERSON_COL[table_name]
        raw_col = getattr(model, person_col_name)
        person_expr = normalize_procurador_expr(raw_col)

        date_col = repo._get_date_column()
        period_expr = func.to_char(date_col, "YYYY-MM")

        stmt = (
            select(period_expr.label("periodo"), func.count().label("total"))
            .select_from(model)
            .where(date_col.isnot(None))
            .where(raw_col.isnot(None))
            .where(person_expr.in_(person_names))
            .group_by(period_expr)
            .order_by(period_expr)
        )
        stmt = repo._apply_global_filters(stmt, filters)

        result = await self.session.execute(stmt)
        return [
            TimelinePoint(periodo=row.periodo, valor=row.total)
            for row in result.all()
        ]

    @cached(ttl=300)
    async def get_chefia_medias(
        self,
        chefia: str,
        filters: GlobalFilters,
        average_unit: str = "month",
        procurador_nomes: list[str] | None = None,
    ) -> ChefiaMediasResponse:
        """KPIs com média por unidade temporal para visão de chefia.

        Permite filtrar por procuradores específicos.
        Retorna totais, médias e timeline filtrada.
        """
        f = self._build_filters("chefia", chefia, filters)

        labels: dict[str, str] = {
            "processos_novos": "Processos Novos",
            "pecas_finalizadas": "Peças Finalizadas",
            "pendencias": "Pendências",
        }

        use_person_filter = bool(procurador_nomes)

        # Coleta totais e timelines
        totals: dict[str, int] = {}
        timelines: dict[str, list[TimelinePoint]] = {}

        for table_name, label in labels.items():
            if use_person_filter:
                totals[table_name] = await self._count_filtered_by_persons(
                    table_name, f, procurador_nomes
                )
                timelines[table_name] = await self._timeline_filtered_by_persons(
                    table_name, f, procurador_nomes
                )
            else:
                totals[table_name] = await self.repos[table_name].total_count(f)
                timelines[table_name] = await self.repos[table_name].count_by_period(f)

        # Calcula médias a partir do range real das timelines coletadas
        units, unit_label = self._compute_units_from_timelines(timelines, average_unit)

        # Quando há procuradores selecionados, a média é por pessoa
        n_persons = len(procurador_nomes) if use_person_filter and procurador_nomes else 1

        kpis = []
        for table_name, label in labels.items():
            total = totals[table_name]
            media = round(total / units / n_persons, 2)
            kpis.append(ChefiaMediaKPI(label=label, total=total, media=media))

        # Monta séries de timeline
        timeline = [
            TimelineSeries(nome=label, dados=timelines[table_name])
            for table_name, label in labels.items()
        ]

        return ChefiaMediasResponse(
            kpis=kpis,
            timeline=timeline,
            units_count=units,
            unit_label=unit_label,
            person_count=n_persons,
        )
