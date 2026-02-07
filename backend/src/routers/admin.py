"""Endpoints administrativos para gestão de roles e importação de dados."""

import logging

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_session
from src.dependencies import verify_admin
from src.domain.schemas import (
    HiddenProcuradorCreate,
    HiddenProcuradorResponse,
    HiddenProcuradorUpdate,
)
from src.services.admin_service import (
    AdminAuthService,
    ExcelImportService,
    HiddenProducaoService,
    LotacaoService,
    TableStatsService,
    UserRoleService,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["admin"])


# --- Schemas de request/response ---

class LoginRequest(BaseModel):
    """Corpo da requisição de login."""
    password: str


class LoginResponse(BaseModel):
    """Resposta do login com token."""
    token: str


class RoleUpdateRequest(BaseModel):
    """Corpo da requisição de atualização de role."""
    role: str


class UserRoleItem(BaseModel):
    """Item de usuário com role para atualização em lote."""
    name: str
    role: str


class BulkRoleUpdateRequest(BaseModel):
    """Corpo da requisição de atualização em lote."""
    users: list[UserRoleItem]


class CargaReduzidaRequest(BaseModel):
    """Corpo da requisição de toggle carga reduzida."""
    carga_reduzida: bool


class LotacaoUpdateRequest(BaseModel):
    """Corpo da requisição de atualização de lotação."""
    chefias: list[str]


# --- Endpoints ---

@router.post("/login", response_model=LoginResponse)
async def admin_login(body: LoginRequest):
    """Autentica o administrador com senha fixa."""
    if not AdminAuthService.verify_password(body.password):
        raise HTTPException(status_code=401, detail="Senha incorreta.")
    token = AdminAuthService.generate_token()
    return LoginResponse(token=token)


@router.get("/users")
async def list_users(
    search: str | None = None,
    role: str | None = None,
    session: AsyncSession = Depends(get_session),
    _: bool = Depends(verify_admin),
):
    """Lista todos os usuários com seus roles, com filtro opcional por tipo."""
    if role and role not in ("procurador", "assessor"):
        raise HTTPException(status_code=400, detail="Role inválido. Use 'procurador' ou 'assessor'.")
    service = UserRoleService(session)
    users = await service.get_all_users(search, role)
    counts = await service.get_role_counts()
    return {"users": users, "counts": counts}


@router.put("/users/{name}/role")
async def update_user_role(
    name: str,
    body: RoleUpdateRequest,
    session: AsyncSession = Depends(get_session),
    _: bool = Depends(verify_admin),
):
    """Atualiza o role de um usuário específico."""
    if body.role not in ("procurador", "assessor"):
        raise HTTPException(status_code=400, detail="Role inválido. Use 'procurador' ou 'assessor'.")
    service = UserRoleService(session)
    result = await service.update_role(name, body.role)
    return result


@router.put("/users/bulk")
async def update_user_roles_bulk(
    body: BulkRoleUpdateRequest,
    session: AsyncSession = Depends(get_session),
    _: bool = Depends(verify_admin),
):
    """Atualiza roles de múltiplos usuários em lote."""
    for user in body.users:
        if user.role not in ("procurador", "assessor"):
            raise HTTPException(
                status_code=400,
                detail=f"Role inválido para '{user.name}': '{user.role}'",
            )
    service = UserRoleService(session)
    count = await service.update_roles_bulk(
        [u.model_dump() for u in body.users]
    )
    return {"atualizados": count}


@router.put("/users/{name}/carga-reduzida")
async def update_carga_reduzida(
    name: str,
    body: CargaReduzidaRequest,
    session: AsyncSession = Depends(get_session),
    _: bool = Depends(verify_admin),
):
    """Atualiza flag de carga reduzida de um usuário."""
    service = UserRoleService(session)
    return await service.update_carga_reduzida(name, body.carga_reduzida)


@router.get("/lotacoes")
async def list_lotacoes(
    search: str | None = None,
    session: AsyncSession = Depends(get_session),
    _: bool = Depends(verify_admin),
):
    """Lista lotações agrupadas por procurador."""
    service = LotacaoService(session)
    return await service.get_all_lotacoes(search)


