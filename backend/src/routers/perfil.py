"""Router para análise individualizada de procurador ou chefia."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_session
from src.dependencies import parse_global_filters, parse_pagination
from src.domain.filters import GlobalFilters, PaginationParams
from src.domain.schemas import (
    ChefiaMediasResponse,
    GroupCount,
    KPIValue,
    PaginatedResponse,
    ProcuradorComparativo,
    TimelineSeries,
)
from src.services.perfil_service import PerfilService

router = APIRouter(prefix="/api/perfil", tags=["Perfil Individual"])

DIMENSAO_PATTERN = r"^(procurador|chefia|assessor)$"
TABELA_PATTERN = r"^(processos_novos|pecas_elaboradas|pecas_finalizadas|pendencias)$"


@router.get("/kpis", response_model=list[KPIValue])
async def get_kpis(
    dimensao: str = Query(..., pattern=DIMENSAO_PATTERN),
    valor: str = Query(..., min_length=1),
    filters: GlobalFilters = Depends(parse_global_filters),
    session: AsyncSession = Depends(get_session),
) -> list[KPIValue]:
    """KPIs do indivíduo: totais nas 4 tabelas."""
    service = PerfilService(session)
    return await service.get_kpis(dimensao, valor, filters)


@router.get("/timeline", response_model=list[TimelineSeries])
async def get_timeline(
    dimensao: str = Query(..., pattern=DIMENSAO_PATTERN),
    valor: str = Query(..., min_length=1),
    filters: GlobalFilters = Depends(parse_global_filters),
    session: AsyncSession = Depends(get_session),
) -> list[TimelineSeries]:
    """Séries temporais mensais do indivíduo."""
    service = PerfilService(session)
    return await service.get_timeline(dimensao, valor, filters)


@router.get("/por-categoria", response_model=list[GroupCount])
async def get_por_categoria(
    dimensao: str = Query(..., pattern=DIMENSAO_PATTERN),
    valor: str = Query(..., min_length=1),
    tabela: str = Query("pecas_elaboradas", pattern=TABELA_PATTERN),
    limit: int = Query(15, ge=1, le=50),
    filters: GlobalFilters = Depends(parse_global_filters),
    session: AsyncSession = Depends(get_session),
) -> list[GroupCount]:
    """Ranking por categoria de peça do indivíduo."""
    service = PerfilService(session)
    return await service.get_por_categoria(dimensao, valor, filters, tabela, limit)


@router.get("/por-modelo", response_model=list[GroupCount])
async def get_por_modelo(
    dimensao: str = Query(..., pattern=DIMENSAO_PATTERN),
    valor: str = Query(..., min_length=1),
    tabela: str = Query("pecas_elaboradas", pattern=TABELA_PATTERN),
    limit: int = Query(15, ge=1, le=50),
    filters: GlobalFilters = Depends(parse_global_filters),
    session: AsyncSession = Depends(get_session),
) -> list[GroupCount]:
    """Ranking por modelo de peça do indivíduo."""
    service = PerfilService(session)
    return await service.get_por_modelo(dimensao, valor, filters, tabela, limit)


@router.get("/por-procurador", response_model=list[GroupCount])
async def get_por_procurador(
    dimensao: str = Query(..., pattern=DIMENSAO_PATTERN),
    valor: str = Query(..., min_length=1),
    tabela: str = Query("pecas_elaboradas", pattern=TABELA_PATTERN),
    limit: int = Query(15, ge=1, le=50),
    filters: GlobalFilters = Depends(parse_global_filters),
    session: AsyncSession = Depends(get_session),
) -> list[GroupCount]:
    """Ranking por procurador: quais procuradores o assessor atendeu."""
    service = PerfilService(session)
    return await service.get_por_procurador(dimensao, valor, filters, tabela, limit)


@router.get("/comparativo-procuradores", response_model=list[ProcuradorComparativo])
async def get_comparativo_procuradores(
    valor: str = Query(..., min_length=1),
    filters: GlobalFilters = Depends(parse_global_filters),
    session: AsyncSession = Depends(get_session),
) -> list[ProcuradorComparativo]:
    """Comparativo entre procuradores de uma chefia em todas as tabelas."""
    service = PerfilService(session)
    return await service.get_comparativo_procuradores(valor, filters)


@router.get("/chefia-medias", response_model=ChefiaMediasResponse)
async def get_chefia_medias(
    valor: str = Query(..., min_length=1),
    average_unit: str = Query("month", pattern=r"^(day|month|year)$"),
    procurador_nomes: list[str] = Query(default=[]),
    filters: GlobalFilters = Depends(parse_global_filters),
    session: AsyncSession = Depends(get_session),
) -> ChefiaMediasResponse:
    """KPIs com média por unidade temporal para uma chefia."""
    service = PerfilService(session)
    return await service.get_chefia_medias(
        chefia=valor,
        filters=filters,
        average_unit=average_unit,
        procurador_nomes=procurador_nomes if procurador_nomes else None,
    )


@router.get("/lista", response_model=PaginatedResponse)
async def get_lista(
    dimensao: str = Query(..., pattern=DIMENSAO_PATTERN),
    valor: str = Query(..., min_length=1),
    tabela: str = Query("pecas_elaboradas", pattern=TABELA_PATTERN),
    filters: GlobalFilters = Depends(parse_global_filters),
    pagination: PaginationParams = Depends(parse_pagination),
    session: AsyncSession = Depends(get_session),
) -> PaginatedResponse:
    """Lista paginada de registros do indivíduo."""
    service = PerfilService(session)
    return await service.get_lista(dimensao, valor, filters, tabela, pagination)
