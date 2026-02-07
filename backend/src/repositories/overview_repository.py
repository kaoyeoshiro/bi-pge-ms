"""Repositório para queries cross-table do dashboard Overview."""

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.constants import CATEGORIAS_NAO_PRODUTIVAS
from src.domain.filters import GlobalFilters
from src.domain.models import PecaFinalizada, Pendencia, ProcessoNovo
from src.domain.schemas import KPIValue, TimelinePoint, TimelineSeries


class OverviewRepository:
    """Consultas agregadas cruzando as 4 tabelas do sistema."""

    def __init__(self, session: AsyncSession):
        self.session = session

    def _date_filter_sql(
        self, filters: GlobalFilters, date_col: str, table: str = ""
    ) -> str:
        """Gera cláusula WHERE SQL para filtros de data."""
        clauses = []
        if filters.anos:
            if len(filters.anos) == 1:
                clauses.append(f"EXTRACT(YEAR FROM {date_col}) = {filters.anos[0]}")
            else:
                anos_str = ",".join(str(a) for a in filters.anos)
                clauses.append(f"EXTRACT(YEAR FROM {date_col}) IN ({anos_str})")
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

        # Excluir categorias não-produtivas de pecas_finalizadas
        if table == "pecas_finalizadas":
            cats = ",".join(f"'{c}'" for c in CATEGORIAS_NAO_PRODUTIVAS)
            clauses.append(f"categoria NOT IN ({cats})")

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

        if filters.anos:
            if len(filters.anos) == 1:
                stmt = stmt.where(func.extract("year", date_col) == filters.anos[0])
            else:
                stmt = stmt.where(func.extract("year", date_col).in_(filters.anos))
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

        # Excluir categorias não-produtivas de pecas_finalizadas
        if model is PecaFinalizada:
            stmt = stmt.where(
                PecaFinalizada.categoria.notin_(CATEGORIAS_NAO_PRODUTIVAS)
            )

        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def get_kpis(self, filters: GlobalFilters) -> list[KPIValue]:
        """Retorna os 3 KPIs principais do Overview (métricas de procurador).

        Peças elaboradas é métrica de assessor e aparece apenas em /perfil-assessor.
        """
        count_pn = await self._count_filtered(ProcessoNovo, filters)
        count_pf = await self._count_filtered(PecaFinalizada, filters)
        count_pd = await self._count_filtered(Pendencia, filters)

        return [
            KPIValue(label="Processos Novos", valor=count_pn),
            KPIValue(label="Peças Finalizadas", valor=count_pf),
            KPIValue(label="Pendências", valor=count_pd),
        ]

    async def get_timeline(
        self, filters: GlobalFilters
    ) -> list[TimelineSeries]:
        """Retorna séries temporais mensais das 4 métricas."""
        tables_config = [
            ("Processos Novos", "processos_novos", "data"),
            ("Peças Finalizadas", "pecas_finalizadas", "data_finalizacao"),
            ("Pendências", "pendencias", "data"),
        ]

        series = []
        for label, table, date_col in tables_config:
            where_clause = self._date_filter_sql(filters, date_col, table)
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
