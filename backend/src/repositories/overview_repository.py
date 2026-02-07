"""Repositório para queries cross-table do dashboard Overview."""

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.filters import GlobalFilters
from src.domain.models import PecaElaborada, PecaFinalizada, Pendencia, ProcessoNovo
from src.domain.schemas import KPIValue, TimelinePoint, TimelineSeries


class OverviewRepository:
    """Consultas agregadas cruzando as 4 tabelas do sistema."""

    def __init__(self, session: AsyncSession):
        self.session = session

    def _date_filter_sql(self, filters: GlobalFilters, date_col: str) -> str:
        """Gera cláusula WHERE SQL para filtros de data."""
        clauses = []
        if filters.ano:
            clauses.append(f"EXTRACT(YEAR FROM {date_col}) = {filters.ano}")
        if filters.mes:
            clauses.append(f"EXTRACT(MONTH FROM {date_col}) = {filters.mes}")
        if filters.data_inicio:
            clauses.append(f"{date_col} >= '{filters.data_inicio}'")
        if filters.data_fim:
            clauses.append(f"{date_col} <= '{filters.data_fim}'")
        if filters.chefia:
            chefias = ",".join(f"'{c}'" for c in filters.chefia)
            clauses.append(f"chefia IN ({chefias})")
        if filters.procurador:
            procs = ",".join(f"'{p}'" for p in filters.procurador)
            clauses.append(f"procurador IN ({procs})")
        return " AND ".join(clauses) if clauses else "1=1"

    async def _count_filtered(
        self, model: type, filters: GlobalFilters
    ) -> int:
        """Conta registros de um modelo com filtros aplicados."""
        date_col_name = (
            "data_finalizacao" if model.__tablename__ == "pecas_finalizadas" else "data"
        )
        date_col = getattr(model, date_col_name)

        stmt = select(func.count()).select_from(model)

        if filters.ano:
            stmt = stmt.where(func.extract("year", date_col) == filters.ano)
        if filters.mes:
            stmt = stmt.where(func.extract("month", date_col) == filters.mes)
        if filters.data_inicio:
            stmt = stmt.where(date_col >= str(filters.data_inicio))
        if filters.data_fim:
            stmt = stmt.where(date_col <= str(filters.data_fim))
        if filters.chefia:
            stmt = stmt.where(model.chefia.in_(filters.chefia))
        if filters.procurador:
            stmt = stmt.where(model.procurador.in_(filters.procurador))

        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def get_kpis(self, filters: GlobalFilters) -> list[KPIValue]:
        """Retorna os 4 KPIs principais do Overview."""
        count_pn = await self._count_filtered(ProcessoNovo, filters)
        count_pe = await self._count_filtered(PecaElaborada, filters)
        count_pf = await self._count_filtered(PecaFinalizada, filters)
        count_pd = await self._count_filtered(Pendencia, filters)

        return [
            KPIValue(label="Processos Novos", valor=count_pn),
            KPIValue(label="Peças Elaboradas", valor=count_pe),
            KPIValue(label="Peças Finalizadas", valor=count_pf),
            KPIValue(label="Pendências", valor=count_pd),
        ]

    async def get_timeline(
        self, filters: GlobalFilters
    ) -> list[TimelineSeries]:
        """Retorna séries temporais mensais das 4 métricas."""
        tables_config = [
            ("Processos Novos", "processos_novos", "data"),
            ("Peças Elaboradas", "pecas_elaboradas", "data"),
            ("Peças Finalizadas", "pecas_finalizadas", "data_finalizacao"),
            ("Pendências", "pendencias", "data"),
        ]

        series = []
        for label, table, date_col in tables_config:
            where_clause = self._date_filter_sql(filters, date_col)
            query = text(f"""
                SELECT TO_CHAR({date_col}, 'YYYY-MM') AS periodo,
                       COUNT(*) AS total
                FROM {table}
                WHERE {date_col} IS NOT NULL AND {where_clause}
                GROUP BY TO_CHAR({date_col}, 'YYYY-MM')
                ORDER BY periodo
            """)
            result = await self.session.execute(query)
            points = [
                TimelinePoint(periodo=row.periodo, valor=row.total)
                for row in result.all()
            ]
            series.append(TimelineSeries(nome=label, dados=points))

        return series
