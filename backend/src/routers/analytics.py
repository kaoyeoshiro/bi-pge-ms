"""Endpoints para analytics e métricas de uso do sistema."""

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_session
from src.domain.models import AccessLog

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.post("/track-access")
async def track_access(
    request: Request, db: AsyncSession = Depends(get_session)
) -> dict:
    """Registra um novo acesso ao sistema."""
    # Extrai IP e User-Agent do request
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    # Cria novo registro
    new_log = AccessLog(ip_address=ip_address, user_agent=user_agent)
    db.add(new_log)
    await db.commit()

    # Retorna total de acessos
    total_result = await db.execute(select(func.count()).select_from(AccessLog))
    total = total_result.scalar() or 0

    return {"success": True, "total_accesses": total}


@router.get("/access-count")
async def get_access_count(db: AsyncSession = Depends(get_session)) -> dict:
    """Retorna o total de acessos registrados."""
    result = await db.execute(select(func.count()).select_from(AccessLog))
    total = result.scalar() or 0
    return {"total_accesses": total}
