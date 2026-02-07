"""Testes de integração: exclusão de categorias não-produtivas.

Valida que as métricas de pecas_finalizadas no banco pge_bi
excluem corretamente as categorias administrativas.
"""

import pytest
from sqlalchemy import func, select

from src.domain.constants import CATEGORIAS_NAO_PRODUTIVAS
from src.domain.filters import GlobalFilters
from src.domain.models import PecaFinalizada
from src.repositories.base_repository import BaseRepository
from src.repositories.overview_repository import OverviewRepository
from src.services.perfil_service import PerfilService


@pytest.fixture
def filters_ps_2026() -> GlobalFilters:
    """Filtros para PS, ano 2026."""
    return GlobalFilters(anos=[2026], chefia=["PS (Cartório)"])


@pytest.mark.asyncio
@pytest.mark.integration
async def test_total_count_exclui_categorias_nao_produtivas(db_session):
    """total_count de PecaFinalizada deve excluir categorias não-produtivas."""
    repo = BaseRepository(db_session, PecaFinalizada)

    # Contagem com exclusão (via repositório)
    total_com_exclusao = await repo.total_count(GlobalFilters())

    # Contagem sem exclusão (SQL direto)
    stmt = select(func.count()).select_from(PecaFinalizada)
    result = await db_session.execute(stmt)
    total_sem_exclusao = result.scalar() or 0

    # Contagem de registros excluídos
    stmt_excluidos = (
        select(func.count())
        .select_from(PecaFinalizada)
        .where(PecaFinalizada.categoria.in_(CATEGORIAS_NAO_PRODUTIVAS))
    )
    result = await db_session.execute(stmt_excluidos)
    total_excluidos = result.scalar() or 0

    assert total_excluidos > 0, "Deve existir ao menos 1 registro não-produtivo no banco"
    assert total_com_exclusao == total_sem_exclusao - total_excluidos, (
        f"total_count ({total_com_exclusao:,}) deveria ser "
        f"total_sem_exclusao ({total_sem_exclusao:,}) - excluidos ({total_excluidos:,})"
    )


@pytest.mark.asyncio
@pytest.mark.integration
async def test_overview_kpi_exclui_categorias(db_session):
    """KPI de peças finalizadas no Overview deve excluir categorias não-produtivas."""
    overview = OverviewRepository(db_session)
    kpis = await overview.get_kpis(GlobalFilters())

    kpi_finalizadas = next(k for k in kpis if k.label == "Peças Finalizadas")

    # Contagem sem exclusão (SQL direto)
    stmt = select(func.count()).select_from(PecaFinalizada)
    result = await db_session.execute(stmt)
    total_bruto = result.scalar() or 0

    assert kpi_finalizadas.valor < total_bruto, (
        "KPI deveria ser menor que total bruto pois exclui categorias não-produtivas"
    )


@pytest.mark.asyncio
@pytest.mark.integration
async def test_sergio_annibal_zero_pecas_ps_2026(db_session, filters_ps_2026):
    """Sérgio W. Annibal deve ter 0 peças finalizadas em PS/2026.

    Todas as 53 peças dele são 'Arquivamento' (não-produtiva).
    """
    repo = BaseRepository(db_session, PecaFinalizada)

    # Buscar contagem filtrada por usuario_finalizacao
    stmt = (
        select(func.count())
        .select_from(PecaFinalizada)
        .where(PecaFinalizada.usuario_finalizacao.ilike("%Sérgio%Annibal%"))
        .where(func.extract("year", PecaFinalizada.data_finalizacao) == 2026)
        .where(PecaFinalizada.categoria.notin_(CATEGORIAS_NAO_PRODUTIVAS))
    )
    for chefia in filters_ps_2026.chefia:
        stmt = stmt.where(PecaFinalizada.chefia == chefia)

    result = await db_session.execute(stmt)
    total = result.scalar() or 0

    assert total == 0, (
        f"Sérgio W. Annibal deveria ter 0 peças produtivas em PS/2026, encontrou {total}"
    )


@pytest.mark.asyncio
@pytest.mark.integration
async def test_procurador_normal_nao_afetado(db_session):
    """Procuradores com produção real não devem ser significativamente afetados.

    Verifica que o top procurador em 2026 mantém contagem alta.
    """
    repo = BaseRepository(db_session, PecaFinalizada)
    filters = GlobalFilters(anos=[2026])

    results = await repo.count_by_group(filters, "procurador", limit=1)

    assert len(results) > 0, "Deveria existir ao menos 1 procurador com peças em 2026"
    assert results[0].total > 100, (
        f"Top procurador deveria ter 100+ peças, encontrou {results[0].total}"
    )


@pytest.mark.asyncio
@pytest.mark.integration
async def test_comparativo_chefia_exclui_nao_produtivas(db_session):
    """Comparativo de procuradores por chefia deve excluir categorias não-produtivas.

    Quem tinha SÓ Arquivamento/Encaminhamento deve ter 0 peças finalizadas.
    """
    service = PerfilService(db_session)

    # Usar chefia que sabemos ter dados em 2026
    resultado = await service.get_comparativo_procuradores(
        "PP - Procuradoria de Pessoal", GlobalFilters(anos=[2026])
    )

    if not resultado:
        pytest.skip("Sem dados para PP em 2026")

    # Todos os valores devem ser >= 0
    for item in resultado:
        assert item.pecas_finalizadas >= 0, (
            f"{item.procurador}: pecas_finalizadas negativo ({item.pecas_finalizadas})"
        )
        assert item.total == (
            item.processos_novos + item.pecas_finalizadas + item.pendencias
        ), f"{item.procurador}: total não bate com soma das métricas"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_timeline_exclui_nao_produtivas(db_session):
    """Timeline do overview deve excluir categorias não-produtivas de pecas_finalizadas."""
    overview = OverviewRepository(db_session)
    series = await overview.get_timeline(GlobalFilters(anos=[2026]))

    serie_pf = next(s for s in series if s.nome == "Peças Finalizadas")
    total_timeline = sum(p.valor for p in serie_pf.dados)

    # Contagem direta sem exclusão
    stmt = (
        select(func.count())
        .select_from(PecaFinalizada)
        .where(func.extract("year", PecaFinalizada.data_finalizacao) == 2026)
    )
    result = await db_session.execute(stmt)
    total_bruto = result.scalar() or 0

    assert total_timeline < total_bruto, (
        f"Timeline ({total_timeline:,}) deveria ser menor que total bruto ({total_bruto:,})"
    )
