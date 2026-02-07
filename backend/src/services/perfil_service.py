"""Serviço para análise individualizada de procurador ou chefia."""

from collections import defaultdict
from dataclasses import asdict

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.filters import GlobalFilters, PaginationParams
from src.domain.models import (
    PecaElaborada,
    PecaFinalizada,
    Pendencia,
    ProcessoNovo,
    TABLE_MODEL_MAP,
)
from src.domain.schemas import (
    GroupCount,
    KPIValue,
    PaginatedResponse,
    ProcuradorComparativo,
    TimelineSeries,
)
from src.repositories.base_repository import BaseRepository
from src.services.cache import cached
from src.services.normalization import normalize_procurador_expr


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
        """KPIs: totais nas 4 tabelas para o indivíduo selecionado."""
        f = self._build_filters(dimensao, valor, filters)

        processos = await self.repos["processos_novos"].total_count(f)
        elaboradas = await self.repos["pecas_elaboradas"].total_count(f)
        finalizadas = await self.repos["pecas_finalizadas"].total_count(f)
        pendencias = await self.repos["pendencias"].total_count(f)

        return [
            KPIValue(label="Processos Novos", valor=processos),
            KPIValue(label="Peças Elaboradas", valor=elaboradas),
            KPIValue(label="Peças Finalizadas", valor=finalizadas),
            KPIValue(label="Pendências", valor=pendencias),
        ]

    @cached(ttl=300)
    async def get_timeline(
        self, dimensao: str, valor: str, filters: GlobalFilters
    ) -> list[TimelineSeries]:
        """Séries temporais mensais nas 4 tabelas."""
        f = self._build_filters(dimensao, valor, filters)

        labels = {
            "processos_novos": "Processos Novos",
            "pecas_elaboradas": "Peças Elaboradas",
            "pecas_finalizadas": "Peças Finalizadas",
            "pendencias": "Pendências",
        }

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
        """Ranking por procurador: quais procuradores o assessor atendeu."""
        f = self._build_filters(dimensao, valor, filters)
        repo = self.repos[tabela]
        return await repo.count_by_group(f, "procurador", limit)

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
        """Comparativo de métricas entre procuradores de uma chefia.

        Executa 4 queries (uma por tabela), agrupando por procurador,
        e mescla os resultados num único ranking.
        """
        f = self._build_filters("chefia", chefia, filters)
        totais: dict[str, dict[str, int]] = defaultdict(
            lambda: {
                "processos_novos": 0,
                "pecas_elaboradas": 0,
                "pecas_finalizadas": 0,
                "pendencias": 0,
            }
        )

        table_models = {
            "processos_novos": ProcessoNovo,
            "pecas_elaboradas": PecaElaborada,
            "pecas_finalizadas": PecaFinalizada,
            "pendencias": Pendencia,
        }

        for table_name, model in table_models.items():
            repo = self.repos[table_name]
            proc_expr = normalize_procurador_expr(model.procurador)

            stmt = (
                select(proc_expr.label("procurador"), func.count().label("total"))
                .select_from(model)
                .where(model.procurador.isnot(None))
                .where(model.procurador != "")
                .group_by(proc_expr)
            )
            stmt = repo._apply_global_filters(stmt, f)

            result = await self.session.execute(stmt)
            for row in result.all():
                totais[row.procurador][table_name] = row.total

        # Montar lista ordenada por total decrescente
        comparativo = []
        for proc, metricas in totais.items():
            total = sum(metricas.values())
            comparativo.append(
                ProcuradorComparativo(
                    procurador=proc,
                    **metricas,
                    total=total,
                )
            )

        comparativo.sort(key=lambda x: x.total, reverse=True)
        return comparativo
