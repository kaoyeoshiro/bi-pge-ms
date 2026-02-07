"""Repositório para peças elaboradas e finalizadas."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.filters import GlobalFilters
from src.domain.models import PecaElaborada, PecaFinalizada
from src.domain.schemas import GroupCount
from src.repositories.base_repository import BaseRepository


class PecasElaboradasRepository(BaseRepository):
    """Operações sobre peças elaboradas."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, PecaElaborada)

    async def count_by_usuario(
        self, filters: GlobalFilters, limit: int = 10
    ) -> list[GroupCount]:
        """Ranking de usuários criadores por volume."""
        return await self.count_by_group(filters, "usuario_criacao", limit)


class PecasFinalizadasRepository(BaseRepository):
    """Operações sobre peças finalizadas."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, PecaFinalizada)

    async def count_by_usuario(
        self, filters: GlobalFilters, limit: int = 10
    ) -> list[GroupCount]:
        """Ranking de usuários finalizadores por volume."""
        return await self.count_by_group(filters, "usuario_finalizacao", limit)
