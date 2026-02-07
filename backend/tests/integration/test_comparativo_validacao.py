"""Testes de validação: comparativo entre procuradores de uma chefia.

Garante que a agregação por procurador produz resultados consistentes
e que a soma por procurador bate com o total da chefia (tolerância zero).
Apenas métricas de procurador: processos_novos, pecas_finalizadas, pendencias.
"""

import pytest
from sqlalchemy import func, select

from src.domain.constants import CATEGORIAS_NAO_PRODUTIVAS
from src.domain.filters import GlobalFilters
from src.domain.models import (
    PecaFinalizada,
    Pendencia,
    ProcessoNovo,
    UserRole,
)
from src.services.normalization import normalize_chefia_expr
from src.services.perfil_service import (
    COMPARATIVO_PERSON_COL,
    PROCURADOR_TABLES,
    PerfilService,
)

# Chefias para teste (cenários diferentes)
CHEFIAS_TESTE = [
    "PS - Procuradoria de Sa\u00fade",
    "PP - Procuradoria de Pessoal",
]

TABLE_MODELS = {
    "processos_novos": ProcessoNovo,
    "pecas_finalizadas": PecaFinalizada,
    "pendencias": Pendencia,
}


@pytest.fixture
def empty_filters() -> GlobalFilters:
    """Filtros globais vazios (sem restrição de período ou chefia)."""
    return GlobalFilters()


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.parametrize("chefia", CHEFIAS_TESTE)
async def test_comparativo_usa_apenas_metricas_procurador(
    db_session, chefia, empty_filters
):
    """Comparativo deve retornar apenas processos_novos, pecas_finalizadas, pendencias."""
    service = PerfilService(db_session)
    resultado = await service.get_comparativo_procuradores(chefia, empty_filters)

    if not resultado:
        pytest.skip(f"Sem dados para chefia {chefia}")

    item = resultado[0]
    assert hasattr(item, "processos_novos")
    assert hasattr(item, "pecas_finalizadas")
    assert hasattr(item, "pendencias")
    assert not hasattr(item, "pecas_elaboradas"), "pecas_elaboradas não deve aparecer no comparativo"


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.parametrize("chefia", CHEFIAS_TESTE)
async def test_soma_por_procurador_igual_total_chefia(
    db_session, chefia, empty_filters
):
    """A soma de registros por procurador deve ser IGUAL ao total da chefia.

    Cada registro tem um procurador (pode ser nulo/vazio, excluído da contagem).
    A partição por procurador deve ser exaustiva.
    """
    service = PerfilService(db_session)
    resultado = await service.get_comparativo_procuradores(chefia, empty_filters)

    if not resultado:
        pytest.skip(f"Sem dados para chefia {chefia}")

    # Subquery: nomes classificados como procurador
    proc_names_sq = (
        select(UserRole.name)
        .where(UserRole.role == "procurador")
        .scalar_subquery()
    )

    for table_name, model in TABLE_MODELS.items():
        chefia_expr = normalize_chefia_expr(model.chefia)

        # Usa a mesma coluna de atribuição que o comparativo
        person_col_name = COMPARATIVO_PERSON_COL[table_name]
        person_col = getattr(model, person_col_name)

        # Total de registros da chefia — apenas procuradores (mesma lógica do comparativo)
        stmt_total = (
            select(func.count())
            .select_from(model)
            .where(chefia_expr == chefia)
            .where(person_col.isnot(None))
            .where(person_col != "")
            .where(person_col.in_(proc_names_sq))
        )

        # Excluir categorias não-produtivas (mesma lógica do repositório)
        if model is PecaFinalizada:
            stmt_total = stmt_total.where(
                PecaFinalizada.categoria.notin_(CATEGORIAS_NAO_PRODUTIVAS)
            )
        result = await db_session.execute(stmt_total)
        total_chefia = result.scalar() or 0

        # Soma do comparativo para esta métrica
        soma_procuradores = sum(getattr(r, table_name) for r in resultado)

        assert soma_procuradores == total_chefia, (
            f"[{chefia}][{table_name}] "
            f"Soma por procurador ({soma_procuradores:,}) != "
            f"total da chefia ({total_chefia:,}). "
            f"Diferença: {soma_procuradores - total_chefia:,}"
        )


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.parametrize("chefia", CHEFIAS_TESTE)
async def test_nenhum_valor_negativo(
    db_session, chefia, empty_filters
):
    """Todos os valores do comparativo devem ser >= 0."""
    service = PerfilService(db_session)
    resultado = await service.get_comparativo_procuradores(chefia, empty_filters)

    for item in resultado:
        assert item.processos_novos >= 0, f"{item.procurador}: processos_novos negativo"
        assert item.pecas_finalizadas >= 0, f"{item.procurador}: pecas_finalizadas negativo"
        assert item.pendencias >= 0, f"{item.procurador}: pendencias negativo"
        assert item.total >= 0, f"{item.procurador}: total negativo"


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.parametrize("chefia", CHEFIAS_TESTE)
async def test_total_igual_soma_3_metricas(
    db_session, chefia, empty_filters
):
    """O campo 'total' deve ser a soma das 3 métricas de procurador."""
    service = PerfilService(db_session)
    resultado = await service.get_comparativo_procuradores(chefia, empty_filters)

    for item in resultado:
        soma = item.processos_novos + item.pecas_finalizadas + item.pendencias
        assert item.total == soma, (
            f"{item.procurador}: total ({item.total:,}) != "
            f"soma das 3 métricas ({soma:,})"
        )


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.parametrize("chefia", CHEFIAS_TESTE)
async def test_kpis_chefia_sem_elaboradas(
    db_session, chefia, empty_filters
):
    """KPIs de chefia devem ter 3 métricas (sem pecas_elaboradas)."""
    service = PerfilService(db_session)
    kpis = await service.get_kpis("chefia", chefia, empty_filters)

    labels = [k.label for k in kpis]
    assert "Processos Novos" in labels
    assert "Peças Finalizadas" in labels
    assert "Pendências" in labels
    assert "Peças Elaboradas" not in labels, "pecas_elaboradas não deve aparecer em KPIs de chefia"


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.parametrize("chefia", CHEFIAS_TESTE)
async def test_comparativo_sem_assessores(
    db_session, chefia, empty_filters
):
    """Comparativo não deve incluir nenhum assessor (apenas procuradores)."""
    service = PerfilService(db_session)
    resultado = await service.get_comparativo_procuradores(chefia, empty_filters)

    if not resultado:
        pytest.skip(f"Sem dados para chefia {chefia}")

    # Buscar nomes de assessores
    stmt = select(UserRole.name).where(UserRole.role == "assessor")
    result = await db_session.execute(stmt)
    assessor_names = {str(row[0]) for row in result.all()}

    assessores_encontrados = [
        item.procurador for item in resultado
        if item.procurador in assessor_names
    ]
    assert not assessores_encontrados, (
        f"[{chefia}] Assessores no comparativo: {assessores_encontrados[:5]}"
    )


@pytest.mark.asyncio
@pytest.mark.integration
async def test_kpis_assessor_inclui_elaboradas(db_session, empty_filters):
    """KPIs de assessor devem incluir pecas_elaboradas."""
    service = PerfilService(db_session)
    # Usar um nome genérico — o teste valida a lógica, não os dados
    kpis = await service.get_kpis("assessor", "TESTE_INEXISTENTE", empty_filters)

    labels = [k.label for k in kpis]
    assert "Peças Elaboradas" in labels, "pecas_elaboradas deve aparecer em KPIs de assessor"
    assert "Peças Finalizadas" in labels
    assert "Processos Novos" in labels
    assert "Pendências" in labels
