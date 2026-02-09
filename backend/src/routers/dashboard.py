"""Router do dashboard Overview."""

from datetime import date

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_session
from src.dependencies import parse_global_filters
from src.domain.filters import GlobalFilters
from src.domain.schemas import GroupCount, KPIValue, TimelineSeries
from src.services.dashboard_service import DashboardService

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


class LastUpdatedResponse(BaseModel):
    """Data mais recente dos dados disponíveis no BI."""

    data: date | None


@router.get("/last-updated", response_model=LastUpdatedResponse)
async def get_last_updated(
    session: AsyncSession = Depends(get_session),
) -> LastUpdatedResponse:
    """Retorna a data mais recente dentre todas as tabelas de dados."""
    service = DashboardService(session)
    last_date = await service.get_last_updated()
    return LastUpdatedResponse(data=last_date)


@router.get("/kpis", response_model=list[KPIValue])
async def get_kpis(
    filters: GlobalFilters = Depends(parse_global_filters),
    session: AsyncSession = Depends(get_session),
) -> list[KPIValue]:
    """Retorna os 4 KPIs principais do Overview."""
    service = DashboardService(session)
    return await service.get_kpis(filters)


@router.get("/timeline", response_model=list[TimelineSeries])
async def get_timeline(
    filters: GlobalFilters = Depends(parse_global_filters),
    session: AsyncSession = Depends(get_session),
) -> list[TimelineSeries]:
    """Retorna séries temporais mensais das 4 métricas."""
    service = DashboardService(session)
    return await service.get_timeline(filters)


@router.get("/top-chefias", response_model=list[GroupCount])
async def get_top_chefias(
    filters: GlobalFilters = Depends(parse_global_filters),
    limit: int = Query(500, ge=1, le=1000),
    metrica: str = Query(
        "pecas_finalizadas",
        pattern=r"^(processos_novos|pecas_finalizadas|pendencias)$",
    ),
    session: AsyncSession = Depends(get_session),
) -> list[GroupCount]:
    """Retorna top N chefias por volume da métrica selecionada."""
    service = DashboardService(session)
    return await service.get_top_chefias(filters, limit, metrica)


@router.get("/top-procuradores", response_model=list[GroupCount])
async def get_top_procuradores(
    filters: GlobalFilters = Depends(parse_global_filters),
    limit: int = Query(500, ge=1, le=1000),
    metrica: str = Query(
        "pecas_finalizadas",
        pattern=r"^(pecas_finalizadas|pendencias)$",
    ),
    session: AsyncSession = Depends(get_session),
) -> list[GroupCount]:
    """Retorna top N procuradores por volume da métrica selecionada.

    Processos novos não é métrica individual de procurador (titularidade muda).
    """
    service = DashboardService(session)
    return await service.get_top_procuradores(filters, limit, metrica)
