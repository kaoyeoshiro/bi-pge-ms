"""Testes unitários: exclusão de categorias não-produtivas de pecas_finalizadas.

Valida que a constante CATEGORIAS_NAO_PRODUTIVAS está correta e que
o BaseRepository aplica a exclusão automaticamente.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.domain.constants import CATEGORIAS_NAO_PRODUTIVAS
from src.domain.filters import GlobalFilters
from src.domain.models import PecaElaborada, PecaFinalizada, ProcessoNovo


class TestCategoriasNaoProdutivas:
    """Testes para a constante CATEGORIAS_NAO_PRODUTIVAS."""

    def test_deve_conter_encaminhamentos(self):
        assert "Encaminhamentos" in CATEGORIAS_NAO_PRODUTIVAS

    def test_deve_conter_arquivamento(self):
        assert "Arquivamento" in CATEGORIAS_NAO_PRODUTIVAS

    def test_deve_conter_arquivamento_dos_autos(self):
        assert "Arquivamento dos autos" in CATEGORIAS_NAO_PRODUTIVAS

    def test_deve_conter_desarquivamento_dos_autos(self):
        assert "Desarquivamento dos autos" in CATEGORIAS_NAO_PRODUTIVAS

    def test_deve_conter_ciencia_de_decisao(self):
        assert "Ciência de Decisão / Despacho" in CATEGORIAS_NAO_PRODUTIVAS

    def test_deve_conter_recusa_do_encaminhamento(self):
        assert "Recusa do encaminhamento" in CATEGORIAS_NAO_PRODUTIVAS

    def test_deve_conter_informacao_administrativa(self):
        assert "Informação Administrativa" in CATEGORIAS_NAO_PRODUTIVAS

    def test_deve_conter_decisao_conflito(self):
        assert "Decisão conflito" in CATEGORIAS_NAO_PRODUTIVAS

    def test_deve_conter_desentranhamento(self):
        assert "Desentranhamento" in CATEGORIAS_NAO_PRODUTIVAS

    def test_deve_conter_apensamento(self):
        assert "Apensamento" in CATEGORIAS_NAO_PRODUTIVAS

    def test_deve_conter_autorizacoes_solicitacao_autos(self):
        assert "Autorizações para solicitação de autos" in CATEGORIAS_NAO_PRODUTIVAS

    def test_deve_conter_redirecionamento(self):
        assert "Redirecionamento" in CATEGORIAS_NAO_PRODUTIVAS

    def test_deve_ter_exatamente_12_categorias(self):
        assert len(CATEGORIAS_NAO_PRODUTIVAS) == 12

    def test_nao_deve_conter_categorias_produtivas(self):
        """Categorias jurídicas legítimas NÃO devem estar na lista."""
        produtivas = [
            "Petições diversas",
            "Contestação",
            "Apelação",
            "Agravo de Instrumento (art. 1.015) 2 Grau - SAJ e PJE",
            "Contrarrazões de Recurso (2 Grau)",
            "Embargos de Declaração 1º Grau",
            "Ofícios",
            "Despacho Interno",
            "Ciência",
            "ADI - Anotações de Dispensa de Recurso",
            "Produção de provas",
        ]
        for cat in produtivas:
            assert cat not in CATEGORIAS_NAO_PRODUTIVAS, (
                f"'{cat}' é produtiva e NÃO deveria estar na lista de exclusão"
            )

    def test_deve_ser_frozenset(self):
        """A constante deve ser imutável."""
        assert isinstance(CATEGORIAS_NAO_PRODUTIVAS, frozenset)


class TestBaseRepositoryExclusao:
    """Testa que _apply_global_filters exclui categorias para PecaFinalizada."""

    def test_apply_filters_exclui_categorias_para_peca_finalizada(self):
        """Para PecaFinalizada, o filtro deve incluir cláusula notin."""
        from sqlalchemy import select
        from src.repositories.base_repository import BaseRepository

        session = MagicMock()
        repo = BaseRepository(session, PecaFinalizada)
        filters = GlobalFilters()

        stmt = select(PecaFinalizada)
        result = repo._apply_global_filters(stmt, filters)

        # Verificar que o SQL compilado contém NOT IN com as categorias
        compiled = str(result.compile(compile_kwargs={"literal_binds": True}))
        assert "NOT IN" in compiled
        assert "Encaminhamentos" in compiled
        assert "Arquivamento" in compiled

    def test_apply_filters_nao_exclui_para_processo_novo(self):
        """Para ProcessoNovo, NÃO deve aplicar exclusão de categorias."""
        from sqlalchemy import select
        from src.repositories.base_repository import BaseRepository

        session = MagicMock()
        repo = BaseRepository(session, ProcessoNovo)
        filters = GlobalFilters()

        stmt = select(ProcessoNovo)
        result = repo._apply_global_filters(stmt, filters)

        compiled = str(result.compile(compile_kwargs={"literal_binds": True}))
        assert "NOT IN" not in compiled
        assert "Encaminhamentos" not in compiled

    def test_apply_filters_nao_exclui_para_peca_elaborada(self):
        """Para PecaElaborada, NÃO deve aplicar exclusão de categorias."""
        from sqlalchemy import select
        from src.repositories.base_repository import BaseRepository

        session = MagicMock()
        repo = BaseRepository(session, PecaElaborada)
        filters = GlobalFilters()

        stmt = select(PecaElaborada)
        result = repo._apply_global_filters(stmt, filters)

        compiled = str(result.compile(compile_kwargs={"literal_binds": True}))
        assert "Encaminhamentos" not in compiled
