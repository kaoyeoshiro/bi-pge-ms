"""Router para opções de filtros globais."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_session
from src.domain.schemas import AssuntoNode, FilterOptions
from src.services.admin_service import UserRoleService
from src.services.cache import cached
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


@router.get("/carga-reduzida", response_model=list[str])
async def get_carga_reduzida(
    session: AsyncSession = Depends(get_session),
) -> list[str]:
    """Retorna nomes de usuários com carga reduzida ativa."""
    service = UserRoleService(session)
    return await service.get_carga_reduzida_names()


@router.get("/assuntos", response_model=list[AssuntoNode])
async def get_assuntos_tree(
    session: AsyncSession = Depends(get_session),
) -> list[AssuntoNode]:
    """Retorna árvore hierárquica de assuntos vinculados a processos."""
    service = FilterOptionsService(session)
    return await service.get_assuntos_tree()
