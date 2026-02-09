"""Dependências de injeção para FastAPI (filtros, paginação, sessão)."""

from datetime import date

from fastapi import Depends, Header, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_session
from src.domain.filters import GlobalFilters, PaginationParams
from src.services.admin_service import AdminAuthService


async def parse_global_filters(
    ano: int | None = Query(None, description="Ano único (retrocompat)"),
    anos: list[int] = Query(default=[], description="Anos para filtrar (múltiplos)"),
    mes: int | None = Query(None, description="Mês para filtrar (1-12)"),
    data_inicio: date | None = Query(None, description="Data inicial (YYYY-MM-DD)"),
    data_fim: date | None = Query(None, description="Data final (YYYY-MM-DD)"),
    chefia: list[str] = Query(default=[], description="Chefias para filtrar"),
    procurador: list[str] = Query(default=[], description="Procuradores para filtrar"),
    categoria: list[str] = Query(default=[], description="Categorias para filtrar"),
    area: list[str] = Query(default=[], description="Áreas para filtrar"),
    assessor: list[str] = Query(default=[], description="Assessores para filtrar"),
    assunto: str = Query("", description="Códigos de assunto separados por vírgula"),
) -> GlobalFilters:
    """Extrai filtros globais dos query params.

    Aceita tanto `ano` (singular, retrocompat) quanto `anos` (múltiplos).
    Se ambos forem fornecidos, `anos` tem prioridade.
    O campo `assunto` aceita códigos separados por vírgula (ex: "123,456,789").
    """
    resolved_anos = anos if anos else ([ano] if ano else [])
    assunto_list = [int(x) for x in assunto.split(",") if x.strip()] if assunto else []
    return GlobalFilters(
        anos=resolved_anos,
        mes=mes,
        data_inicio=data_inicio,
        data_fim=data_fim,
        chefia=chefia,
        procurador=procurador,
        categoria=categoria,
        area=area,
        assessor=assessor,
        assunto=assunto_list,
    )


async def parse_pagination(
    page: int = Query(1, ge=1, description="Página atual"),
    page_size: int = Query(25, ge=1, le=100, description="Itens por página"),
    sort_by: str | None = Query(None, description="Coluna para ordenar"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="Direção da ordenação"),
    search: str | None = Query(None, description="Busca textual"),
) -> PaginationParams:
    """Extrai parâmetros de paginação dos query params."""
    return PaginationParams(
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
        search=search,
    )


def get_db() -> AsyncSession:
    """Alias para get_session para uso nos routers."""
    return Depends(get_session)


async def verify_admin(authorization: str = Header(...)) -> bool:
    """Valida o token de administrador no header Authorization.

    Raises:
        HTTPException: Se o token for inválido ou ausente.
    """
    token = authorization.replace("Bearer ", "").strip()
    if not AdminAuthService.verify_token(token):
        raise HTTPException(status_code=401, detail="Token inválido ou expirado.")
    return True
