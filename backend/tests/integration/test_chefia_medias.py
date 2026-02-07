"""Testes para médias de chefia (helpers e endpoint).

Testes unitários (sem banco): resolve_date_range e compute_units_count.
Testes de integração (com banco): endpoint chefia-medias via PerfilService.
"""

from datetime import date

import pytest

from src.domain.filters import GlobalFilters
from src.services.perfil_service import PerfilService


# --- Testes unitários: resolve_date_range ---


def test_resolve_date_range_com_anos():
    """anos=[2025] → jan a dez de 2025."""
    filters = GlobalFilters(anos=[2025])
    start, end = PerfilService.resolve_date_range(filters)

    assert start == date(2025, 1, 1)
    assert end == date(2025, 12, 31)


def test_resolve_date_range_com_anos_e_mes():
    """anos=[2025], mes=3 → março de 2025."""
    filters = GlobalFilters(anos=[2025], mes=3)
    start, end = PerfilService.resolve_date_range(filters)

    assert start == date(2025, 3, 1)
    assert end == date(2025, 3, 31)


def test_resolve_date_range_com_range_explicito():
    """data_inicio/data_fim direto → usa os valores fornecidos."""
    filters = GlobalFilters(
        data_inicio=date(2025, 6, 15),
        data_fim=date(2025, 9, 20),
    )
    start, end = PerfilService.resolve_date_range(filters)

    assert start == date(2025, 6, 15)
    assert end == date(2025, 9, 20)


def test_resolve_date_range_com_multiplos_anos():
    """anos=[2024, 2025] → jan/2024 a dez/2025."""
    filters = GlobalFilters(anos=[2024, 2025])
    start, end = PerfilService.resolve_date_range(filters)

    assert start == date(2024, 1, 1)
    assert end == date(2025, 12, 31)


def test_resolve_date_range_fallback():
    """Sem filtros → ano corrente até hoje."""
    filters = GlobalFilters()
    start, end = PerfilService.resolve_date_range(filters)

    today = date.today()
    assert start == date(today.year, 1, 1)
    assert end == today


# --- Testes unitários: compute_units_count ---


def test_compute_units_count_diario():
    """Ano de 2025 = 365 dias."""
    count, label = PerfilService.compute_units_count(
        date(2025, 1, 1), date(2025, 12, 31), "day"
    )
    assert count == 365
    assert label == "dias"


def test_compute_units_count_mensal():
    """Ano de 2025 = 12 meses."""
    count, label = PerfilService.compute_units_count(
        date(2025, 1, 1), date(2025, 12, 31), "month"
    )
    assert count == 12
    assert label == "meses"


def test_compute_units_count_anual():
    """2024 a 2025 = 2 anos."""
    count, label = PerfilService.compute_units_count(
        date(2024, 1, 1), date(2025, 12, 31), "year"
    )
    assert count == 2
    assert label == "anos"


def test_compute_units_count_minimo_1():
    """Mesmo com range zero, retorna no mínimo 1."""
    count, label = PerfilService.compute_units_count(
        date(2025, 3, 15), date(2025, 3, 15), "year"
    )
    assert count >= 1


def test_compute_units_count_mes_parcial():
    """Março a maio = 3 meses."""
    count, label = PerfilService.compute_units_count(
        date(2025, 3, 1), date(2025, 5, 31), "month"
    )
    assert count == 3
    assert label == "meses"


# --- Testes de integração (com banco) ---


@pytest.mark.asyncio
@pytest.mark.integration
async def test_chefia_medias_retorna_3_kpis(db_session):
    """Endpoint retorna 3 KPIs (processos, finalizadas, pendências)."""
    service = PerfilService(db_session)
    filters = GlobalFilters(anos=[2025])

    result = await service.get_chefia_medias(
        chefia="PA - Procuradoria Administrativa",
        filters=filters,
        average_unit="month",
    )

    assert len(result.kpis) == 3
    labels = [k.label for k in result.kpis]
    assert "Processos Novos" in labels
    assert "Peças Finalizadas" in labels
    assert "Pendências" in labels


@pytest.mark.asyncio
@pytest.mark.integration
async def test_media_igual_total_dividido_unidades(db_session):
    """media == round(total / units_count, 2) para cada KPI."""
    service = PerfilService(db_session)
    filters = GlobalFilters(anos=[2025])

    result = await service.get_chefia_medias(
        chefia="PA - Procuradoria Administrativa",
        filters=filters,
        average_unit="month",
    )

    for kpi in result.kpis:
        expected = round(kpi.total / result.units_count, 2)
        assert kpi.media == expected, (
            f"{kpi.label}: media={kpi.media}, esperado={expected} "
            f"(total={kpi.total}, units={result.units_count})"
        )


@pytest.mark.asyncio
@pytest.mark.integration
async def test_filtro_procurador_reduz_totais(db_session):
    """Selecionar 1 procurador produz total ≤ total geral."""
    service = PerfilService(db_session)
    chefia = "PP - Procuradoria de Pessoal"
    filters = GlobalFilters(anos=[2026])

    # Total geral
    geral = await service.get_chefia_medias(
        chefia=chefia, filters=filters, average_unit="month"
    )

    # Comparativo para pegar um procurador
    comp = await service.get_comparativo_procuradores(chefia, filters)
    if not comp:
        pytest.skip("Sem procuradores em PA/2025")

    nome = comp[0].procurador

    # Total filtrado
    filtrado = await service.get_chefia_medias(
        chefia=chefia,
        filters=filters,
        average_unit="month",
        procurador_nomes=[nome],
    )

    for kpi_geral, kpi_filtrado in zip(geral.kpis, filtrado.kpis):
        assert kpi_filtrado.total <= kpi_geral.total, (
            f"{kpi_geral.label}: filtrado ({kpi_filtrado.total}) > geral ({kpi_geral.total})"
        )


@pytest.mark.asyncio
@pytest.mark.integration
async def test_sem_procuradores_igual_total_geral(db_session):
    """procurador_nomes=[] deve retornar mesmo resultado que sem filtro."""
    service = PerfilService(db_session)
    chefia = "PA - Procuradoria Administrativa"
    filters = GlobalFilters(anos=[2025])

    sem_filtro = await service.get_chefia_medias(
        chefia=chefia, filters=filters, average_unit="month"
    )

    com_lista_vazia = await service.get_chefia_medias(
        chefia=chefia,
        filters=filters,
        average_unit="month",
        procurador_nomes=None,
    )

    for kpi_a, kpi_b in zip(sem_filtro.kpis, com_lista_vazia.kpis):
        assert kpi_a.total == kpi_b.total, (
            f"{kpi_a.label}: sem_filtro={kpi_a.total} != lista_vazia={kpi_b.total}"
        )
