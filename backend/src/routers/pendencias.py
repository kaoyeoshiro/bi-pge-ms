"""Router de pendências."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_session
from src.dependencies import parse_global_filters, parse_pagination
from src.domain.filters import GlobalFilters, PaginationParams
from src.domain.schemas import GroupCount, KPIValue, PaginatedResponse, TimelineSeries
from src.services.pendencias_service import PendenciasService

router = APIRouter(prefix="/api/pendencias", tags=["Pendências"])


@router.get("/kpis", response_model=list[KPIValue])
async def get_kpis(
    filters: GlobalFilters = Depends(parse_global_filters),
    session: AsyncSession = Depends(get_session),
) -> list[KPIValue]:
    """KPIs de pendências."""
    service = PendenciasService(session)
    return await service.get_kpis(filters)


@router.get("/timeline", response_model=list[TimelineSeries])
async def get_timeline(
    filters: GlobalFilters = Depends(parse_global_filters),
    session: AsyncSession = Depends(get_session),
) -> list[TimelineSeries]:
    """Série temporal de pendências."""
    service = PendenciasService(session)
    return await service.get_timeline(filters)


@router.get("/por-area", response_model=list[GroupCount])
async def get_por_area(
    filters: GlobalFilters = Depends(parse_global_filters),
    limit: int = Query(500, ge=1, le=1000),
    session: AsyncSession = Depends(get_session),
) -> list[GroupCount]:
    """Ranking por área jurídica."""
    service = PendenciasService(session)
    return await service.get_por_area(filters, limit)


@router.get("/por-tipo")
async def get_por_tipo(
    filters: GlobalFilters = Depends(parse_global_filters),
    session: AsyncSession = Depends(get_session),
):
    """Contagem por tipo de pendência."""
    service = PendenciasService(session)
    return await service.get_por_tipo(filters)


@router.get("/por-categoria", response_model=list[GroupCount])
async def get_por_categoria(
    filters: GlobalFilters = Depends(parse_global_filters),
    limit: int = Query(500, ge=1, le=1000),
    session: AsyncSession = Depends(get_session),
) -> list[GroupCount]:
    """Ranking por categoria."""
    service = PendenciasService(session)
    return await service.get_por_categoria(filters, limit)


@router.get("/por-chefia", response_model=list[GroupCount])
async def get_por_chefia(
    filters: GlobalFilters = Depends(parse_global_filters),
    limit: int = Query(500, ge=1, le=1000),
    session: AsyncSession = Depends(get_session),
) -> list[GroupCount]:
    """Ranking por chefia."""
    service = PendenciasService(session)
    return await service.get_por_chefia(filters, limit)


@router.get("/lista", response_model=PaginatedResponse)
async def list_pendencias(
    filters: GlobalFilters = Depends(parse_global_filters),
    pagination: PaginationParams = Depends(parse_pagination),
    session: AsyncSession = Depends(get_session),
) -> PaginatedResponse:
    """Lista paginada de pendências."""
    service = PendenciasService(session)
    return await service.list_pendencias(filters, pagination)
