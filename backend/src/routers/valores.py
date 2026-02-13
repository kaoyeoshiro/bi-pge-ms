"""Router de análise de valores da causa."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_session
from src.dependencies import parse_global_filters, parse_pagination
from src.domain.filters import GlobalFilters, PaginationParams
from src.domain.schemas import (
    KPIValue,
    PaginatedResponse,
    TimelineSeries,
    ValorFaixaItem,
    ValorGroupItem,
)
from src.services.valores_service import ValoresService

router = APIRouter(prefix="/api/valores", tags=["Valores"])


@router.get("/kpis", response_model=list[KPIValue])
async def get_kpis(
    filters: GlobalFilters = Depends(parse_global_filters),
    session: AsyncSession = Depends(get_session),
) -> list[KPIValue]:
    """KPIs de valor da causa."""
    service = ValoresService(session)
    return await service.get_kpis(filters)


@router.get("/distribuicao", response_model=list[ValorFaixaItem])
async def get_distribuicao(
    filters: GlobalFilters = Depends(parse_global_filters),
    session: AsyncSession = Depends(get_session),
) -> list[ValorFaixaItem]:
    """Distribuição de processos por faixa de valor."""
    service = ValoresService(session)
    return await service.get_distribuicao(filters)


@router.get("/por-grupo", response_model=list[ValorGroupItem])
async def get_por_grupo(
    grupo: str = Query("chefia", pattern=r"^(chefia|procurador|assunto)$"),
    metrica: str = Query("total", pattern=r"^(total|medio)$"),
    limit: int = Query(15, ge=1, le=100),
    filters: GlobalFilters = Depends(parse_global_filters),
    session: AsyncSession = Depends(get_session),
) -> list[ValorGroupItem]:
    """Ranking por dimensão (chefia, procurador, assunto)."""
    service = ValoresService(session)
    return await service.get_por_grupo(filters, grupo, metrica, limit)


@router.get("/timeline", response_model=list[TimelineSeries])
async def get_timeline(
    filters: GlobalFilters = Depends(parse_global_filters),
    session: AsyncSession = Depends(get_session),
) -> list[TimelineSeries]:
    """Evolução temporal do valor das causas."""
    service = ValoresService(session)
    return await service.get_timeline(filters)


@router.get("/lista", response_model=PaginatedResponse)
async def list_processos(
    filters: GlobalFilters = Depends(parse_global_filters),
    pagination: PaginationParams = Depends(parse_pagination),
    session: AsyncSession = Depends(get_session),
) -> PaginatedResponse:
    """Lista paginada de processos com valor da causa."""
    if pagination.sort_by is None:
        pagination.sort_by = "valor_acao"
    service = ValoresService(session)
    return await service.list_processos(filters, pagination)