@router.put("/lotacoes/{name}")
async def update_lotacao(
    name: str,
    body: LotacaoUpdateRequest,
    session: AsyncSession = Depends(get_session),
    _: bool = Depends(verify_admin),
):
    """Define as chefias de um procurador."""
    service = LotacaoService(session)
    return await service.set_lotacoes(name, body.chefias)


@router.get("/chefias-disponiveis")
async def list_chefias_disponiveis(
    session: AsyncSession = Depends(get_session),
    _: bool = Depends(verify_admin),
):
    """Lista chefias distintas normalizadas disponíveis."""
    service = LotacaoService(session)
    return await service.get_chefias_disponiveis()


@router.post("/populate-roles")
async def populate_roles(
    session: AsyncSession = Depends(get_session),
    _: bool = Depends(verify_admin),
):
    """Popula a tabela user_roles com nomes extraídos dos dados existentes."""
    service = UserRoleService(session)
    result = await service.populate_initial_roles()
    return result


@router.post("/upload")
async def upload_excel(
    file: UploadFile = File(...),
    tabela: str = Form(...),
    modo: str = Form(...),
    session: AsyncSession = Depends(get_session),
    _: bool = Depends(verify_admin),
):
    """Importa arquivo Excel para uma tabela do BI."""
    # Validações
    if tabela not in ("processos_novos", "pecas_elaboradas", "pendencias", "pecas_finalizadas"):
        raise HTTPException(status_code=400, detail=f"Tabela inválida: {tabela}")
    if modo not in ("substituir", "adicionar"):
        raise HTTPException(status_code=400, detail=f"Modo inválido: {modo}")
    if not file.filename or not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Arquivo deve ser .xlsx ou .xls")

    content = await file.read()
    service = ExcelImportService(session)

    try:
        result = await service.import_excel(content, tabela, modo)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Erro ao importar Excel para {tabela}")
        raise HTTPException(status_code=500, detail=f"Erro na importação: {str(e)}")

    return result


@router.get("/tables/stats")
async def table_stats(
    session: AsyncSession = Depends(get_session),
    _: bool = Depends(verify_admin),
):
    """Retorna contagem de linhas de cada tabela."""
    service = TableStatsService(session)
    return await service.get_stats()


# --- Endpoints de Ocultação de Produção ---


@router.get(
    "/hidden-producao",
    response_model=list[HiddenProcuradorResponse],
)
async def list_hidden_rules(
    only_active: bool = True,
    session: AsyncSession = Depends(get_session),
    _: bool = Depends(verify_admin),
):
    """Lista regras de ocultação de produção."""
    service = HiddenProducaoService(session)
    return await service.list_rules(only_active)


@router.post(
    "/hidden-producao",
    response_model=HiddenProcuradorResponse,
    status_code=201,
)
async def create_hidden_rule(
    body: HiddenProcuradorCreate,
    session: AsyncSession = Depends(get_session),
    _: bool = Depends(verify_admin),
):
    """Cria nova regra de ocultação de produção."""
    service = HiddenProducaoService(session)
    try:
        return await service.create_rule(body)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put(
    "/hidden-producao/{rule_id}",
    response_model=HiddenProcuradorResponse,
)
async def update_hidden_rule(
    rule_id: int,
    body: HiddenProcuradorUpdate,
    session: AsyncSession = Depends(get_session),
    _: bool = Depends(verify_admin),
):
    """Atualiza regra de ocultação de produção."""
    service = HiddenProducaoService(session)
    try:
        return await service.update_rule(rule_id, body)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/hidden-producao/{rule_id}", status_code=204)
async def delete_hidden_rule(
    rule_id: int,
    session: AsyncSession = Depends(get_session),
    _: bool = Depends(verify_admin),
):
    """Remove regra de ocultação de produção."""
    service = HiddenProducaoService(session)
    try:
        await service.delete_rule(rule_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
