"""Serviço para carregar opções dos filtros globais."""

import logging

from sqlalchemy import func, select, distinct
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.models import Assunto, PecaElaborada, Pendencia, ProcessoAssunto, ProcessoNovo, UserRole
from src.domain.schemas import AssuntoNode, FilterOptions
from src.services.cache import cached
from src.services.normalization import normalize_chefia_expr, normalize_procurador_expr

logger = logging.getLogger(__name__)


class FilterOptionsService:
    """Carrega valores distintos para popular os dropdowns de filtro."""

    def __init__(self, session: AsyncSession):
        self.session = session

    @cached(ttl=3600)
    async def get_options(self) -> FilterOptions:
        """Retorna todas as opções de filtro disponíveis."""
        chefias = await self._distinct_values(ProcessoNovo, "chefia")
        procuradores = await self._distinct_values(ProcessoNovo, "procurador")
        categorias = await self._distinct_values(PecaElaborada, "categoria")
        areas = await self._distinct_values(Pendencia, "area")
        anos = await self._get_anos()

        return FilterOptions(
            chefias=chefias,
            procuradores=procuradores,
            categorias=categorias,
            areas=areas,
            anos=anos,
        )

    def _get_normalized_expr(self, model: type, column: str):
        """Retorna expressão normalizada para a coluna quando aplicável."""
        col = getattr(model, column)
        if column == "chefia":
            return normalize_chefia_expr(col)
        if column == "procurador":
            return normalize_procurador_expr(col)
        return col

    async def _distinct_values(
        self, model: type, column: str
    ) -> list[str]:
        """Busca valores distintos de uma coluna com normalização."""
        col = getattr(model, column)
        expr = self._get_normalized_expr(model, column)

        stmt = (
            select(expr.label("valor"))
            .where(col.isnot(None))
            .where(col != "")
            .distinct()
            .order_by(expr)
        )
        result = await self.session.execute(stmt)
        return [str(row[0]) for row in result.all()]

    @cached(ttl=3600)
    async def get_assessores(self) -> list[str]:
        """Retorna nomes de assessores consultando user_roles, com fallback."""
        # Tentar consultar tabela user_roles primeiro
        try:
            stmt = (
                select(UserRole.name)
                .where(UserRole.role == "assessor")
                .order_by(UserRole.name)
            )
            result = await self.session.execute(stmt)
            names = [str(row[0]) for row in result.all()]
            if names:
                return names
        except Exception:
            logger.debug("Tabela user_roles não disponível, usando fallback.")

        # Fallback: lógica original por exclusão
        proc_subq = (
            select(distinct(PecaElaborada.procurador))
            .where(PecaElaborada.procurador.isnot(None))
            .scalar_subquery()
        )
        stmt = (
            select(distinct(PecaElaborada.usuario_criacao))
            .where(PecaElaborada.usuario_criacao.isnot(None))
            .where(PecaElaborada.usuario_criacao != "")
            .where(PecaElaborada.usuario_criacao.notin_(proc_subq))
            .order_by(PecaElaborada.usuario_criacao)
        )
        result = await self.session.execute(stmt)
        return [str(row[0]) for row in result.all()]

    async def _get_anos(self) -> list[int]:
        """Retorna anos disponíveis nos dados."""
        stmt = (
            select(func.extract("year", ProcessoNovo.data).label("ano"))
            .where(ProcessoNovo.data.isnot(None))
            .distinct()
            .order_by(func.extract("year", ProcessoNovo.data))
        )
        result = await self.session.execute(stmt)
        return [int(row.ano) for row in result.all()]

    @cached(ttl=3600)
    async def get_assuntos_tree(self) -> list[AssuntoNode]:
        """Retorna árvore hierárquica de assuntos vinculados a processos.

        Somente assuntos efetivamente usados (ou seus ancestrais) são retornados.
        """
        # Buscar códigos de assuntos que possuem pelo menos 1 vínculo com processo
        used_stmt = (
            select(distinct(ProcessoAssunto.codigo_assunto))
        )
        used_result = await self.session.execute(used_stmt)
        used_codes = {row[0] for row in used_result.all()}

        if not used_codes:
            return []

        # Buscar todos os assuntos
        all_stmt = select(Assunto).order_by(Assunto.nivel, Assunto.nome)
        all_result = await self.session.execute(all_stmt)
        all_assuntos = all_result.scalars().all()

        # Mapear por código para acesso rápido
        by_code: dict[int, Assunto] = {a.codigo: a for a in all_assuntos}

        # Expandir ancestrais: para cada assunto usado, incluir toda a cadeia até a raiz
        relevant_codes = set(used_codes)
        for code in used_codes:
            current = by_code.get(code)
            while current and current.codigo_pai:
                relevant_codes.add(current.codigo_pai)
                current = by_code.get(current.codigo_pai)

        # Construir árvore: agrupar filhos por codigo_pai
        children_map: dict[int | None, list[Assunto]] = {}
        for a in all_assuntos:
            if a.codigo not in relevant_codes:
                continue
            parent_key = a.codigo_pai
            children_map.setdefault(parent_key, []).append(a)

        def build_nodes(parent_code: int | None) -> list[AssuntoNode]:
            """Constrói lista de nós recursivamente."""
            children = children_map.get(parent_code, [])
            nodes = []
            for child in children:
                node = AssuntoNode(
                    codigo=child.codigo,
                    nome=child.nome or "",
                    nivel=child.nivel or 1,
                    filhos=build_nodes(child.codigo),
                )
                nodes.append(node)
            return nodes

        return build_nodes(None)
