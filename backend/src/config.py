"""Configuração da aplicação via variáveis de ambiente."""

from pathlib import Path

from pydantic_settings import BaseSettings


def _find_env_file() -> str | None:
    """Procura .env na raiz do projeto (desenvolvimento local)."""
    candidates = [
        Path(__file__).resolve().parent.parent.parent / ".env",  # backend/../.env
        Path(__file__).resolve().parent.parent.parent.parent / ".env",  # Docker context
    ]
    for path in candidates:
        if path.exists():
            return str(path)
    return None


class Settings(BaseSettings):
    """Configurações carregadas do .env ou variáveis de ambiente."""

    # Conexão individual (desenvolvimento local)
    db_host: str = "localhost"
    db_port: int = 5432
    db_user: str = "postgres"
    db_password: str = ""
    db_name: str = "pge_bi"

    # URL direta (Railway fornece automaticamente)
    database_url: str | None = None

    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]
    admin_password: str = "changeme"

    @property
    def async_database_url(self) -> str:
        """URL de conexão async para PostgreSQL."""
        if self.database_url:
            url = self.database_url
            # Railway fornece postgresql://, asyncpg precisa de postgresql+asyncpg://
            if url.startswith("postgresql://"):
                url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
            return url
        return (
            f"postgresql+asyncpg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    model_config = {
        "env_file": _find_env_file(),
        "env_file_encoding": "utf-8",
    }


settings = Settings()
