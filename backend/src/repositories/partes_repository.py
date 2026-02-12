"""Repositório para consultas de partes normalizadas e processos."""

import math

from sqlalchemy import func, select, or_, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.models import ParteNormalizada


# Mapeamento de campo de ordenação para coluna do modelo
SORT_COLUMNS = {
    "nome": ParteNormalizada.nome,
    "qtd_processos": ParteNormalizada.qtd_processos,
    "qtd_contra_estado": ParteNormalizada.qtd_contra_estado,
    "qtd_executado_estado": ParteNormalizada.qtd_executado_estado,
    "qtd_advogado": ParteNormalizada.qtd_advogado,
    "qtd_coreu_estado": ParteNormalizada.qtd_coreu_estado,
    "valor_total": ParteNormalizada.valor_total,
    "valor_medio": ParteNormalizada.valor_medio,
}

# Papel -> coluna de contagem + filtro mínimo
ROLE_FILTERS = {
    "demandante": ParteNormalizada.qtd_contra_estado,
    "executado": ParteNormalizada.qtd_executado_estado,
    "advogado": ParteNormalizada.qtd_advogado,
    "coreu": ParteNormalizada.qtd_coreu_estado,
}


class PartesRepository:
    """Acesso a dados de partes normalizadas."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_kpis(self) -> dict:
        """Retorna KPIs gerais de partes."""
        stmt = select(
            func.count().label("total_pessoas"),
            func.count().filter(ParteNormalizada.qtd_contra_estado > 0).label("total_demandantes"),
            func.count().filter(ParteNormalizada.qtd_executado_estado > 0).label("total_executados"),
            func.count().filter(ParteNormalizada.qtd_advogado > 0).label("total_advogados"),
            func.count().filter(ParteNormalizada.qtd_coreu_estado > 0).label("total_coreus"),
            func.sum(ParteNormalizada.valor_total).label("valor_total_causas"),
        ).select_from(ParteNormalizada)
        result = await self.session.execute(stmt)
        row = result.one()

        # Total de processos distintos com partes
        stmt_proc = select(
            func.max(ParteNormalizada.qtd_processos)
        ).select_from(ParteNormalizada)
        # Simplificação: contar processos distintos da tabela partes_processo
        from src.domain.models import ParteProcesso
        stmt_proc = select(
            func.count(func.distinct(ParteProcesso.cd_processo))
        ).select_from(ParteProcesso)
        result_proc = await self.session.execute(stmt_proc)

        return {
            "total_pessoas": row.total_pessoas,
            "total_demandantes": row.total_demandantes,
            "total_executados": row.total_executados,
            "total_advogados": row.total_advogados,
            "total_coreus": row.total_coreus,
            "valor_total_causas": float(row.valor_total_causas or 0),
            "total_processos_com_partes": result_proc.scalar_one(),
        }

    async def get_ranking(
        self,
        role: str | None = None,
        search: str | None = None,
        sort_by: str = "qtd_processos",
        sort_order: str = "desc",
        page: int = 1,
        page_size: int = 25,
    ) -> dict:
        """Retorna ranking paginado de partes normalizadas.

        Args:
            role: Filtro por papel (demandante, executado, advogado, coreu).
            search: Busca textual por nome, CPF, CNPJ ou OAB.
            sort_by: Coluna de ordenação.
            sort_order: Direção (asc/desc).
            page: Página atual.
            page_size: Itens por página.
        """
        base = select(ParteNormalizada)

        # Excluir o próprio Estado
        base = base.where(
            ParteNormalizada.nome.not_ilike("%Estado de Mato Grosso%")
        )

        # Filtro por papel
        if role and role in ROLE_FILTERS:
            col = ROLE_FILTERS[role]
            base = base.where(col > 0)

        # Filtro de busca textual
        if search:
            pattern = f"%{search}%"
            base = base.where(
                or_(
                    ParteNormalizada.nome.ilike(pattern),
                    ParteNormalizada.cpf.ilike(pattern),
                    ParteNormalizada.cnpj.ilike(pattern),
                    ParteNormalizada.oab.ilike(pattern),
                )
            )

        # Contagem total
        count_stmt = select(func.count()).select_from(base.subquery())
        total = (await self.session.execute(count_stmt)).scalar_one()

        # Ordenação
        sort_col = SORT_COLUMNS.get(sort_by, ParteNormalizada.qtd_processos)
        order_fn = desc if sort_order == "desc" else asc
        # Ordenação padrão por papel quando role é especificado
        if role and role in ROLE_FILTERS and sort_by == "qtd_processos":
            role_col_name = {
                "demandante": "qtd_contra_estado",
                "executado": "qtd_executado_estado",
                "advogado": "qtd_advogado",
                "coreu": "qtd_coreu_estado",
            }
            sort_col = SORT_COLUMNS.get(role_col_name[role], sort_col)
        base = base.order_by(order_fn(sort_col), ParteNormalizada.nome)

        # Paginação
        offset = (page - 1) * page_size
        stmt = base.offset(offset).limit(page_size)
        result = await self.session.execute(stmt)
        rows = result.scalars().all()

        items = [
            {
                "id": r.id,
                "nome": r.nome,
                "cpf": r.cpf,
                "cnpj": r.cnpj,
                "oab": r.oab,
                "tipo_pessoa": r.tipo_pessoa,
                "qtd_processos": r.qtd_processos,
                "qtd_contra_estado": r.qtd_contra_estado,
                "qtd_executado_estado": r.qtd_executado_estado,
                "qtd_advogado": r.qtd_advogado,
                "qtd_coreu_estado": r.qtd_coreu_estado,
                "valor_total": float(r.valor_total or 0),
                "valor_medio": float(r.valor_medio or 0),
            }
            for r in rows
        ]

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": math.ceil(total / page_size) if page_size else 1,
        }

    async def get_by_id(self, parte_id: int) -> dict | None:
        """Retorna detalhes de uma parte normalizada por ID."""
        stmt = select(ParteNormalizada).where(ParteNormalizada.id == parte_id)
        result = await self.session.execute(stmt)
        r = result.scalar_one_or_none()
        if not r:
            return None
        return {
            "id": r.id,
            "nome": r.nome,
            "cpf": r.cpf,
            "cnpj": r.cnpj,
            "oab": r.oab,
            "tipo_pessoa": r.tipo_pessoa,
            "qtd_processos": r.qtd_processos,
            "qtd_contra_estado": r.qtd_contra_estado,
            "qtd_executado_estado": r.qtd_executado_estado,
            "qtd_advogado": r.qtd_advogado,
            "qtd_coreu_estado": r.qtd_coreu_estado,
            "valor_total": float(r.valor_total or 0),
            "valor_medio": float(r.valor_medio or 0),
        }

    async def get_processos_da_parte(
        self,
        parte_id: int,
        page: int = 1,
        page_size: int = 25,
    ) -> dict:
        """Retorna processos vinculados a uma parte normalizada."""
        from src.domain.models import ParteProcesso

        # Buscar a chave da parte normalizada
        parte = await self.session.execute(
            select(ParteNormalizada).where(ParteNormalizada.id == parte_id)
        )
        pn = parte.scalar_one_or_none()
        if not pn:
            return {"items": [], "total": 0, "page": page, "page_size": page_size, "total_pages": 0}

        # Filtrar partes_processo pela chave de normalização
        base = select(ParteProcesso)
        if pn.chave_tipo == "CNPJ":
            base = base.where(ParteProcesso.cnpj == pn.chave_valor)
        elif pn.chave_tipo == "CPF":
            base = base.where(ParteProcesso.cpf == pn.chave_valor)
        else:
            base = base.where(ParteProcesso.cd_pessoa == int(pn.chave_valor))

        # Contagem
        count_stmt = select(func.count()).select_from(base.subquery())
        total = (await self.session.execute(count_stmt)).scalar_one()

        # Paginação
        offset = (page - 1) * page_size
        stmt = base.order_by(ParteProcesso.cd_processo).offset(offset).limit(page_size)
        result = await self.session.execute(stmt)
        rows = result.scalars().all()

        items = [
            {
                "cd_processo": r.cd_processo,
                "numero_processo": r.numero_processo,
                "numero_formatado": r.numero_formatado,
                "nome": r.nome,
                "tipo_parte": r.tipo_parte,
                "polo": r.polo,
                "valor_acao": float(r.valor_acao) if r.valor_acao else None,
            }
            for r in rows
        ]

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": math.ceil(total / page_size) if page_size else 1,
        }
