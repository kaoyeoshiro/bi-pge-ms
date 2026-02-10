"""Router para exploração interativa da árvore de assuntos."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_session
from src.dependencies import parse_global_filters, parse_pagination
from src.domain.filters import GlobalFilters, PaginationParams
from src.domain.schemas import AssuntoGroupCount, AssuntoNode, AssuntoResumoResponse, PaginatedResponse
from src.services.assunto_explorer_service import AssuntoExplorerService

router = APIRouter(prefix="/api/assuntos", tags=["Assuntos"])


@router.get("/drill-down", response_model=list[AssuntoGroupCount])
async def drill_down(
    assunto_pai: int | None = Query(None, description="Código do assunto pai (None = raízes)"),
    limit: int = Query(50, ge=1, le=200, description="Limite de resultados"),
    filters: GlobalFilters = Depends(parse_global_filters),
    session: AsyncSession = Depends(get_session),
) -> list[AssuntoGroupCount]:
    """Drill-down hierárquico: retorna filhos diretos com totais acumulados."""
    service = AssuntoExplorerService(session)
    return await service.drill_down(assunto_pai, filters, limit)


@router.get("/resumo", response_model=AssuntoResumoResponse)
async def get_resumo(
    codigo: int = Query(..., description="Código do assunto"),
    filters: GlobalFilters = Depends(parse_global_filters),
    session: AsyncSession = Depends(get_session),
) -> AssuntoResumoResponse:
    """Resumo completo de um nó: KPIs cross-table, top chefias e timeline."""
    service = AssuntoExplorerService(session)
    return await service.get_resumo(codigo, filters)


@router.get("/lista", response_model=PaginatedResponse)
async def list_processos_by_assunto(
    filters: GlobalFilters = Depends(parse_global_filters),
    pagination: PaginationParams = Depends(parse_pagination),
    session: AsyncSession = Depends(get_session),
) -> PaginatedResponse:
    """Lista paginada de processos filtrados por assunto (com descendentes)."""
    service = AssuntoExplorerService(session)
    return await service.list_processos(filters, pagination)


@router.get("/search", response_model=list[AssuntoNode])
async def search_assuntos(
    q: str = Query(..., min_length=2, description="Termo de busca (mínimo 2 caracteres)"),
    limit: int = Query(20, ge=1, le=50, description="Limite de resultados"),
    session: AsyncSession = Depends(get_session),
) -> list[AssuntoNode]:
    """Busca textual de assuntos por nome (case-insensitive, sem acentos)."""
    service = AssuntoExplorerService(session)
    return await service.search_assuntos(q, limit)


@router.get("/path/{codigo}", response_model=list[AssuntoNode])
async def get_assunto_path(
    codigo: int,
    session: AsyncSession = Depends(get_session),
) -> list[AssuntoNode]:
    """Retorna o caminho hierárquico completo até o assunto (da raiz até ele)."""
    service = AssuntoExplorerService(session)
    return await service.get_assunto_path(codigo)
