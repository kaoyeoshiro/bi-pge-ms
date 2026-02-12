"""Router de partes/demandantes normalizados."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_session
from src.domain.schemas import (
    PaginatedResponse,
    ParteNormalizadaResponse,
    PartesKPIsResponse,
    PartesRankingResponse,
)
from src.services.partes_service import PartesService

router = APIRouter(prefix="/api/partes", tags=["Partes"])


@router.get("/kpis", response_model=PartesKPIsResponse)
async def get_kpis(
    session: AsyncSession = Depends(get_session),
) -> PartesKPIsResponse:
    """Retorna KPIs gerais de partes/demandantes."""
    service = PartesService(session)
    return await service.get_kpis()


@router.get("/ranking", response_model=PartesRankingResponse)
async def get_ranking(
    role: str | None = Query(
        None,
        description="Papel: demandante, executado, advogado, coreu",
        pattern="^(demandante|executado|advogado|coreu)$",
    ),
    search: str | None = Query(None, description="Busca por nome, CPF, CNPJ ou OAB"),
    sort_by: str = Query("qtd_processos", description="Coluna de ordenação"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
) -> PartesRankingResponse:
    """Retorna ranking paginado de partes normalizadas."""
    service = PartesService(session)
    return await service.get_ranking(
        role=role,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
    )


@router.get("/{parte_id}", response_model=ParteNormalizadaResponse)
async def get_parte(
    parte_id: int,
    session: AsyncSession = Depends(get_session),
) -> ParteNormalizadaResponse:
    """Retorna detalhes de uma parte normalizada."""
    service = PartesService(session)
    result = await service.get_by_id(parte_id)
    if not result:
        raise HTTPException(status_code=404, detail="Parte não encontrada.")
    return result


@router.get("/{parte_id}/processos", response_model=PaginatedResponse)
async def get_processos_da_parte(
    parte_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
) -> PaginatedResponse:
    """Retorna processos vinculados a uma parte normalizada."""
    service = PartesService(session)
    data = await service.get_processos(
        parte_id=parte_id,
        page=page,
        page_size=page_size,
    )
    return PaginatedResponse(**data)
