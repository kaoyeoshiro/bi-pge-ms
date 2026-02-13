"""Serviço de análise de valores da causa."""

from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.filters import GlobalFilters, PaginationParams
from src.domain.schemas import (
    KPIValue,
    PaginatedResponse,
    TimelineSeries,
    TimelinePoint,
    ValorFaixaItem,
    ValorGroupItem,
)
from src.repositories.valores_repository import ValoresRepository
from src.services.cache import cached


class ValoresService:
    """Orquestra dados de valor da causa."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = ValoresRepository(session)

    @cached(ttl=300)
    async def get_kpis(self, filters: GlobalFilters) -> list[KPIValue]:
        """KPIs de valor da causa: total, média, mediana, qtd, %."""
        agg = await self.repo.get_aggregates(filters)

        return [
            KPIValue(label="Valor Total Causas", valor=agg["soma"], formato="moeda"),
            KPIValue(label="Valor Médio", valor=agg["media"], formato="moeda"),
            KPIValue(label="Valor Mediano", valor=agg["mediana"], formato="moeda"),
            KPIValue(
                label="Processos com Valor",
                valor=agg["qtd_com_valor"],
                formato="inteiro",
            ),
            KPIValue(
                label="% com Valor Informado",
                valor=agg["pct_com_valor"],
                formato="percentual",
            ),
        ]

    @cached(ttl=300)
    async def get_distribuicao(self, filters: GlobalFilters) -> list[ValorFaixaItem]:
        """Distribuição de processos por faixa de valor."""
        return await self.repo.get_distribuicao(filters)

    @cached(ttl=300)
    async def get_por_grupo(
        self,
        filters: GlobalFilters,
        grupo: str,
        metrica: str = "total",
        limit: int = 15,
    ) -> list[ValorGroupItem]:
        """Ranking por dimensão (chefia, procurador, assunto)."""
        return await self.repo.get_por_grupo(filters, grupo, metrica, limit)

    @cached(ttl=300)
    async def get_timeline(self, filters: GlobalFilters) -> list[TimelineSeries]:
        """Séries temporais de valor total e médio mensal."""
        rows = await self.repo.get_timeline(filters)

        serie_total = TimelineSeries(
            nome="Valor Total",
            dados=[
                TimelinePoint(periodo=r.periodo, valor=int(r.valor_total))
                for r in rows
            ],
        )
        serie_medio = TimelineSeries(
            nome="Valor Médio",
            dados=[
                TimelinePoint(periodo=r.periodo, valor=int(r.valor_medio))
                for r in rows
            ],
        )

        return [serie_total, serie_medio]

    async def list_processos(
        self, filters: GlobalFilters, pagination: PaginationParams
    ) -> PaginatedResponse:
        """Lista paginada de processos com valor."""
        return await self.repo.list_paginated(filters, pagination)
