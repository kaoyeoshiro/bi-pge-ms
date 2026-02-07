"""Serviço de exportação CSV e Excel com streaming."""

import csv
import io
from datetime import datetime

from openpyxl import Workbook
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.enums import TableName
from src.domain.filters import GlobalFilters
from src.domain.models import TABLE_MODEL_MAP
from src.repositories.base_repository import BaseRepository
from src.services.explorer_service import COLUMN_LABELS


class ExportService:
    """Gera arquivos CSV e Excel para download."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def export_csv(
        self, table: TableName, filters: GlobalFilters
    ) -> str:
        """Gera conteúdo CSV com filtros aplicados."""
        model = TABLE_MODEL_MAP[table.value]
        repo = BaseRepository(self.session, model)

        stmt = select(model)
        stmt = repo._apply_global_filters(stmt, filters)
        stmt = stmt.limit(50000)  # Limite de segurança

        result = await self.session.execute(stmt)
        rows = result.scalars().all()

        output = io.StringIO()
        columns = [col.name for col in model.__table__.columns]
        headers = [COLUMN_LABELS.get(c, c) for c in columns]

        writer = csv.writer(output, delimiter=";")
        writer.writerow(headers)

        for row in rows:
            values = []
            for col_name in columns:
                val = getattr(row, col_name)
                if isinstance(val, datetime):
                    val = val.strftime("%d/%m/%Y %H:%M")
                values.append(val if val is not None else "")
            writer.writerow(values)

        return output.getvalue()

    async def export_excel(
        self, table: TableName, filters: GlobalFilters
    ) -> bytes:
        """Gera arquivo Excel com filtros aplicados."""
        model = TABLE_MODEL_MAP[table.value]
        repo = BaseRepository(self.session, model)

        stmt = select(model)
        stmt = repo._apply_global_filters(stmt, filters)
        stmt = stmt.limit(50000)

        result = await self.session.execute(stmt)
        rows = result.scalars().all()

        wb = Workbook()
        ws = wb.active
        ws.title = table.value

        columns = [col.name for col in model.__table__.columns]
        headers = [COLUMN_LABELS.get(c, c) for c in columns]
        ws.append(headers)

        for row in rows:
            values = []
            for col_name in columns:
                val = getattr(row, col_name)
                if isinstance(val, datetime):
                    val = val.strftime("%d/%m/%Y %H:%M")
                values.append(val if val is not None else "")
            ws.append(values)

        output = io.BytesIO()
        wb.save(output)
        return output.getvalue()
