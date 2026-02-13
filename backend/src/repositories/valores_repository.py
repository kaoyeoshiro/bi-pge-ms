"""Repositório de análise de valores da causa (processos_novos.valor_acao)."""

from sqlalchemy import Select, case, cast, func, literal_column, select, Numeric
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.filters import GlobalFilters
from src.domain.models import Assunto, ProcessoAssunto, ProcessoNovo
from src.domain.schemas import TimelinePoint, ValorFaixaItem, ValorGroupItem
from src.repositories.base_repository import BaseRepository
from src.services.normalization import normalize_chefia_expr

# Ano mínimo padrão — processos com ano CNJ anterior são excluídos
# quando nenhum filtro de ano é aplicado explicitamente.
ANO_MINIMO_PADRAO = 2021

# Faixas fixas de valor da causa
FAIXAS = [
    ("Sem valor", None, None),
    ("Até R$ 10 mil", 0.01, 10_000),
    ("R$ 10 mil – 100 mil", 10_000.01, 100_000),
    ("R$ 100 mil – 1 milhão", 100_000.01, 1_000_000),
    ("Acima de R$ 1 milhão", 1_000_000.01, None),
]


class ValoresRepository(BaseRepository):
    """Operações de agregação sobre valor_acao de processos_novos."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, ProcessoNovo)

    def _apply_global_filters(
        self, stmt: Select, filters: GlobalFilters
    ) -> Select:
        """Aplica filtros globais com piso de ano padrão (2021+).

        Quando nenhum ano é selecionado, aplica ano CNJ >= 2021
        para evitar que processos antigos com valores extremos
        distorçam as métricas.
        """
        if not filters.anos:
            year_expr = self._get_year_expr()
            stmt = stmt.where(year_expr >= ANO_MINIMO_PADRAO)
        return super()._apply_global_filters(stmt, filters)

    async def get_aggregates(self, filters: GlobalFilters) -> dict:
        """Retorna métricas agregadas de valor: soma, média, mediana, qtd."""
        stmt = (
            select(
                func.sum(ProcessoNovo.valor_acao).label("soma"),
                func.avg(ProcessoNovo.valor_acao).label("media"),
                func.percentile_cont(0.5)
                .within_group(ProcessoNovo.valor_acao)
                .label("mediana"),
                func.count()
                .filter(ProcessoNovo.valor_acao.isnot(None))
                .label("qtd_com_valor"),
                func.count().label("qtd_total"),
            )
            .select_from(ProcessoNovo)
        )
        stmt = self._apply_global_filters(stmt, filters)

        result = await self.session.execute(stmt)
        row = result.one()

        qtd_com = row.qtd_com_valor or 0
        qtd_total = row.qtd_total or 0
        return {
            "soma": float(row.soma or 0),
            "media": float(row.media or 0),
            "mediana": float(row.mediana or 0),
            "qtd_com_valor": qtd_com,
            "qtd_total": qtd_total,
            "pct_com_valor": round(
                (qtd_com / qtd_total * 100) if qtd_total > 0 else 0, 2
            ),
        }

    async def get_distribuicao(self, filters: GlobalFilters) -> list[ValorFaixaItem]:
        """Distribuição de processos pelas faixas fixas de valor."""
        faixa_expr = case(
            (ProcessoNovo.valor_acao.is_(None), literal_column("0")),
            (ProcessoNovo.valor_acao <= 10_000, literal_column("1")),
            (ProcessoNovo.valor_acao <= 100_000, literal_column("2")),
            (ProcessoNovo.valor_acao <= 1_000_000, literal_column("3")),
            else_=literal_column("4"),
        )

        stmt = (
            select(
                faixa_expr.label("faixa_idx"),
                func.count().label("qtd"),
                func.coalesce(func.sum(ProcessoNovo.valor_acao), 0).label("valor_total"),
                func.coalesce(
                    func.avg(ProcessoNovo.valor_acao)
                    .filter(ProcessoNovo.valor_acao.isnot(None)),
                    0,
                ).label("valor_medio"),
            )
            .select_from(ProcessoNovo)
            .group_by(faixa_expr)
            .order_by(faixa_expr)
        )
        stmt = self._apply_global_filters(stmt, filters)

        result = await self.session.execute(stmt)
        rows = result.all()

        total_geral = sum(r.qtd for r in rows) or 1
        faixa_names = [f[0] for f in FAIXAS]

        items = []
        for row in rows:
            idx = int(row.faixa_idx)
            items.append(
                ValorFaixaItem(
                    faixa=faixa_names[idx],
                    qtd=row.qtd,
                    percentual=round(row.qtd / total_geral * 100, 2),
                    valor_total=float(row.valor_total),
                    valor_medio=float(row.valor_medio),
                )
            )

        return items

    async def get_por_grupo(
        self,
        filters: GlobalFilters,
        grupo: str,
        metrica: str = "total",
        limit: int = 15,
    ) -> list[ValorGroupItem]:
        """Ranking de valor por dimensão (chefia, procurador, assunto)."""
        if grupo == "assunto":
            return await self._get_por_assunto(filters, metrica, limit)

        if grupo == "chefia":
            group_expr = normalize_chefia_expr(ProcessoNovo.chefia)
            col = ProcessoNovo.chefia
        else:
            # procurador — usa coluna direta (processos_novos não tem resolução)
            group_expr = self._get_group_expr("procurador")
            col = ProcessoNovo.procurador

        order_col = (
            func.sum(ProcessoNovo.valor_acao)
            if metrica == "total"
            else func.avg(ProcessoNovo.valor_acao)
        )

        stmt = (
            select(
                group_expr.label("grupo"),
                func.count().label("qtd_processos"),
                func.coalesce(func.sum(ProcessoNovo.valor_acao), 0).label("valor_total"),
                func.coalesce(func.avg(ProcessoNovo.valor_acao), 0).label("valor_medio"),
            )
            .select_from(ProcessoNovo)
            .where(col.isnot(None))
            .where(ProcessoNovo.valor_acao > 0)
            .group_by(group_expr)
            .order_by(order_col.desc())
            .limit(limit)
        )
        stmt = self._apply_global_filters(stmt, filters)

        result = await self.session.execute(stmt)
        return [
            ValorGroupItem(
                grupo=row.grupo,
                qtd_processos=row.qtd_processos,
                valor_total=float(row.valor_total),
                valor_medio=float(row.valor_medio),
            )
            for row in result.all()
        ]

    async def _get_por_assunto(
        self,
        filters: GlobalFilters,
        metrica: str,
        limit: int,
    ) -> list[ValorGroupItem]:
        """Ranking de valor por assunto (via JOIN processo_assuntos + assuntos)."""
        order_col = (
            func.sum(ProcessoNovo.valor_acao)
            if metrica == "total"
            else func.avg(ProcessoNovo.valor_acao)
        )

        stmt = (
            select(
                Assunto.nome.label("grupo"),
                func.count().label("qtd_processos"),
                func.coalesce(func.sum(ProcessoNovo.valor_acao), 0).label("valor_total"),
                func.coalesce(func.avg(ProcessoNovo.valor_acao), 0).label("valor_medio"),
            )
            .select_from(ProcessoNovo)
            .join(
                ProcessoAssunto,
                ProcessoAssunto.numero_processo == ProcessoNovo.numero_processo,
            )
            .join(Assunto, Assunto.codigo == ProcessoAssunto.codigo_assunto)
            .where(ProcessoNovo.valor_acao > 0)
            .group_by(Assunto.nome)
            .order_by(order_col.desc())
            .limit(limit)
        )
        stmt = self._apply_global_filters(stmt, filters)

        result = await self.session.execute(stmt)
        return [
            ValorGroupItem(
                grupo=row.grupo,
                qtd_processos=row.qtd_processos,
                valor_total=float(row.valor_total),
                valor_medio=float(row.valor_medio),
            )
            for row in result.all()
        ]

    async def get_timeline(self, filters: GlobalFilters) -> list[TimelinePoint]:
        """Série temporal de valor total mensal."""
        date_col = self._get_date_column()
        period_expr = func.to_char(date_col, "YYYY-MM")

        stmt = (
            select(
                period_expr.label("periodo"),
                func.coalesce(func.sum(ProcessoNovo.valor_acao), 0).label("valor_total"),
                func.coalesce(func.avg(ProcessoNovo.valor_acao), 0).label("valor_medio"),
            )
            .select_from(ProcessoNovo)
            .where(date_col.isnot(None))
            .where(ProcessoNovo.valor_acao > 0)
            .group_by(period_expr)
            .order_by(period_expr)
        )
        stmt = self._apply_global_filters(stmt, filters)

        result = await self.session.execute(stmt)
        return result.all()
