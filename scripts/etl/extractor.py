"""Extração de dados do Oracle SAJ/SPJMS via oracledb (thick mode).

Requer Oracle Instant Client instalado — ver scripts/SETUP-ETL.md.
"""

import logging
from collections.abc import Generator
from datetime import date
from pathlib import Path

import oracledb

from .config import BATCH_SIZE, OracleConfig
from .oracle_queries import (
    ASSUNTOS,
    DISCOVER_CHEFIAS,
    PROCESSO_ASSUNTOS,
    TABLE_QUERIES,
)

logger = logging.getLogger(__name__)

# Caminho do Oracle Instant Client (necessário para thick mode com Oracle 11g)
INSTANT_CLIENT_DIR = Path(r"C:\oracle\instantclient_21_20")


def _init_thick_mode() -> None:
    """Inicializa o oracledb em thick mode (necessário para Oracle 11g)."""
    lib_dir = str(INSTANT_CLIENT_DIR) if INSTANT_CLIENT_DIR.exists() else None
    try:
        oracledb.init_oracle_client(lib_dir=lib_dir)
        logger.info("oracledb inicializado em thick mode (lib_dir=%s).", lib_dir)
    except oracledb.exceptions.ProgrammingError:
        # Já inicializado — ignorar
            pass


class OracleExtractor:
    """Conecta ao Oracle via thick mode e extrai dados em batches.

    O Oracle deve estar acessível em localhost (via túnel SSH).
    Requer Oracle Instant Client instalado para thick mode (Oracle 11g).
    """

    def __init__(self, config: OracleConfig) -> None:
        self._config = config
        self._conn = None

    def connect(self) -> None:
        """Abre conexão com o Oracle em thick mode."""
        _init_thick_mode()
        logger.info("Conectando ao Oracle em %s...", self._config.dsn)
        self._conn = oracledb.connect(
            user=self._config.user,
            password=self._config.password,
            dsn=self._config.dsn,
        )
        logger.info("Conectado ao Oracle (thick mode).")

    def close(self) -> None:
        """Fecha conexão com o Oracle."""
        if self._conn:
            self._conn.close()
            self._conn = None
            logger.info("Conexao Oracle encerrada.")

    def _ensure_connected(self) -> oracledb.Connection:
        """Garante que a conexão está ativa."""
        if self._conn is None:
            raise RuntimeError("Extrator Oracle nao conectado. Chame connect() primeiro.")
        return self._conn

    def extract_table(
        self,
        table: str,
        start_date: date,
        end_date: date,
    ) -> Generator[list[dict], None, None]:
        """Extrai dados de uma tabela Oracle em batches.

        Args:
            table: Nome da tabela BI (processos_novos, etc.).
            start_date: Data mínima para filtro (inclusive).
            end_date: Data máxima para filtro (exclusive — dados até end_date - 1).

        Yields:
            Lista de dicts representando um batch de registros.
        """
        conn = self._ensure_connected()
        query = TABLE_QUERIES.get(table)
        if not query:
            raise ValueError(f"Tabela nao suportada: {table}")

        logger.info("Extraindo '%s' (%s ate %s)...", table, start_date, end_date)
        cursor = conn.cursor()
        cursor.arraysize = BATCH_SIZE

        cursor.execute(query, start_date=start_date, end_date=end_date)
        columns = [col[0].lower() for col in cursor.description]

        total = 0
        while True:
            rows = cursor.fetchmany(BATCH_SIZE)
            if not rows:
                break
            batch = [dict(zip(columns, row)) for row in rows]
            total += len(batch)
            yield batch

        cursor.close()
        logger.info("  '%s': %d registros extraidos.", table, total)

    def extract_assuntos(self) -> list[dict]:
        """Extrai árvore completa de assuntos do Oracle."""
        conn = self._ensure_connected()
        logger.info("Extraindo arvore de assuntos...")

        cursor = conn.cursor()
        cursor.execute(ASSUNTOS)
        columns = [col[0].lower() for col in cursor.description]
        rows = cursor.fetchall()
        cursor.close()

        result = [dict(zip(columns, row)) for row in rows]
        logger.info("  %d assuntos extraidos.", len(result))
        return result

    def extract_processo_assuntos(
        self,
        start_date: date,
        end_date: date,
    ) -> Generator[list[dict], None, None]:
        """Extrai vínculos processo-assunto em batches.

        Args:
            start_date: Data mínima de distribuição dos processos (inclusive).
            end_date: Data máxima de distribuição (exclusive).

        Yields:
            Lista de dicts representando um batch de vínculos.
        """
        conn = self._ensure_connected()
        logger.info("Extraindo vinculos processo-assunto (%s ate %s)...", start_date, end_date)

        cursor = conn.cursor()
        cursor.arraysize = BATCH_SIZE
        cursor.execute(PROCESSO_ASSUNTOS, start_date=start_date, end_date=end_date)
        columns = [col[0].lower() for col in cursor.description]

        total = 0
        while True:
            rows = cursor.fetchmany(BATCH_SIZE)
            if not rows:
                break
            batch = [dict(zip(columns, row)) for row in rows]
            total += len(batch)
            yield batch

        cursor.close()
        logger.info("  %d vinculos processo-assunto extraidos.", total)

    def discover_chefias(self) -> list[str]:
        """Lista chefias distintas no Oracle para verificação/mapeamento."""
        conn = self._ensure_connected()
        logger.info("Consultando chefias distintas no Oracle...")

        cursor = conn.cursor()
        cursor.execute(DISCOVER_CHEFIAS)
        chefias = [row[0] for row in cursor.fetchall()]
        cursor.close()

        logger.info("  %d chefias encontradas.", len(chefias))
        return chefias

    def count_table(self, table: str, start_date: date, end_date: date) -> int:
        """Conta registros no Oracle para uma tabela (verificação)."""
        conn = self._ensure_connected()
        query = TABLE_QUERIES.get(table)
        if not query:
            raise ValueError(f"Tabela nao suportada: {table}")

        count_query = f"SELECT COUNT(*) FROM ({query})"
        cursor = conn.cursor()
        cursor.execute(count_query, start_date=start_date, end_date=end_date)
        count = cursor.fetchone()[0]
        cursor.close()
        return count
