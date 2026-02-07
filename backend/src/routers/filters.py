"""Router para opções de filtros globais."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_session
from src.domain.schemas import FilterOptions
from src.services.filter_options_service import FilterOptionsService

router = APIRouter(prefix="/api/filters", tags=["Filtros"])


@router.get("/options", response_model=FilterOptions)
async def get_filter_options(
    session: AsyncSession = Depends(get_session),
) -> FilterOptions:
    """Retorna opções disponíveis para popular os dropdowns de filtro."""
    service = FilterOptionsService(session)
    return await service.get_options()


@router.get("/assessores", response_model=list[str])
async def get_assessores(
    session: AsyncSession = Depends(get_session),
) -> list[str]:
    """Retorna nomes de assessores (usuários que não são procuradores)."""
    service = FilterOptionsService(session)
    return await service.get_assessores()
