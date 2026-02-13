"""Repositório para queries cross-table do dashboard Overview."""

from sqlalchemy import DateTime, Integer, case, cast, func, literal, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.constants import CATEGORIAS_NAO_PRODUTIVAS
from src.domain.filters import GlobalFilters
from src.domain.models import (
    HiddenProcuradorProducao,
    PecaFinalizada,
    Pendencia,
    ProcessoAssunto,
    ProcessoNovo,
)
from src.domain.schemas import KPIValue, TimelinePoint, TimelineSeries
from src.services.normalization import (
    normalize_chefia_expr,
    normalize_chefia_sql,
    normalize_procurador_expr,
)

# Coluna resolvida para ocultação por tabela (mesma lógica do PROCURADOR_COL_MAP)
_HIDDEN_RESOLVED_COL: dict[str, str] = {
    "processos_novos": "procurador",
    "pecas_finalizadas": "usuario_finalizacao",
    "pendencias": "procurador",
}

# Tabelas que participam da ocultação
_HIDDEN_TABLES = {"processos_novos", "pecas_finalizadas", "pendencias"}


class OverviewRepository:
    """Consultas agregadas cruzando as 4 tabelas do sistema."""

    def __init__(self, session: AsyncSession):
        self.session = session

    def _date_filter_sql(
        self, filters: GlobalFilters, date_col: str, table: str = ""
    ) -> str:
        """Gera cláusula WHERE SQL para filtros de data."""
        clauses = []

        # Para processos_novos, o ano é do número CNJ (numero_formatado)
        # Suporta NNNNNNN-DD.YYYY... e NNNNNNNNN.YYYY... via SPLIT_PART
        if table == "processos_novos":
            year_sql = (
                f"CASE WHEN numero_formatado ~ '\\.\\d{{4}}\\.' "
                f"THEN CAST(SPLIT_PART(numero_formatado, '.', 2) AS INTEGER) "
                f"ELSE EXTRACT(YEAR FROM {date_col})::INTEGER END"
            )
        else:
            year_sql = f"EXTRACT(YEAR FROM {date_col})"

        if filters.anos:
            if len(filters.anos) == 1:
                clauses.append(f"{year_sql} = {filters.anos[0]}")
            else:
                anos_str = ",".join(str(a) for a in filters.anos)
                clauses.append(f"{year_sql} IN ({anos_str})")
        if filters.mes:
            clauses.append(f"EXTRACT(MONTH FROM {date_col}) = {filters.mes}")
        if filters.data_inicio:
            clauses.append(f"{date_col} >= '{filters.data_inicio}'")
        if filters.data_fim:
            clauses.append(f"{date_col} <= '{filters.data_fim}'")
        if filters.chefia:
            chefias = ",".join(f"'{c}'" for c in filters.chefia)
            chefia_norm = normalize_chefia_sql("chefia")
            clauses.append(f"{chefia_norm} IN ({chefias})")
        if filters.procurador:
            procs = ",".join(f"'{p}'" for p in filters.procurador)
            clauses.append(f"procurador IN ({procs})")

        # Excluir categorias não-produtivas de pecas_finalizadas
        if table == "pecas_finalizadas":
            cats = ",".join(f"'{c}'" for c in CATEGORIAS_NAO_PRODUTIVAS)
            clauses.append(f"categoria NOT IN ({cats})")

        # Excluir produção oculta por regras administrativas
        if filters.exclude_hidden and table in _HIDDEN_TABLES:
            resolved_col = _HIDDEN_RESOLVED_COL.get(table, "procurador")
            proc_expr = f"TRIM(REGEXP_REPLACE({resolved_col}, '\\s*\\(.*\\)$', '', 'g'))"
            chefia_expr = normalize_chefia_sql(f"{table}.chefia")
            clauses.append(
                f"NOT EXISTS ("
                f"SELECT 1 FROM admin_hidden_procurador_producao h "
                f"WHERE h.is_active = true "
                f"AND h.procurador_name = {proc_expr} "
                f"AND (h.chefia IS NULL OR h.chefia = {chefia_expr}) "
                f"AND {date_col} >= h.start_date::timestamp "
                f"AND {date_col} < (h.end_date + INTERVAL '1 day')::timestamp"
                f")"
            )

        # Filtro por assunto: subquery em processo_assuntos (só processos_novos)
        if filters.assunto and table == "processos_novos":
            codigos = ",".join(str(c) for c in filters.assunto)
            clauses.append(
                f"numero_processo IN ("
                f"SELECT DISTINCT numero_processo FROM processo_assuntos "
                f"WHERE codigo_assunto IN ({codigos})"
                f")"
            )

        # Filtro por faixa de valor da causa
        # Sem valor_min → inclui NULLs (processos sem valor informado)
        # Com valor_min → exclui NULLs (só processos com valor no range)
        if filters.valor_min is not None or filters.valor_max is not None:
            if table == "processos_novos":
                if filters.valor_min is not None:
                    clauses.append(f"valor_acao >= {filters.valor_min}")
                if filters.valor_max is not None:
                    if filters.valor_min is None:
                        clauses.append(
                            f"(valor_acao <= {filters.valor_max} OR valor_acao IS NULL)"
                        )
                    else:
                        clauses.append(f"valor_acao <= {filters.valor_max}")
            else:
                valor_conds = []
                if filters.valor_min is not None:
                    valor_conds.append(f"valor_acao >= {filters.valor_min}")
                if filters.valor_max is not None:
                    if filters.valor_min is None:
                        valor_conds.append(
                            f"(valor_acao <= {filters.valor_max} OR valor_acao IS NULL)"
                        )
                    else:
                        valor_conds.append(f"valor_acao <= {filters.valor_max}")
                else:
                    valor_conds.append("valor_acao IS NOT NULL")
                valor_where = " AND ".join(valor_conds)
                clauses.append(
                    f"numero_processo IN ("
                    f"SELECT DISTINCT numero_processo FROM processos_novos "
                    f"WHERE {valor_where}"
                    f")"
                )

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

        # Para processos_novos, o ano é do número CNJ (numero_formatado)
        if model is ProcessoNovo:
            has_cnj_year = model.numero_formatado.op("~")(r"\.\d{4}\.")
            cnj_year = cast(
                func.split_part(model.numero_formatado, ".", 2), Integer
            )
            year_expr = case(
                (has_cnj_year, cnj_year),
                else_=cast(func.extract("year", date_col), Integer),
            )
        else:
            year_expr = func.extract("year", date_col)

        if filters.anos:
            if len(filters.anos) == 1:
                stmt = stmt.where(year_expr == filters.anos[0])
            else:
                stmt = stmt.where(year_expr.in_(filters.anos))
        if filters.mes:
            stmt = stmt.where(func.extract("month", date_col) == filters.mes)
        if filters.data_inicio:
            stmt = stmt.where(date_col >= str(filters.data_inicio))
        if filters.data_fim:
            stmt = stmt.where(date_col <= str(filters.data_fim))
        if filters.chefia:
            stmt = stmt.where(normalize_chefia_expr(model.chefia).in_(filters.chefia))
        if filters.procurador:
            stmt = stmt.where(model.procurador.in_(filters.procurador))

        # Excluir categorias não-produtivas de pecas_finalizadas
        if model is PecaFinalizada:
            stmt = stmt.where(
                PecaFinalizada.categoria.notin_(CATEGORIAS_NAO_PRODUTIVAS)
            )

        # Filtro por assunto: subquery em processo_assuntos (só processos_novos)
        if filters.assunto and model is ProcessoNovo:
            assunto_subq = (
                select(ProcessoAssunto.numero_processo)
                .where(ProcessoAssunto.codigo_assunto.in_(filters.assunto))
                .distinct()
                .scalar_subquery()
            )
            stmt = stmt.where(model.numero_processo.in_(assunto_subq))

        # Filtro por faixa de valor da causa
        if filters.valor_min is not None or filters.valor_max is not None:
            if model is ProcessoNovo:
                if filters.valor_min is not None:
                    stmt = stmt.where(ProcessoNovo.valor_acao >= filters.valor_min)
                if filters.valor_max is not None:
                    if filters.valor_min is None:
                        stmt = stmt.where(or_(
                            ProcessoNovo.valor_acao <= filters.valor_max,
                            ProcessoNovo.valor_acao.is_(None),
                        ))
                    else:
                        stmt = stmt.where(ProcessoNovo.valor_acao <= filters.valor_max)
            else:
                valor_subq = select(ProcessoNovo.numero_processo)
                if filters.valor_min is not None:
                    valor_subq = valor_subq.where(
                        ProcessoNovo.valor_acao >= filters.valor_min
                    )
                if filters.valor_max is not None:
                    if filters.valor_min is None:
                        valor_subq = valor_subq.where(or_(
                            ProcessoNovo.valor_acao <= filters.valor_max,
                            ProcessoNovo.valor_acao.is_(None),
                        ))
                    else:
                        valor_subq = valor_subq.where(
                            ProcessoNovo.valor_acao <= filters.valor_max
                        )
                else:
                    valor_subq = valor_subq.where(
                        ProcessoNovo.valor_acao.isnot(None)
                    )
                stmt = stmt.where(
                    model.numero_processo.in_(valor_subq.distinct().scalar_subquery())
                )

        # Excluir produção oculta por regras administrativas
        if filters.exclude_hidden and model.__tablename__ in _HIDDEN_TABLES:
            stmt = self._apply_hidden_filter_orm(stmt, model, date_col)

        result = await self.session.execute(stmt)
        return result.scalar() or 0

    def _apply_hidden_filter_orm(self, stmt, model, date_col):
        """Adiciona NOT EXISTS para excluir registros de procuradores ocultos."""
        hidden = HiddenProcuradorProducao.__table__
        resolved_col = _HIDDEN_RESOLVED_COL.get(
            model.__tablename__, "procurador"
        )
        proc_col = normalize_procurador_expr(getattr(model, resolved_col))
        chefia_col = normalize_chefia_expr(model.chefia)

        exists_subq = (
            select(literal(1))
            .select_from(hidden)
            .where(
                hidden.c.is_active.is_(True),
                hidden.c.procurador_name == proc_col,
                or_(
                    hidden.c.chefia.is_(None),
                    hidden.c.chefia == chefia_col,
                ),
                date_col >= func.cast(hidden.c.start_date, DateTime),
                date_col < func.cast(
                    hidden.c.end_date + text("INTERVAL '1 day'"), DateTime
                ),
            )
            .correlate(model)
            .exists()
        )
        return stmt.where(~exists_subq)

    async def _valor_aggregates(self, filters: GlobalFilters) -> tuple[float, float]:
        """Retorna (soma, média) de valor_acao de TODOS os processos no banco.

        O valor da causa é propriedade imutável do processo — não faz sentido
        filtrar por ano/data. Apenas o filtro de faixa (valor_min/valor_max)
        é aplicado.
        """
        stmt = select(
            func.coalesce(func.sum(ProcessoNovo.valor_acao), 0),
            func.coalesce(func.avg(ProcessoNovo.valor_acao), 0),
        ).select_from(ProcessoNovo).where(ProcessoNovo.valor_acao.isnot(None))

        if filters.valor_min is not None:
            stmt = stmt.where(ProcessoNovo.valor_acao >= filters.valor_min)
        if filters.valor_max is not None:
            stmt = stmt.where(ProcessoNovo.valor_acao <= filters.valor_max)

        result = await self.session.execute(stmt)
        row = result.one()
        return float(row[0]), float(row[1])

    async def get_kpis(self, filters: GlobalFilters) -> list[KPIValue]:
        """Retorna os KPIs principais do Overview.

        Peças elaboradas é métrica de assessor e aparece apenas em /perfil-assessor.
        """
        count_pn = await self._count_filtered(ProcessoNovo, filters)
        count_pf = await self._count_filtered(PecaFinalizada, filters)
        count_pd = await self._count_filtered(Pendencia, filters)
        valor_total, valor_medio = await self._valor_aggregates(filters)

        return [
            KPIValue(label="Processos Novos", valor=count_pn),
            KPIValue(label="Peças Finalizadas", valor=count_pf),
            KPIValue(label="Pendências", valor=count_pd),
            KPIValue(label="Valor Total Causas", valor=valor_total, formato="moeda"),
            KPIValue(label="Valor Médio Causa", valor=valor_medio, formato="moeda"),
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
