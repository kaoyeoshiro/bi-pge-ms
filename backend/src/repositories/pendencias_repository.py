"""Repositório para a tabela pendencias."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.filters import GlobalFilters
from src.domain.models import Pendencia
from src.repositories.base_repository import BaseRepository


class PendenciasRepository(BaseRepository):
    """Operações sobre pendências."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, Pendencia)

    async def count_obrigatorias(self, filters: GlobalFilters) -> int:
        """Conta pendências com manifestação obrigatória."""
        stmt = (
            select(func.count())
            .select_from(Pendencia)
            .where(Pendencia.categoria_pendencia == "Manifestação obrigatória")
        )
        stmt = self._apply_global_filters(stmt, filters)
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def count_opcionais(self, filters: GlobalFilters) -> int:
        """Conta pendências com manifestação opcional."""
        stmt = (
            select(func.count())
            .select_from(Pendencia)
            .where(Pendencia.categoria_pendencia == "Manifestação opcional")
        )
        stmt = self._apply_global_filters(stmt, filters)
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def count_by_tipo(
        self, filters: GlobalFilters
    ) -> list[dict[str, int | str]]:
        """Conta pendências agrupadas por categoria_pendencia."""
        stmt = (
            select(
                Pendencia.categoria_pendencia.label("grupo"),
                func.count().label("total"),
            )
            .where(Pendencia.categoria_pendencia.isnot(None))
            .group_by(Pendencia.categoria_pendencia)
            .order_by(func.count().desc())
        )
        stmt = self._apply_global_filters(stmt, filters)
        result = await self.session.execute(stmt)
        return [
            {"grupo": row.grupo, "total": row.total}
            for row in result.all()
        ]
