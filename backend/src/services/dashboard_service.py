"""Serviço para o dashboard Overview."""

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.filters import GlobalFilters
from src.domain.models import (
    PecaElaborada,
    PecaFinalizada,
    Pendencia,
    ProcessoNovo,
    TABLE_MODEL_MAP,
)
from src.domain.schemas import GroupCount, KPIValue, TimelineSeries
from src.repositories.base_repository import BaseRepository
from src.repositories.overview_repository import OverviewRepository
from src.repositories.processos_repository import ProcessosRepository
from src.repositories.pecas_repository import PecasElaboradasRepository
from src.services.cache import cached


class DashboardService:
    """Orquestra dados do Overview."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.overview_repo = OverviewRepository(session)
        self.processos_repo = ProcessosRepository(session)
        self.pecas_repo = PecasElaboradasRepository(session)

    def _get_repo_for_metrica(self, metrica: str) -> BaseRepository:
        """Retorna repositório correspondente à métrica selecionada."""
        model = TABLE_MODEL_MAP[metrica]
        return BaseRepository(self.session, model)

    @cached(ttl=300)
    async def get_kpis(self, filters: GlobalFilters) -> list[KPIValue]:
        """Retorna os 4 KPIs principais."""
        return await self.overview_repo.get_kpis(filters)

    @cached(ttl=300)
    async def get_timeline(
        self, filters: GlobalFilters
    ) -> list[TimelineSeries]:
        """Retorna séries temporais mensais."""
        return await self.overview_repo.get_timeline(filters)

    @cached(ttl=300)
    async def get_top_chefias(
        self,
        filters: GlobalFilters,
        limit: int = 10,
        metrica: str = "pecas_finalizadas",
    ) -> list[GroupCount]:
        """Retorna top N chefias pela métrica selecionada."""
        repo = self._get_repo_for_metrica(metrica)
        return await repo.count_by_group(filters, "chefia", limit)

    @cached(ttl=300)
    async def get_top_procuradores(
        self,
        filters: GlobalFilters,
        limit: int = 10,
        metrica: str = "pecas_finalizadas",
    ) -> list[GroupCount]:
        """Retorna top N procuradores pela métrica selecionada."""
        repo = self._get_repo_for_metrica(metrica)
        return await repo.count_by_group(filters, "procurador", limit)

    @cached(ttl=3600)
    async def get_last_updated(self) -> date | None:
        """Retorna a data mais recente dentre todas as tabelas de dados."""
        date_columns = [
            func.max(ProcessoNovo.data),
            func.max(PecaElaborada.data),
            func.max(Pendencia.data),
            func.max(PecaFinalizada.data_finalizacao),
        ]
        queries = [select(col) for col in date_columns]
        max_dates: list[date | None] = []
        for query in queries:
            result = await self.session.execute(query)
            val = result.scalar()
            if val is not None:
                max_dates.append(val.date() if hasattr(val, "date") else val)
        return max(max_dates) if max_dates else None
