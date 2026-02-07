"""Repositório para a tabela processos_novos."""

from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.models import ProcessoNovo
from src.repositories.base_repository import BaseRepository


class ProcessosRepository(BaseRepository):
    """Operações sobre processos novos."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, ProcessoNovo)
