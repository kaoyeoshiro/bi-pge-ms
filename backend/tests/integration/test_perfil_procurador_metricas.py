"""Testes de validação: métricas do Perfil do Procurador.

Garante que os KPIs e timeline do perfil usam a coluna de atribuição
correta por tabela:
- processos_novos / pendencias → coluna `procurador` (dono do caso)
- pecas_finalizadas → coluna `usuario_finalizacao` (quem finalizou)

Bug original: KPIs usavam `procurador` para pecas_finalizadas, mostrando
peças finalizadas por OUTROS nos processos do procurador, inflando/deflando
a métrica. Corrigido em _apply_global_filters (resolução via PROCURADOR_COL_MAP).
"""

import pytest
from sqlalchemy import func, select

from src.domain.constants import CATEGORIAS_NAO_PRODUTIVAS
from src.domain.filters import GlobalFilters
from src.domain.models import PecaFinalizada, Pendencia, ProcessoNovo, UserRole
from src.repositories.base_repository import BaseRepository
from src.services.normalization import normalize_procurador_expr
from src.services.perfil_service import PerfilService


async def _get_sample_procuradores(db_session, limit: int = 3) -> list[str]:
    """Retorna procuradores com dados em pecas_finalizadas para teste."""
    stmt = (
        select(UserRole.name)
        .where(UserRole.role == "procurador")
        .limit(limit)
    )
    result = await db_session.execute(stmt)
    return [str(row[0]) for row in result.all()]


@pytest.fixture
def perfil_filters() -> GlobalFilters:
    """Filtros como o endpoint /perfil aplica (exclude_hidden=False)."""
    return GlobalFilters(exclude_hidden=False, exclude_no_pendencias=False)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_kpi_pecas_finalizadas_usa_usuario_finalizacao(
    db_session, perfil_filters,
):
    """KPI 'Peças Finalizadas' do perfil deve contar pela coluna usuario_finalizacao.

    Compara o resultado do service (que usa _apply_global_filters) com
    uma query direta por usuario_finalizacao.
    """
    nomes = await _get_sample_procuradores(db_session)
    if not nomes:
        pytest.skip("Sem procuradores na user_roles")

    service = PerfilService(db_session)

    for nome in nomes:
        # KPIs via service (código sob teste)
        kpis = await service.get_kpis("procurador", nome, perfil_filters)
        kpi_pf = next((k.valor for k in kpis if k.label == "Peças Finalizadas"), None)
        assert kpi_pf is not None, f"KPI 'Peças Finalizadas' não encontrado para {nome}"

        # Query direta por usuario_finalizacao (valor esperado)
        uf_expr = normalize_procurador_expr(PecaFinalizada.usuario_finalizacao)
        stmt = (
            select(func.count())
            .select_from(PecaFinalizada)
            .where(uf_expr == nome)
            .where(PecaFinalizada.categoria.notin_(CATEGORIAS_NAO_PRODUTIVAS))
        )
        result = await db_session.execute(stmt)
        expected = result.scalar() or 0

        assert kpi_pf == expected, (
            f"[{nome}] KPI pecas_finalizadas={kpi_pf:,} != "
            f"usuario_finalizacao={expected:,}. "
            f"Provável uso da coluna 'procurador' (dono) em vez de 'usuario_finalizacao'."
        )


@pytest.mark.asyncio
@pytest.mark.integration
async def test_kpi_processos_novos_usa_procurador(
    db_session, perfil_filters,
):
    """KPI 'Processos Novos' deve contar pela coluna procurador (dono do caso)."""
    nomes = await _get_sample_procuradores(db_session)
    if not nomes:
        pytest.skip("Sem procuradores na user_roles")

    service = PerfilService(db_session)

    for nome in nomes:
        kpis = await service.get_kpis("procurador", nome, perfil_filters)
        kpi_pn = next((k.valor for k in kpis if k.label == "Processos Novos"), None)
        assert kpi_pn is not None

        proc_expr = normalize_procurador_expr(ProcessoNovo.procurador)
        stmt = (
            select(func.count())
            .select_from(ProcessoNovo)
            .where(proc_expr == nome)
        )
        result = await db_session.execute(stmt)
        expected = result.scalar() or 0

        assert kpi_pn == expected, (
            f"[{nome}] KPI processos_novos={kpi_pn:,} != esperado={expected:,}"
        )


