"""Router de exportação CSV e Excel."""

from fastapi import APIRouter, Depends
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_session
from src.dependencies import parse_global_filters
from src.domain.enums import TableName
from src.domain.filters import GlobalFilters
from src.services.export_service import ExportService

router = APIRouter(prefix="/api/export", tags=["Exportação"])


@router.get("/{table}/csv")
async def export_csv(
    table: TableName,
    filters: GlobalFilters = Depends(parse_global_filters),
    session: AsyncSession = Depends(get_session),
):
    """Exporta dados filtrados em CSV."""
    service = ExportService(session)
    content = await service.export_csv(table, filters)

    return Response(
        content=content.encode("utf-8-sig"),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{table.value}.csv"'
        },
    )


@router.get("/{table}/excel")
async def export_excel(
    table: TableName,
    filters: GlobalFilters = Depends(parse_global_filters),
    session: AsyncSession = Depends(get_session),
):
    """Exporta dados filtrados em Excel."""
    service = ExportService(session)
    content = await service.export_excel(table, filters)

    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{table.value}.xlsx"'
        },
    )
