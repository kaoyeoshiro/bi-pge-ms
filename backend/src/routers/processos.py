"""Router de processos novos."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_session
from src.dependencies import parse_global_filters, parse_pagination
from src.domain.filters import GlobalFilters, PaginationParams
from src.domain.schemas import GroupCount, KPIValue, PaginatedResponse, TimelineSeries
from src.services.processos_service import ProcessosService

router = APIRouter(prefix="/api/processos", tags=["Processos"])


@router.get("/kpis", response_model=list[KPIValue])
async def get_kpis(
    filters: GlobalFilters = Depends(parse_global_filters),
    session: AsyncSession = Depends(get_session),
) -> list[KPIValue]:
    """KPIs de processos."""
    service = ProcessosService(session)
    return await service.get_kpis(filters)


@router.get("/timeline", response_model=list[TimelineSeries])
async def get_timeline(
    filters: GlobalFilters = Depends(parse_global_filters),
    session: AsyncSession = Depends(get_session),
) -> list[TimelineSeries]:
    """Série temporal de processos novos."""
    service = ProcessosService(session)
    return await service.get_timeline(filters)


@router.get("/por-chefia", response_model=list[GroupCount])
async def get_por_chefia(
    filters: GlobalFilters = Depends(parse_global_filters),
    limit: int = Query(15, ge=1, le=50),
    session: AsyncSession = Depends(get_session),
) -> list[GroupCount]:
    """Ranking por chefia."""
    service = ProcessosService(session)
    return await service.get_por_chefia(filters, limit)


@router.get("/por-procurador", response_model=list[GroupCount])
async def get_por_procurador(
    filters: GlobalFilters = Depends(parse_global_filters),
    limit: int = Query(15, ge=1, le=50),
    session: AsyncSession = Depends(get_session),
) -> list[GroupCount]:
    """Ranking por procurador."""
    service = ProcessosService(session)
    return await service.get_por_procurador(filters, limit)


@router.get("/lista", response_model=PaginatedResponse)
async def list_processos(
    filters: GlobalFilters = Depends(parse_global_filters),
    pagination: PaginationParams = Depends(parse_pagination),
    session: AsyncSession = Depends(get_session),
) -> PaginatedResponse:
    """Lista paginada de processos."""
    service = ProcessosService(session)
    return await service.list_processos(filters, pagination)
