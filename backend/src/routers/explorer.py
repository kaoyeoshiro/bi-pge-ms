"""Router do Data Explorer genérico."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_session
from src.dependencies import parse_global_filters, parse_pagination
from src.domain.enums import TableName
from src.domain.filters import GlobalFilters, PaginationParams
from src.domain.schemas import PaginatedResponse, TableSchema
from src.services.explorer_service import ExplorerService

router = APIRouter(prefix="/api/explorer", tags=["Explorer"])


@router.get("/{table}/schema", response_model=TableSchema)
async def get_schema(
    table: TableName,
    session: AsyncSession = Depends(get_session),
) -> TableSchema:
    """Retorna o schema de uma tabela."""
    service = ExplorerService(session)
    return await service.get_schema(table)


@router.get("/{table}/data", response_model=PaginatedResponse)
async def get_data(
    table: TableName,
    filters: GlobalFilters = Depends(parse_global_filters),
    pagination: PaginationParams = Depends(parse_pagination),
    session: AsyncSession = Depends(get_session),
) -> PaginatedResponse:
    """Retorna dados paginados de uma tabela."""
    service = ExplorerService(session)
    return await service.get_data(table, filters, pagination)


@router.get("/{table}/distinct/{column}")
async def get_distinct(
    table: TableName,
    column: str,
    limit: int = Query(500, ge=1, le=1000),
    session: AsyncSession = Depends(get_session),
) -> list[str]:
    """Retorna valores distintos de uma coluna."""
    service = ExplorerService(session)
    return await service.get_distinct(table, column, limit)
