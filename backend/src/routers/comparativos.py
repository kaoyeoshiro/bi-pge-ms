"""Router de comparativos."""

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_session
from src.dependencies import parse_global_filters
from src.domain.filters import GlobalFilters
from src.services.comparativo_service import ComparativoService

router = APIRouter(prefix="/api/comparativos", tags=["Comparativos"])


@router.get("/chefias")
async def comparar_chefias(
    chefias: list[str] = Query(..., description="Chefias para comparar"),
    filters: GlobalFilters = Depends(parse_global_filters),
    session: AsyncSession = Depends(get_session),
):
    """Compara KPIs entre N chefias."""
    service = ComparativoService(session)
    return await service.comparar_chefias(chefias, filters)


@router.get("/procuradores")
async def comparar_procuradores(
    procuradores: list[str] = Query(..., description="Procuradores para comparar"),
    filters: GlobalFilters = Depends(parse_global_filters),
    session: AsyncSession = Depends(get_session),
):
    """Compara KPIs entre N procuradores."""
    service = ComparativoService(session)
    return await service.comparar_procuradores(procuradores, filters)


@router.get("/periodos")
async def comparar_periodos(
    p1_inicio: date = Query(..., description="Início do período 1"),
    p1_fim: date = Query(..., description="Fim do período 1"),
    p2_inicio: date = Query(..., description="Início do período 2"),
    p2_fim: date = Query(..., description="Fim do período 2"),
    filters: GlobalFilters = Depends(parse_global_filters),
    session: AsyncSession = Depends(get_session),
):
    """Compara KPIs entre 2 períodos."""
    service = ComparativoService(session)
    return await service.comparar_periodos(
        p1_inicio, p1_fim, p2_inicio, p2_fim, filters
    )