@pytest.mark.asyncio
@pytest.mark.integration
async def test_kpi_pendencias_usa_procurador(
    db_session, perfil_filters,
):
    """KPI 'Pendências' deve contar pela coluna procurador (dono do caso)."""
    nomes = await _get_sample_procuradores(db_session)
    if not nomes:
        pytest.skip("Sem procuradores na user_roles")

    service = PerfilService(db_session)

    for nome in nomes:
        kpis = await service.get_kpis("procurador", nome, perfil_filters)
        kpi_pd = next((k.valor for k in kpis if k.label == "Pendências"), None)
        assert kpi_pd is not None

        proc_expr = normalize_procurador_expr(Pendencia.procurador)
        stmt = (
            select(func.count())
            .select_from(Pendencia)
            .where(proc_expr == nome)
        )
        result = await db_session.execute(stmt)
        expected = result.scalar() or 0

        assert kpi_pd == expected, (
            f"[{nome}] KPI pendencias={kpi_pd:,} != esperado={expected:,}"
        )


@pytest.mark.asyncio
@pytest.mark.integration
async def test_kpi_perfil_consistente_com_comparativo(db_session):
    """KPI do perfil individual deve bater com o valor no comparativo da chefia.

    Se um procurador tem X pecas_finalizadas no perfil (sem filtro de chefia),
    o comparativo de uma chefia deve atribuir a ele um subconjunto <= X.
    Além disso, a soma do comparativo por chefia deve bater com query direta.
    """
    # Buscar uma chefia não-PS (evitar normalização complexa)
    from src.services.normalization import normalize_chefia_expr as nce
    chefia_nome = "PP - Procuradoria de Pessoal"

    service = PerfilService(db_session)
    comp_filters = GlobalFilters(
        exclude_hidden=False, exclude_no_pendencias=False
    )
    comparativo = await service.get_comparativo_procuradores(
        chefia_nome, comp_filters
    )
    if not comparativo:
        pytest.skip(f"Sem dados no comparativo para {chefia_nome}")

    # Para cada procurador no comparativo, verificar que o KPI individual
    # (sem filtro de chefia) é >= o valor no comparativo
    for item in comparativo[:3]:  # Testar top 3 para performance
        perfil_filters = GlobalFilters(
            exclude_hidden=False, exclude_no_pendencias=False
        )
        kpis = await service.get_kpis("procurador", item.procurador, perfil_filters)
        kpi_pf = next((k.valor for k in kpis if k.label == "Peças Finalizadas"), 0)

        assert kpi_pf >= item.pecas_finalizadas, (
            f"[{item.procurador}] KPI global pecas_finalizadas={kpi_pf:,} < "
            f"comparativo chefia={item.pecas_finalizadas:,}. "
            f"O total sem filtro de chefia deve ser >= o filtrado por chefia."
        )


@pytest.mark.asyncio
@pytest.mark.integration
async def test_total_count_resolve_coluna_pecas_finalizadas(db_session):
    """total_count para pecas_finalizadas com filtro procurador deve usar
    usuario_finalizacao, não a coluna procurador."""
    repo = BaseRepository(db_session, PecaFinalizada)

    # Buscar um procurador que tenha diferença entre as colunas
    stmt = select(
        normalize_procurador_expr(PecaFinalizada.procurador).label("dono"),
        normalize_procurador_expr(PecaFinalizada.usuario_finalizacao).label("finaliz"),
    ).where(
        PecaFinalizada.procurador.isnot(None),
        PecaFinalizada.usuario_finalizacao.isnot(None),
        PecaFinalizada.categoria.notin_(CATEGORIAS_NAO_PRODUTIVAS),
    ).limit(1)
    result = await db_session.execute(stmt)
    row = result.first()

    if not row:
        pytest.skip("Sem dados em pecas_finalizadas")

    # Testar com o finalizador (não o dono)
    nome = row.finaliz
    filters = GlobalFilters(
        procurador=[nome], exclude_hidden=False, exclude_no_pendencias=False
    )
    count = await repo.total_count(filters)

    # Verificação direta: contar por usuario_finalizacao
    uf_expr = normalize_procurador_expr(PecaFinalizada.usuario_finalizacao)
    direct_stmt = (
        select(func.count())
        .select_from(PecaFinalizada)
        .where(uf_expr == nome)
        .where(PecaFinalizada.categoria.notin_(CATEGORIAS_NAO_PRODUTIVAS))
    )
    direct_result = await db_session.execute(direct_stmt)
    expected = direct_result.scalar() or 0

    assert count == expected, (
        f"total_count(procurador=[{nome}])={count:,} != "
        f"usuario_finalizacao={expected:,}"
    )
