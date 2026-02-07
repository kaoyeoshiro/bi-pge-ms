"""Serviço de pendências."""

from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.filters import GlobalFilters, PaginationParams
from src.domain.schemas import (
    GroupCount,
    KPIValue,
    PaginatedResponse,
    TimelineSeries,
)
from src.repositories.pendencias_repository import PendenciasRepository
from src.services.cache import cached


class PendenciasService:
    """Orquestra dados de pendências."""

    def __init__(self, session: AsyncSession):
        self.repo = PendenciasRepository(session)

    @cached(ttl=300)
    async def get_kpis(self, filters: GlobalFilters) -> list[KPIValue]:
        """KPIs: total, obrigatórias, opcionais, % obrigatórias."""
        total = await self.repo.total_count(filters)
        obrigatorias = await self.repo.count_obrigatorias(filters)
        opcionais = await self.repo.count_opcionais(filters)
        pct = round(obrigatorias / total * 100, 2) if total > 0 else 0.0

        return [
            KPIValue(label="Total de Pendências", valor=total),
            KPIValue(label="Obrigatórias", valor=obrigatorias),
            KPIValue(label="Opcionais", valor=opcionais),
            KPIValue(label="% Obrigatórias", valor=pct, formato="percentual"),
        ]

    @cached(ttl=300)
    async def get_timeline(self, filters: GlobalFilters) -> list[TimelineSeries]:
        """Série temporal mensal de pendências."""
        data = await self.repo.count_by_period(filters)
        return [TimelineSeries(nome="Pendências", dados=data)]

    @cached(ttl=300)
    async def get_por_area(
        self, filters: GlobalFilters, limit: int = 15
    ) -> list[GroupCount]:
        """Ranking por área jurídica."""
        return await self.repo.count_by_group(filters, "area", limit)

    @cached(ttl=300)
    async def get_por_tipo(
        self, filters: GlobalFilters
    ) -> list[dict[str, int | str]]:
        """Contagem por categoria de pendência (obrigatória/opcional)."""
        return await self.repo.count_by_tipo(filters)

    @cached(ttl=300)
    async def get_por_categoria(
        self, filters: GlobalFilters, limit: int = 15
    ) -> list[GroupCount]:
        """Ranking por categoria."""
        return await self.repo.count_by_group(filters, "categoria", limit)

    @cached(ttl=300)
    async def get_por_chefia(
        self, filters: GlobalFilters, limit: int = 15
    ) -> list[GroupCount]:
        """Ranking por chefia."""
        return await self.repo.count_by_group(filters, "chefia", limit)

    async def list_pendencias(
        self, filters: GlobalFilters, pagination: PaginationParams
    ) -> PaginatedResponse:
        """Lista paginada de pendências."""
        return await self.repo.list_paginated(filters, pagination)
