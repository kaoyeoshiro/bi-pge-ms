"""Aplicação FastAPI principal do BI PGE-MS."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from sqlalchemy import text

from src.config import settings
from src.database import engine
from src.routers import (
    admin,
    comparativos,
    dashboard,
    explorer,
    export,
    filters,
    pendencias,
    perfil,
    processos,
    producao,
)

# Diretório dos arquivos estáticos do frontend (gerados pelo Vite build)
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerencia o ciclo de vida da aplicação."""
    logger.info("BI PGE-MS iniciando...")
    # Criar/migrar tabelas auxiliares
    async with engine.begin() as conn:
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS user_roles (
                id SERIAL PRIMARY KEY,
                name VARCHAR(300) UNIQUE NOT NULL,
                role VARCHAR(20) NOT NULL CHECK (role IN ('procurador', 'assessor')),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """))
        # Migração: coluna carga_reduzida em user_roles
        await conn.execute(text("""
            ALTER TABLE user_roles
            ADD COLUMN IF NOT EXISTS carga_reduzida BOOLEAN DEFAULT FALSE
        """))
        # Tabela de lotação de procuradores em chefias
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS procurador_lotacoes (
                id SERIAL PRIMARY KEY,
                procurador VARCHAR(300) NOT NULL,
                chefia VARCHAR(200) NOT NULL,
                updated_at TIMESTAMP DEFAULT NOW(),
                UNIQUE(procurador, chefia)
            )
        """))
        # Tabela de ocultação temporária de produção
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS admin_hidden_procurador_producao (
                id SERIAL PRIMARY KEY,
                procurador_name VARCHAR(300) NOT NULL,
                chefia VARCHAR(200),
                start_date DATE NOT NULL,
                end_date DATE NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                reason TEXT,
                created_by VARCHAR(100) NOT NULL DEFAULT 'admin',
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP,
                CONSTRAINT ck_start_before_end CHECK (start_date <= end_date)
            )
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_hidden_proc_active
            ON admin_hidden_procurador_producao(procurador_name, chefia, is_active)
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_hidden_dates_active
            ON admin_hidden_procurador_producao(chefia, start_date, end_date, is_active)
        """))
    logger.info("Tabelas auxiliares verificadas.")
    yield
    await engine.dispose()
    logger.info("BI PGE-MS encerrado.")


app = FastAPI(
    title="BI PGE-MS",
    description="Dashboard de Business Intelligence da PGE-MS",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(admin.router)
app.include_router(filters.router)
app.include_router(dashboard.router)
app.include_router(producao.router)
app.include_router(pendencias.router)
app.include_router(processos.router)
app.include_router(comparativos.router)
app.include_router(perfil.router)
app.include_router(explorer.router)
app.include_router(export.router)


@app.get("/api/health")
async def health_check():
    """Endpoint de verificação de saúde da API."""
    return {"status": "ok", "service": "bi-pge-ms"}


# --- Frontend estático (produção) ---
if STATIC_DIR.exists() and (STATIC_DIR / "index.html").exists():
    logger.info("Frontend estático detectado em %s — servindo SPA.", STATIC_DIR)
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(request: Request, full_path: str):
        """Serve arquivos estáticos ou o index.html para rotas SPA."""
        file_path = STATIC_DIR / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(STATIC_DIR / "index.html")
else:
    logger.info("Frontend estático não encontrado — apenas API disponível.")
