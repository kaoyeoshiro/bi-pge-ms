"""Serviço de processos novos."""

from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.filters import GlobalFilters, PaginationParams
from src.domain.schemas import (
    GroupCount,
    KPIValue,
    PaginatedResponse,
    TimelineSeries,
)
from src.repositories.processos_repository import ProcessosRepository
from src.services.cache import cached


class ProcessosService:
    """Orquestra dados de processos novos."""

    def __init__(self, session: AsyncSession):
        self.repo = ProcessosRepository(session)

    @cached(ttl=300)
    async def get_kpis(self, filters: GlobalFilters) -> list[KPIValue]:
        """KPIs: total, média mensal, valor total e valor médio."""
        total = await self.repo.total_count(filters)
        timeline = await self.repo.count_by_period(filters)
        meses = len(timeline) if timeline else 1
        media_mes = round(total / meses) if meses > 0 else 0
        valor_total, valor_medio = await self.repo.valor_aggregates(filters)

        return [
            KPIValue(label="Total de Processos", valor=total),
            KPIValue(label="Média por Mês", valor=media_mes),
            KPIValue(label="Valor Total Causas", valor=valor_total, formato="moeda"),
            KPIValue(label="Valor Médio Causa", valor=valor_medio, formato="moeda"),
        ]

    @cached(ttl=300)
    async def get_timeline(self, filters: GlobalFilters) -> list[TimelineSeries]:
        """Série temporal de processos novos."""
        data = await self.repo.count_by_period(filters)
        return [TimelineSeries(nome="Processos Novos", dados=data)]

    @cached(ttl=300)
    async def get_por_chefia(
        self, filters: GlobalFilters, limit: int = 15
    ) -> list[GroupCount]:
        """Ranking por chefia."""
        return await self.repo.count_by_group(filters, "chefia", limit)

    @cached(ttl=300)
    async def get_por_procurador(
        self, filters: GlobalFilters, limit: int = 15
    ) -> list[GroupCount]:
        """Ranking por procurador."""
        return await self.repo.count_by_group(filters, "procurador", limit)

    async def list_processos(
        self, filters: GlobalFilters, pagination: PaginationParams
    ) -> PaginatedResponse:
        """Lista paginada de processos."""
        return await self.repo.list_paginated(filters, pagination)
