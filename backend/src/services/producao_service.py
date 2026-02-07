"""Serviço de produção (peças elaboradas e finalizadas)."""

from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.filters import GlobalFilters, PaginationParams
from src.domain.schemas import (
    GroupCount,
    KPIValue,
    PaginatedResponse,
    TimelinePoint,
    TimelineSeries,
)
from src.repositories.pecas_repository import (
    PecasElaboradasRepository,
    PecasFinalizadasRepository,
)
from src.services.cache import cached


class ProducaoService:
    """Orquestra dados de produção jurídica."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.elab_repo = PecasElaboradasRepository(session)
        self.final_repo = PecasFinalizadasRepository(session)

    @cached(ttl=300)
    async def get_kpis(self, filters: GlobalFilters) -> list[KPIValue]:
        """KPIs de produção: elaboradas, finalizadas, taxa, média/dia."""
        total_elab = await self.elab_repo.total_count(filters)
        total_final = await self.final_repo.total_count(filters)

        taxa = round(total_final / total_elab * 100, 2) if total_elab > 0 else 0.0
        # Estima média por dia útil (~22 dias/mês)
        timeline = await self.elab_repo.count_by_period(filters)
        meses = len(timeline) if timeline else 1
        media_dia = round(total_elab / (meses * 22), 2) if meses > 0 else 0.0

        return [
            KPIValue(label="Peças Elaboradas", valor=total_elab),
            KPIValue(label="Peças Finalizadas", valor=total_final),
            KPIValue(label="Taxa de Conclusão (%)", valor=taxa, formato="percentual"),
            KPIValue(label="Média por Dia Útil", valor=media_dia, formato="decimal"),
        ]

    @cached(ttl=300)
    async def get_timeline(
        self, filters: GlobalFilters
    ) -> list[TimelineSeries]:
        """Séries temporais de elaboradas e finalizadas."""
        elab_data = await self.elab_repo.count_by_period(filters)
        final_data = await self.final_repo.count_by_period(filters)

        return [
            TimelineSeries(nome="Elaboradas", dados=elab_data),
            TimelineSeries(nome="Finalizadas", dados=final_data),
        ]

    def _get_repo(self, tipo: str) -> PecasElaboradasRepository | PecasFinalizadasRepository:
        """Retorna repositório conforme o tipo selecionado."""
        if tipo == "finalizadas":
            return self.final_repo
        return self.elab_repo

    @cached(ttl=300)
    async def get_por_categoria(
        self, filters: GlobalFilters, limit: int = 15, tipo: str = "elaboradas"
    ) -> list[GroupCount]:
        """Ranking por categoria de peça."""
        return await self._get_repo(tipo).count_by_group(filters, "categoria", limit)

    @cached(ttl=300)
    async def get_por_chefia(
        self, filters: GlobalFilters, limit: int = 15, tipo: str = "elaboradas"
    ) -> list[GroupCount]:
        """Ranking por chefia."""
        return await self._get_repo(tipo).count_by_group(filters, "chefia", limit)

    @cached(ttl=300)
    async def get_por_procurador(
        self, filters: GlobalFilters, limit: int = 15, tipo: str = "elaboradas"
    ) -> list[GroupCount]:
        """Ranking por procurador."""
        return await self._get_repo(tipo).count_by_group(filters, "procurador", limit)

    @cached(ttl=300)
    async def get_por_usuario(
        self, filters: GlobalFilters, limit: int = 15, tipo: str = "elaboradas"
    ) -> list[GroupCount]:
        """Ranking por usuário criador/finalizador."""
        return await self._get_repo(tipo).count_by_usuario(filters, limit)

    async def list_elaboradas(
        self, filters: GlobalFilters, pagination: PaginationParams
    ) -> PaginatedResponse:
        """Lista paginada de peças elaboradas."""
        return await self.elab_repo.list_paginated(filters, pagination)

    async def list_finalizadas(
        self, filters: GlobalFilters, pagination: PaginationParams
    ) -> PaginatedResponse:
        """Lista paginada de peças finalizadas."""
        return await self.final_repo.list_paginated(filters, pagination)
