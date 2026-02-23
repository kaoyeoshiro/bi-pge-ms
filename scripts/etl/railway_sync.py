"""Sincronização do PostgreSQL local → Railway (produção) via pg_dump/pg_restore.

Automatiza o pipeline:
  1. Sync de schema (migrações + tabelas auxiliares)
  2. pg_dump das tabelas locais (formato custom, compactado)
  3. pg_restore atômico com --single-transaction --clean
  4. Verificação de contagens

O uso de --single-transaction garante que o TRUNCATE + COPY ocorre em uma
única transação. Se falhar, faz rollback e os dados originais são preservados.
Isso elimina o cenário de tabelas vazias/bloqueadas que derrubava o app.
"""

import logging
import os
import subprocess
import tempfile
import time
from pathlib import Path

from .config import PostgresConfig
from .loader import SCHEMA_MIGRATIONS

logger = logging.getLogger(__name__)

# Binários PostgreSQL (configurável via PG_BIN_DIR no .env)
PG_BIN_DIR = Path(os.getenv("PG_BIN_DIR", r"E:\Projetos\PostgreSQL\bin"))

# ── Tabelas por grupo ─────────────────────────────────────────────────

MAIN_TABLES = [
    "processos_novos",
    "pecas_elaboradas",
    "pecas_finalizadas",
    "pendencias",
]
ASSUNTOS_TABLES = ["assuntos", "processo_assuntos"]
PARTES_TABLES = ["partes_processo", "partes_normalizadas"]

ALL_TABLES = MAIN_TABLES + ASSUNTOS_TABLES + PARTES_TABLES

# ── Timeouts em segundos ──────────────────────────────────────────────

DUMP_TIMEOUT = 1800     # 30 min (dump local)
RESTORE_TIMEOUT = 3600  # 60 min (restore via internet)
PSQL_TIMEOUT = 300      # 5 min (comandos SQL avulsos)

# ── Retry ─────────────────────────────────────────────────────────────

MAX_RETRIES = 3
RETRY_BASE_DELAY = 30  # segundos (backoff: 30s, 60s, 120s)

# ── DDL para tabelas de partes (idempotente) ──────────────────────────

