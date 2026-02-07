"""Serviço para carregar opções dos filtros globais."""

import logging

from sqlalchemy import func, select, distinct
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.models import PecaElaborada, Pendencia, ProcessoNovo, UserRole
from src.domain.schemas import FilterOptions
from src.services.cache import cached
from src.services.normalization import normalize_chefia_expr, normalize_procurador_expr

logger = logging.getLogger(__name__)


class FilterOptionsService:
    """Carrega valores distintos para popular os dropdowns de filtro."""

    def __init__(self, session: AsyncSession):
        self.session = session

    @cached(ttl=3600)
    async def get_options(self) -> FilterOptions:
        """Retorna todas as opções de filtro disponíveis."""
        chefias = await self._distinct_values(ProcessoNovo, "chefia")
        procuradores = await self._distinct_values(ProcessoNovo, "procurador")
        categorias = await self._distinct_values(PecaElaborada, "categoria")
        areas = await self._distinct_values(Pendencia, "area")
        anos = await self._get_anos()

        return FilterOptions(
            chefias=chefias,
            procuradores=procuradores,
            categorias=categorias,
            areas=areas,
            anos=anos,
        )

    def _get_normalized_expr(self, model: type, column: str):
        """Retorna expressão normalizada para a coluna quando aplicável."""
        col = getattr(model, column)
        if column == "chefia":
            return normalize_chefia_expr(col)
        if column == "procurador":
            return normalize_procurador_expr(col)
        return col

    async def _distinct_values(
        self, model: type, column: str
    ) -> list[str]:
        """Busca valores distintos de uma coluna com normalização."""
        col = getattr(model, column)
        expr = self._get_normalized_expr(model, column)

        stmt = (
            select(expr.label("valor"))
            .where(col.isnot(None))
            .where(col != "")
            .distinct()
            .order_by(expr)
        )
        result = await self.session.execute(stmt)
        return [str(row[0]) for row in result.all()]

    @cached(ttl=3600)
    async def get_assessores(self) -> list[str]:
        """Retorna nomes de assessores consultando user_roles, com fallback."""
        # Tentar consultar tabela user_roles primeiro
        try:
            stmt = (
                select(UserRole.name)
                .where(UserRole.role == "assessor")
                .order_by(UserRole.name)
            )
            result = await self.session.execute(stmt)
            names = [str(row[0]) for row in result.all()]
            if names:
                return names
        except Exception:
            logger.debug("Tabela user_roles não disponível, usando fallback.")

        # Fallback: lógica original por exclusão
        proc_subq = (
            select(distinct(PecaElaborada.procurador))
            .where(PecaElaborada.procurador.isnot(None))
            .scalar_subquery()
        )
        stmt = (
            select(distinct(PecaElaborada.usuario_criacao))
            .where(PecaElaborada.usuario_criacao.isnot(None))
            .where(PecaElaborada.usuario_criacao != "")
            .where(PecaElaborada.usuario_criacao.notin_(proc_subq))
            .order_by(PecaElaborada.usuario_criacao)
        )
        result = await self.session.execute(stmt)
        return [str(row[0]) for row in result.all()]

    async def _get_anos(self) -> list[int]:
        """Retorna anos disponíveis nos dados."""
        stmt = (
            select(func.extract("year", ProcessoNovo.data).label("ano"))
            .where(ProcessoNovo.data.isnot(None))
            .distinct()
            .order_by(func.extract("year", ProcessoNovo.data))
        )
        result = await self.session.execute(stmt)
        return [int(row.ano) for row in result.all()]
