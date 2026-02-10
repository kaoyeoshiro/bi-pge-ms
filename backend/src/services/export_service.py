"""Serviço de exportação CSV e Excel com streaming."""

import csv
import io
from datetime import datetime
from typing import AsyncIterator

from openpyxl import Workbook
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.enums import TableName
from src.domain.filters import GlobalFilters
from src.domain.models import TABLE_MODEL_MAP
from src.repositories.base_repository import BaseRepository
from src.services.explorer_service import COLUMN_LABELS


class ExportService:
    """Gera arquivos CSV e Excel para download com streaming."""

    # Limite por arquivo para dividir exports grandes
    MAX_ROWS_PER_FILE = 100_000

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_total_rows(
        self, table: TableName, filters: GlobalFilters
    ) -> int:
        """Retorna total de linhas que serão exportadas."""
        model = TABLE_MODEL_MAP[table.value]
        repo = BaseRepository(self.session, model)

        stmt = select(func.count()).select_from(model)
        stmt = repo._apply_global_filters(stmt, filters)

        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def stream_csv_chunks(
        self, table: TableName, filters: GlobalFilters
    ) -> AsyncIterator[str]:
        """
        Gera CSV em chunks via streaming.
        Yield linha por linha para evitar carregar tudo na memória.
        """
        model = TABLE_MODEL_MAP[table.value]
        repo = BaseRepository(self.session, model)

        # Monta query base
        stmt = select(model)
        stmt = repo._apply_global_filters(stmt, filters)
        stmt = stmt.execution_options(yield_per=1000)  # Fetch em batches de 1000

        columns = [col.name for col in model.__table__.columns]
        headers = [COLUMN_LABELS.get(c, c) for c in columns]

        # Yield header
        output = io.StringIO()
        writer = csv.writer(output, delimiter=";")
        writer.writerow(headers)
        yield output.getvalue()

        # Stream rows em chunks
        result = await self.session.stream(stmt)
        row_count = 0

        async for row in result.scalars():
            output = io.StringIO()
            writer = csv.writer(output, delimiter=";")

            values = []
            for col_name in columns:
                val = getattr(row, col_name)
                if isinstance(val, datetime):
                    val = val.strftime("%d/%m/%Y %H:%M")
                values.append(val if val is not None else "")
            writer.writerow(values)

            yield output.getvalue()
            row_count += 1

            # Limite de segurança (previne exports infinitos)
            if row_count >= 500_000:
                break

    async def export_csv(
        self, table: TableName, filters: GlobalFilters
    ) -> str:
        """
        [DEPRECATED] Gera conteúdo CSV com filtros aplicados.
        Mantido para compatibilidade. Use stream_csv_chunks() para exports grandes.
        """
        model = TABLE_MODEL_MAP[table.value]
        repo = BaseRepository(self.session, model)

        stmt = select(model)
        stmt = repo._apply_global_filters(stmt, filters)
        stmt = stmt.limit(self.MAX_ROWS_PER_FILE)

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
        """
        Gera arquivo Excel com filtros aplicados.
        NOTA: Excel não suporta streaming real, então mantém limite para evitar
        travamento do servidor. Para exports grandes, use CSV.
        """
        model = TABLE_MODEL_MAP[table.value]
        repo = BaseRepository(self.session, model)

        stmt = select(model)
        stmt = repo._apply_global_filters(stmt, filters)
        # Excel tem limite de ~1M linhas, mas travaria muito antes.
        # Limitamos a 100k por questão de performance e memória.
        stmt = stmt.limit(self.MAX_ROWS_PER_FILE)

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
