"""Testes para médias de chefia (helpers e endpoint).

Testes unitários (sem banco): _compute_units_from_timelines e compute_units_count.
Testes de integração (com banco): endpoint chefia-medias via PerfilService.
"""

from datetime import date

import pytest

from src.domain.filters import GlobalFilters
from src.domain.schemas import TimelinePoint
from src.services.perfil_service import PerfilService


# --- Testes unitários: _compute_units_from_timelines ---


def test_compute_from_timelines_range_mensal():
    """Timelines de jan a jun/2025 → 6 meses."""
    timelines = {
        "processos_novos": [
            TimelinePoint(periodo="2025-01", valor=10),
            TimelinePoint(periodo="2025-03", valor=5),
        ],
        "pecas_finalizadas": [
            TimelinePoint(periodo="2025-02", valor=8),
            TimelinePoint(periodo="2025-06", valor=3),
        ],
        "pendencias": [],
    }

    count, label = PerfilService._compute_units_from_timelines(timelines, "month")

    assert count == 6
    assert label == "meses"


def test_compute_from_timelines_vazia():
    """Sem dados em nenhuma timeline → retorna 1."""
    timelines = {
        "processos_novos": [],
        "pecas_finalizadas": [],
        "pendencias": [],
    }

    count, label = PerfilService._compute_units_from_timelines(timelines, "month")

    assert count == 1
    assert label == "meses"


def test_compute_from_timelines_um_periodo():
    """Apenas um mês com dados → retorna 1 mês."""
    timelines = {
        "processos_novos": [TimelinePoint(periodo="2025-07", valor=20)],
        "pecas_finalizadas": [],
        "pendencias": [],
    }

    count, label = PerfilService._compute_units_from_timelines(timelines, "month")

    assert count == 1
    assert label == "meses"


def test_compute_from_timelines_unidade_dia():
    """Range jan-mar/2025 em dias = 90 dias (31+28+31)."""
    timelines = {
        "processos_novos": [
            TimelinePoint(periodo="2025-01", valor=10),
            TimelinePoint(periodo="2025-03", valor=5),
        ],
    }

    count, label = PerfilService._compute_units_from_timelines(timelines, "day")

    assert count == 90
    assert label == "dias"


def test_compute_from_timelines_unidade_ano():
    """Range 2024-01 a 2025-06 → 2 anos."""
    timelines = {
        "processos_novos": [
            TimelinePoint(periodo="2024-01", valor=10),
        ],
        "pecas_finalizadas": [
            TimelinePoint(periodo="2025-06", valor=5),
        ],
    }

    count, label = PerfilService._compute_units_from_timelines(timelines, "year")

    assert count == 2
    assert label == "anos"


def test_compute_from_timelines_cross_table_union():
    """Min/max calculados pela UNIÃO de todas as tabelas."""
    timelines = {
        "processos_novos": [TimelinePoint(periodo="2025-04", valor=1)],
        "pecas_finalizadas": [TimelinePoint(periodo="2025-01", valor=1)],
        "pendencias": [TimelinePoint(periodo="2025-09", valor=1)],
    }

    count, label = PerfilService._compute_units_from_timelines(timelines, "month")

    # jan a set = 9 meses
    assert count == 9
    assert label == "meses"


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
