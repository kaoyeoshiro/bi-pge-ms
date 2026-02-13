"""Repositório para a tabela processos_novos."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.filters import GlobalFilters
from src.domain.models import ProcessoNovo
from src.repositories.base_repository import BaseRepository


class ProcessosRepository(BaseRepository):
    """Operações sobre processos novos."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, ProcessoNovo)

    async def valor_aggregates(self, filters: GlobalFilters) -> tuple[float, float]:
        """Retorna (soma, média) de valor_acao de TODOS os processos no banco.

        O valor da causa é propriedade imutável do processo — não faz sentido
        filtrar por ano/data. Apenas o filtro de faixa (valor_min/valor_max)
        é aplicado.
        """
        stmt = select(
            func.coalesce(func.sum(ProcessoNovo.valor_acao), 0),
            func.coalesce(func.avg(ProcessoNovo.valor_acao), 0),
        ).select_from(ProcessoNovo).where(ProcessoNovo.valor_acao.isnot(None))

        if filters.valor_min is not None:
            stmt = stmt.where(ProcessoNovo.valor_acao >= filters.valor_min)
        if filters.valor_max is not None:
            stmt = stmt.where(ProcessoNovo.valor_acao <= filters.valor_max)

        result = await self.session.execute(stmt)
        row = result.one()
        return float(row[0]), float(row[1])