PARTES_SCHEMA_DDL = [
    # partes_processo
    """
    CREATE TABLE IF NOT EXISTS partes_processo (
        cd_processo     VARCHAR(50)  NOT NULL,
        seq_parte       INTEGER      NOT NULL,
        numero_processo VARCHAR(50),
        numero_formatado VARCHAR(50),
        cd_pessoa       BIGINT,
        nome            TEXT,
        tipo_parte      TEXT,
        polo            INTEGER,
        principal       CHAR(1),
        tipo_pessoa     CHAR(1),
        cd_categ_pessoa INTEGER,
        cpf             VARCHAR(20),
        cnpj            VARCHAR(20),
        rg              VARCHAR(30),
        oab             VARCHAR(30),
        valor_acao      NUMERIC,
        tipo_valor      CHAR(1),
        PRIMARY KEY (cd_processo, seq_parte)
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_partes_numero_processo ON partes_processo (numero_processo);",
    "CREATE INDEX IF NOT EXISTS idx_partes_cd_pessoa ON partes_processo (cd_pessoa);",
    "CREATE INDEX IF NOT EXISTS idx_partes_polo ON partes_processo (polo);",
    "CREATE INDEX IF NOT EXISTS idx_partes_cpf ON partes_processo (cpf) WHERE cpf IS NOT NULL;",
    "CREATE INDEX IF NOT EXISTS idx_partes_cnpj ON partes_processo (cnpj) WHERE cnpj IS NOT NULL;",
    "CREATE INDEX IF NOT EXISTS idx_partes_oab ON partes_processo (oab) WHERE oab IS NOT NULL;",
    "CREATE INDEX IF NOT EXISTS idx_partes_nome ON partes_processo (nome);",
    # partes_normalizadas
    """
    CREATE TABLE IF NOT EXISTS partes_normalizadas (
        id                      SERIAL PRIMARY KEY,
        chave_tipo              VARCHAR(4) NOT NULL,
        chave_valor             TEXT NOT NULL,
        nome                    TEXT NOT NULL,
        cpf                     VARCHAR(20),
        cnpj                    VARCHAR(20),
        oab                     VARCHAR(30),
        tipo_pessoa             CHAR(1),
        qtd_processos           INTEGER DEFAULT 0,
        qtd_contra_estado       INTEGER DEFAULT 0,
        qtd_executado_estado    INTEGER DEFAULT 0,
        qtd_advogado            INTEGER DEFAULT 0,
        qtd_coreu_estado        INTEGER DEFAULT 0,
        valor_total             NUMERIC DEFAULT 0,
        valor_medio             NUMERIC DEFAULT 0,
        UNIQUE (chave_tipo, chave_valor)
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_pn_nome ON partes_normalizadas (nome);",
    "CREATE INDEX IF NOT EXISTS idx_pn_cpf ON partes_normalizadas (cpf) WHERE cpf IS NOT NULL;",
    "CREATE INDEX IF NOT EXISTS idx_pn_cnpj ON partes_normalizadas (cnpj) WHERE cnpj IS NOT NULL;",
    "CREATE INDEX IF NOT EXISTS idx_pn_oab ON partes_normalizadas (oab) WHERE oab IS NOT NULL;",
    "CREATE INDEX IF NOT EXISTS idx_pn_contra ON partes_normalizadas (qtd_contra_estado DESC);",
    "CREATE INDEX IF NOT EXISTS idx_pn_executado ON partes_normalizadas (qtd_executado_estado DESC);",
    "CREATE INDEX IF NOT EXISTS idx_pn_advogado ON partes_normalizadas (qtd_advogado DESC);",
    "CREATE INDEX IF NOT EXISTS idx_pn_coreu ON partes_normalizadas (qtd_coreu_estado DESC);",
    "CREATE INDEX IF NOT EXISTS idx_pn_valor ON partes_normalizadas (valor_total DESC);",
]


class RailwaySync:
    """Sincroniza PostgreSQL local → Railway via pg_dump/pg_restore atômico.

    Args:
        local_config: Configuração do PostgreSQL local.
        railway_url: URL de conexão do Railway (postgresql://...).
    """

    def __init__(self, local_config: PostgresConfig, railway_url: str) -> None:
        self._local = local_config
        self._railway_url = railway_url
        self._pg_dump = str(PG_BIN_DIR / "pg_dump.exe")
        self._pg_restore = str(PG_BIN_DIR / "pg_restore.exe")
        self._psql = str(PG_BIN_DIR / "psql.exe")

    # ── Operações de baixo nível ──────────────────────────────────────

    def _local_env(self) -> dict[str, str]:
        """Variáveis de ambiente com PGPASSWORD para PG local."""
        env = os.environ.copy()
        env["PGPASSWORD"] = self._local.password
        return env

    def _run_pg_dump(self, tables: list[str], output_path: str) -> None:
        """Executa pg_dump das tabelas em formato custom (compactado).

        Args:
            tables: Nomes das tabelas a exportar.
            output_path: Caminho do arquivo de saída (.dump).
        """
        cmd = [
            self._pg_dump,
            "-h", self._local.host,
            "-p", str(self._local.port),
            "-U", self._local.user,
            "-d", self._local.dbname,
            "--data-only", "--no-owner", "--no-privileges",
            "-Fc",
        ]
        for table in tables:
            cmd.extend(["-t", table])
        cmd.extend(["-f", output_path])

        logger.info("pg_dump: %s -> %s", ", ".join(tables), Path(output_path).name)
        result = subprocess.run(
            cmd, env=self._local_env(),
            capture_output=True, text=True, timeout=DUMP_TIMEOUT,
        )
        if result.returncode != 0:
            raise RuntimeError(f"pg_dump falhou (rc={result.returncode}): {result.stderr.strip()}")

        size_mb = Path(output_path).stat().st_size / (1024 * 1024)
        logger.info("pg_dump concluído (%.1f MB).", size_mb)

    def _run_psql_railway(self, sql: str, timeout: int = PSQL_TIMEOUT) -> str:
        """Executa SQL no Railway via psql.

        Args:
            sql: Comando SQL a executar.
            timeout: Timeout em segundos.

        Returns:
            Saída stdout do psql.
        """
        cmd = [self._psql, self._railway_url, "-c", sql, "-v", "ON_ERROR_STOP=1"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if result.returncode != 0:
            raise RuntimeError(f"psql Railway falhou: {result.stderr.strip()}")
        return result.stdout

    def _run_pg_restore(
        self,
        dump_path: str,
        disable_triggers: bool = False,
        single_transaction: bool = True,
    ) -> None:
        """Executa pg_restore no Railway.

        Com --single-transaction, todo o COPY ocorre em uma unica transacao.
        Se falhar, faz rollback (dados parciais nao ficam no banco).

        Nota: --clean e --data-only sao incompativeis no pg_restore.
        O TRUNCATE deve ser feito separadamente antes de chamar este metodo.

        Args:
            dump_path: Caminho do arquivo .dump (formato custom).
            disable_triggers: Se True, desabilita triggers durante restore.
            single_transaction: Se True, usa --single-transaction (padrao).
        """
        cmd = [
            self._pg_restore,
            "-d", self._railway_url,
            "--data-only", "--no-owner", "--no-privileges",
        ]
        if single_transaction:
            cmd.append("--single-transaction")
        if disable_triggers:
            cmd.append("--disable-triggers")
        cmd.append(dump_path)

        suffix_parts = []
        if single_transaction:
            suffix_parts.append("single-transaction")
        if disable_triggers:
            suffix_parts.append("triggers desabilitados")
        suffix = f" ({', '.join(suffix_parts)})" if suffix_parts else ""

        logger.info("pg_restore -> Railway%s...", suffix)
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=RESTORE_TIMEOUT)
        if result.returncode != 0:
            raise RuntimeError(
                f"pg_restore falhou (rc={result.returncode}): {result.stderr.strip()}"
            )
        logger.info("pg_restore concluido.")

    def _run_pg_restore_with_retry(self, dump_path: str, **kwargs) -> None:
        """Executa pg_restore com retry e backoff exponencial.

        Args:
            dump_path: Caminho do arquivo .dump.
            **kwargs: Parâmetros repassados para _run_pg_restore.
        """
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                self._run_pg_restore(dump_path, **kwargs)
                return
            except RuntimeError as e:
                if attempt == MAX_RETRIES:
                    raise
                delay = RETRY_BASE_DELAY * (2 ** (attempt - 1))
                logger.warning(
                    "pg_restore falhou (tentativa %d/%d): %s",
                    attempt, MAX_RETRIES, e,
                )
                logger.info("Aguardando %ds antes de tentar novamente...", delay)
                time.sleep(delay)

    # ── Sync de schema ────────────────────────────────────────────────

    def sync_schema(self) -> None:
        """Aplica migrações de schema no Railway antes do data sync.

        Inclui migrações das tabelas principais (loader.py) e DDL
        das tabelas auxiliares (partes_processo, partes_normalizadas).
        Todas as operações são idempotentes.
        """
        logger.info("Aplicando migrações de schema no Railway...")

        for sql in SCHEMA_MIGRATIONS:
            self._run_psql_railway(sql)

        for ddl in PARTES_SCHEMA_DDL:
            self._run_psql_railway(ddl)

        logger.info("Schema Railway atualizado.")

    # ── Sincronização por grupo de tabelas ────────────────────────────

    def sync_all(
        self,
        include_assuntos: bool = True,
        include_partes: bool = True,
    ) -> None:
        """Sincroniza todas as tabelas para Railway.

        Args:
            include_assuntos: Se False, pula assuntos e processo_assuntos.
            include_partes: Se False, pula partes_processo e partes_normalizadas.
        """
        logger.info("=" * 60)
        logger.info("SYNC: PostgreSQL local -> Railway")

        self.sync_schema()
        self._sync_main_tables()

        if include_assuntos:
            self._sync_assuntos()

        if include_partes:
            self._sync_partes()

        self._verify_counts(include_partes=include_partes)
        logger.info("Sincronização Railway concluída.")

    def _sync_main_tables(self) -> None:
        """Dump, truncate e restore das 4 tabelas principais."""
        dump_path = tempfile.mktemp(suffix=".dump", prefix="etl_main_")
        try:
            self._run_pg_dump(MAIN_TABLES, dump_path)

            tables_csv = ", ".join(MAIN_TABLES)
            logger.info("TRUNCATE %s no Railway...", tables_csv)
            self._run_psql_railway(f"TRUNCATE {tables_csv};")

            self._run_pg_restore_with_retry(dump_path)
        finally:
            _cleanup_file(dump_path)

    def _sync_assuntos(self) -> None:
        """Dump e restore de assuntos + processo_assuntos.

        Desabilita triggers temporariamente para evitar violação de FK
        auto-referencial (assuntos.codigo_pai → assuntos.codigo).
        """
        dump_path = tempfile.mktemp(suffix=".dump", prefix="etl_assuntos_")
        try:
            self._run_pg_dump(ASSUNTOS_TABLES, dump_path)

            logger.info("Desabilitando triggers e truncando assuntos no Railway...")
            self._run_psql_railway(
                "ALTER TABLE assuntos DISABLE TRIGGER ALL; "
                "ALTER TABLE processo_assuntos DISABLE TRIGGER ALL; "
                "TRUNCATE processo_assuntos, assuntos;"
            )

            try:
                self._run_pg_restore_with_retry(
                    dump_path, disable_triggers=True,
                )
            finally:
                logger.info("Reabilitando triggers de assuntos no Railway...")
                self._run_psql_railway(
                    "ALTER TABLE assuntos ENABLE TRIGGER ALL; "
                    "ALTER TABLE processo_assuntos ENABLE TRIGGER ALL;"
                )

        finally:
            _cleanup_file(dump_path)

    def _sync_partes(self) -> None:
        """Dump, truncate e restore de partes_processo + partes_normalizadas."""
        dump_path = tempfile.mktemp(suffix=".dump", prefix="etl_partes_")
        try:
            self._run_pg_dump(PARTES_TABLES, dump_path)

            tables_csv = ", ".join(PARTES_TABLES)
            logger.info("TRUNCATE %s no Railway...", tables_csv)
            self._run_psql_railway(f"TRUNCATE {tables_csv};")

            self._run_pg_restore_with_retry(dump_path)

            # Reajusta a sequence SERIAL de partes_normalizadas
            self._run_psql_railway(
                "SELECT setval('partes_normalizadas_id_seq', "
                "COALESCE(MAX(id), 1)) FROM partes_normalizadas;"
            )
        finally:
            _cleanup_file(dump_path)

    # ── Verificação ───────────────────────────────────────────────────

    def _verify_counts(self, include_partes: bool = True) -> None:
        """Verifica contagens nas tabelas Railway e loga resultado."""
        logger.info("Verificando contagens no Railway...")

        tables = MAIN_TABLES + ASSUNTOS_TABLES
        if include_partes:
            tables += PARTES_TABLES

        sql_parts = [
            f"SELECT '{t}' AS tabela, COUNT(*) AS registros FROM {t}"
            for t in tables
        ]
        sql = " UNION ALL ".join(sql_parts) + " ORDER BY 1;"

        output = self._run_psql_railway(sql)
        logger.info("Contagens Railway:\n%s", output.strip())


def _cleanup_file(path: str) -> None:
    """Remove arquivo temporário se existir."""
    try:
        p = Path(path)
        if p.exists():
            p.unlink()
            logger.info("Temp removido: %s", p.name)
    except OSError as e:
        logger.warning("Falha ao remover temp %s: %s", path, e)
