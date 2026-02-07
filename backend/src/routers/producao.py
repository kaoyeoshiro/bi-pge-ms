"""Router de produção (peças elaboradas e finalizadas)."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_session
from src.dependencies import parse_global_filters, parse_pagination
from src.domain.filters import GlobalFilters, PaginationParams
from src.domain.schemas import (
    GroupCount,
    KPIValue,
    PaginatedResponse,
    TimelineSeries,
)
from src.services.producao_service import ProducaoService

router = APIRouter(prefix="/api/producao", tags=["Produção"])


@router.get("/kpis", response_model=list[KPIValue])
async def get_kpis(
    filters: GlobalFilters = Depends(parse_global_filters),
    session: AsyncSession = Depends(get_session),
) -> list[KPIValue]:
    """KPIs de produção."""
    service = ProducaoService(session)
    return await service.get_kpis(filters)


@router.get("/timeline", response_model=list[TimelineSeries])
async def get_timeline(
    filters: GlobalFilters = Depends(parse_global_filters),
    session: AsyncSession = Depends(get_session),
) -> list[TimelineSeries]:
    """Séries temporais de elaboradas e finalizadas."""
    service = ProducaoService(session)
    return await service.get_timeline(filters)


@router.get("/por-categoria", response_model=list[GroupCount])
async def get_por_categoria(
    filters: GlobalFilters = Depends(parse_global_filters),
    limit: int = Query(500, ge=1, le=1000),
    tipo: str = Query("elaboradas", pattern=r"^(elaboradas|finalizadas)$"),
    session: AsyncSession = Depends(get_session),
) -> list[GroupCount]:
    """Ranking por categoria (elaboradas ou finalizadas)."""
    service = ProducaoService(session)
    return await service.get_por_categoria(filters, limit, tipo)


@router.get("/por-chefia", response_model=list[GroupCount])
async def get_por_chefia(
    filters: GlobalFilters = Depends(parse_global_filters),
    limit: int = Query(500, ge=1, le=1000),
    tipo: str = Query("elaboradas", pattern=r"^(elaboradas|finalizadas)$"),
    session: AsyncSession = Depends(get_session),
) -> list[GroupCount]:
    """Ranking por chefia (elaboradas ou finalizadas)."""
    service = ProducaoService(session)
    return await service.get_por_chefia(filters, limit, tipo)


@router.get("/por-procurador", response_model=list[GroupCount])
async def get_por_procurador(
    filters: GlobalFilters = Depends(parse_global_filters),
    limit: int = Query(500, ge=1, le=1000),
    tipo: str = Query("elaboradas", pattern=r"^(elaboradas|finalizadas)$"),
    session: AsyncSession = Depends(get_session),
) -> list[GroupCount]:
    """Ranking por procurador (elaboradas ou finalizadas)."""
    service = ProducaoService(session)
    return await service.get_por_procurador(filters, limit, tipo)


@router.get("/por-usuario", response_model=list[GroupCount])
async def get_por_usuario(
    filters: GlobalFilters = Depends(parse_global_filters),
    limit: int = Query(500, ge=1, le=1000),
    tipo: str = Query("elaboradas", pattern=r"^(elaboradas|finalizadas)$"),
    session: AsyncSession = Depends(get_session),
) -> list[GroupCount]:
    """Ranking por usuário criador/finalizador (elaboradas ou finalizadas)."""
    service = ProducaoService(session)
    return await service.get_por_usuario(filters, limit, tipo)


@router.get("/elaboradas", response_model=PaginatedResponse)
async def list_elaboradas(
    filters: GlobalFilters = Depends(parse_global_filters),
    pagination: PaginationParams = Depends(parse_pagination),
    session: AsyncSession = Depends(get_session),
) -> PaginatedResponse:
    """Lista paginada de peças elaboradas."""
    service = ProducaoService(session)
    return await service.list_elaboradas(filters, pagination)


@router.get("/finalizadas", response_model=PaginatedResponse)
async def list_finalizadas(
    filters: GlobalFilters = Depends(parse_global_filters),
    pagination: PaginationParams = Depends(parse_pagination),
    session: AsyncSession = Depends(get_session),
) -> PaginatedResponse:
    """Lista paginada de peças finalizadas."""
    service = ProducaoService(session)
    return await service.list_finalizadas(filters, pagination)
