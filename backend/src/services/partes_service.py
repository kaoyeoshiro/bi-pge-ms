"""Serviço de partes/demandantes normalizados."""

from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.schemas import (
    ParteNormalizadaResponse,
    PartesKPIsResponse,
    PartesRankingResponse,
)
from src.repositories.partes_repository import PartesRepository
from src.services.cache import cached


class PartesService:
    """Orquestra consultas de partes normalizadas."""

    def __init__(self, session: AsyncSession):
        self.repo = PartesRepository(session)

    @cached(ttl=3600)
    async def get_kpis(self) -> PartesKPIsResponse:
        """Retorna KPIs gerais."""
        data = await self.repo.get_kpis()
        return PartesKPIsResponse(**data)

    async def get_ranking(
        self,
        role: str | None = None,
        search: str | None = None,
        sort_by: str = "qtd_processos",
        sort_order: str = "desc",
        page: int = 1,
        page_size: int = 25,
    ) -> PartesRankingResponse:
        """Retorna ranking paginado."""
        data = await self.repo.get_ranking(
            role=role,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            page_size=page_size,
        )
        data["items"] = [ParteNormalizadaResponse(**item) for item in data["items"]]
        return PartesRankingResponse(**data)

    async def get_by_id(self, parte_id: int) -> ParteNormalizadaResponse | None:
        """Retorna detalhes de uma parte por ID."""
        data = await self.repo.get_by_id(parte_id)
        if not data:
            return None
        return ParteNormalizadaResponse(**data)

    async def get_processos(
        self,
        parte_id: int,
        page: int = 1,
        page_size: int = 25,
    ) -> dict:
        """Retorna processos vinculados a uma parte."""
        return await self.repo.get_processos_da_parte(
            parte_id=parte_id,
            page=page,
            page_size=page_size,
        )
