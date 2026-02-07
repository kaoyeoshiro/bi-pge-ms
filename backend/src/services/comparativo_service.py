"""Serviço de comparativos entre chefias, procuradores e períodos."""

from dataclasses import replace
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.filters import GlobalFilters
from src.repositories.overview_repository import OverviewRepository
from src.services.cache import cached


class ComparativoService:
    """Compara métricas entre entidades ou períodos."""

    def __init__(self, session: AsyncSession):
        self.overview_repo = OverviewRepository(session)

    @cached(ttl=300)
    async def comparar_chefias(
        self, chefias: list[str], filters: GlobalFilters
    ) -> list[dict]:
        """Compara KPIs entre N chefias."""
        resultados = []
        for chefia in chefias:
            filtro_chefia = replace(filters, chefia=[chefia])
            kpis = await self.overview_repo.get_kpis(filtro_chefia)
            resultados.append({
                "chefia": chefia,
                "metricas": [kpi.model_dump() for kpi in kpis],
            })
        return resultados

    @cached(ttl=300)
    async def comparar_procuradores(
        self, procuradores: list[str], filters: GlobalFilters
    ) -> list[dict]:
        """Compara KPIs entre N procuradores."""
        resultados = []
        for proc in procuradores:
            filtro_proc = replace(filters, procurador=[proc])
            kpis = await self.overview_repo.get_kpis(filtro_proc)
            resultados.append({
                "procurador": proc,
                "metricas": [kpi.model_dump() for kpi in kpis],
            })
        return resultados

    @cached(ttl=300)
    async def comparar_periodos(
        self,
        p1_inicio: date,
        p1_fim: date,
        p2_inicio: date,
        p2_fim: date,
        filters: GlobalFilters,
    ) -> dict:
        """Compara KPIs entre 2 períodos."""
        filtro_p1 = replace(filters, data_inicio=p1_inicio, data_fim=p1_fim)
        filtro_p2 = replace(filters, data_inicio=p2_inicio, data_fim=p2_fim)

        kpis_p1 = await self.overview_repo.get_kpis(filtro_p1)
        kpis_p2 = await self.overview_repo.get_kpis(filtro_p2)

        return {
            "periodo_1": {
                "inicio": str(p1_inicio),
                "fim": str(p1_fim),
                "metricas": [kpi.model_dump() for kpi in kpis_p1],
            },
            "periodo_2": {
                "inicio": str(p2_inicio),
                "fim": str(p2_fim),
                "metricas": [kpi.model_dump() for kpi in kpis_p2],
            },
        }
