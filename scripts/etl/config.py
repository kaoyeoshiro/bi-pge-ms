"""Configurações do ETL lidas do .env e constantes operacionais."""

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


# Raiz do projeto (3 níveis acima: scripts/etl/config.py → scripts/etl → scripts → BI)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")


@dataclass(frozen=True)
class OracleConfig:
    """Configuração de conexão com o banco Oracle."""

    host: str = field(default_factory=lambda: os.getenv("DB_ORACLE_HOST", "10.2.12.215"))
    port: int = field(default_factory=lambda: int(os.getenv("DB_ORACLE_PORT", "1521")))
    sid: str = field(default_factory=lambda: os.getenv("DB_ORACLE_SID", "SPJMS"))
    user: str = field(default_factory=lambda: os.getenv("DB_ORACLE_USER", ""))
    password: str = field(default_factory=lambda: os.getenv("DB_ORACLE_PASSWORD", ""))

    @property
    def dsn(self) -> str:
        """DSN para conexão via oracledb (thin mode, via túnel → localhost)."""
        return f"localhost:{self.port}/{self.sid}"


@dataclass(frozen=True)
class PostgresConfig:
    """Configuração de conexão com o banco PostgreSQL."""

    host: str = field(default_factory=lambda: os.getenv("DB_HOST", "localhost"))
    port: int = field(default_factory=lambda: int(os.getenv("DB_PORT", "5432")))
    user: str = field(default_factory=lambda: os.getenv("DB_USER", "postgres"))
    password: str = field(default_factory=lambda: os.getenv("DB_PASSWORD", ""))
    dbname: str = field(default_factory=lambda: os.getenv("DB_NAME", "pge_bi"))


@dataclass(frozen=True)
class TunnelConfig:
    """Configuração do túnel SSH para acesso ao Oracle."""

    ssh_host: str = field(default_factory=lambda: os.getenv("RDP_HOST", "10.21.9.206"))
    ssh_user: str = field(default_factory=lambda: os.getenv("RDP_USER", "rcosta@PGE.ms"))
    oracle_host: str = field(default_factory=lambda: os.getenv("DB_ORACLE_HOST", "10.2.12.215"))
    oracle_port: int = field(default_factory=lambda: int(os.getenv("DB_ORACLE_PORT", "1521")))
    ssh_exe: str = r"C:\Program Files\Git\usr\bin\ssh.exe"
    vpn_name: str = "VPN-PGE"


# ── Constantes operacionais ──────────────────────────────────────────

BATCH_SIZE = 5000
SLIDING_WINDOW_DAYS = 30
START_DATE = "2021-01-01"

ETL_TABLES = [
    "processos_novos",
    "pecas_elaboradas",
    "pecas_finalizadas",
    "pendencias",
]

LOG_DIR = PROJECT_ROOT / "scripts" / "logs"
