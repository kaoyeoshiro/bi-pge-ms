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


@router.get("/{table}/info")
async def export_info(
    table: TableName,
    filters: GlobalFilters = Depends(parse_global_filters),
    session: AsyncSession = Depends(get_session),
):
    """
    Retorna informações sobre a exportação (total de linhas, tamanho estimado, etc).
    Use antes de iniciar o download para avisar o usuário sobre exports grandes.
    """
    service = ExportService(session)
    total_rows = await service.get_total_rows(table, filters)

    max_per_file = ExportService.MAX_ROWS_PER_FILE
    will_be_limited = total_rows > max_per_file

    return {
        "total_rows": total_rows,
        "max_rows_per_file": max_per_file,
        "will_be_limited": will_be_limited,
        "exported_rows": min(total_rows, max_per_file),
        "warning": (
            f"Este export contém {total_rows:,} linhas. "
            f"Serão exportadas as primeiras {max_per_file:,} linhas. "
            "Considere aplicar mais filtros para reduzir o volume."
        ) if will_be_limited else None
    }


@router.get("/{table}/csv")
async def export_csv(
    table: TableName,
    filters: GlobalFilters = Depends(parse_global_filters),
    session: AsyncSession = Depends(get_session),
):
    """
    Exporta dados filtrados em CSV com streaming.
    Para exports grandes (>100k linhas), use este endpoint.
    Os dados são enviados em chunks para evitar timeout e uso excessivo de memória.
    """
    service = ExportService(session)

    # Streaming response com chunks
    async def generate():
        async for chunk in service.stream_csv_chunks(table, filters):
            yield chunk.encode("utf-8-sig")

    return StreamingResponse(
        generate(),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{table.value}.csv"',
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get("/{table}/excel")
async def export_excel(
    table: TableName,
    filters: GlobalFilters = Depends(parse_global_filters),
    session: AsyncSession = Depends(get_session),
):
    """
    Exporta dados filtrados em Excel.
    ATENÇÃO: Excel tem limite de 100.000 linhas por questão de performance.
    Para exports maiores, use CSV que suporta streaming e volumes ilimitados.
    """
    service = ExportService(session)
    content = await service.export_excel(table, filters)

    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{table.value}.xlsx"',
            "X-Content-Type-Options": "nosniff",
        },
    )
