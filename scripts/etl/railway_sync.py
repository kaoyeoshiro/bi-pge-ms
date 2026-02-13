"""Sincronização do PostgreSQL local → Railway (produção) via pg_dump/pg_restore.

Automatiza o processo manual documentado em scripts/ETL.md:
  1. pg_dump das tabelas locais (formato custom, compactado)
  2. TRUNCATE no Railway
  3. pg_restore no Railway
  4. Verificação de contagens
"""

import logging
import os
import subprocess
import tempfile
from pathlib import Path

from .config import PostgresConfig

logger = logging.getLogger(__name__)

# Binários PostgreSQL (configurável via PG_BIN_DIR no .env)
PG_BIN_DIR = Path(os.getenv("PG_BIN_DIR", r"E:\Projetos\PostgreSQL\bin"))

# Tabelas por grupo (assuntos requerem tratamento especial de FK)
MAIN_TABLES = [
    "processos_novos",
    "pecas_elaboradas",
    "pecas_finalizadas",
    "pendencias",
]
ASSUNTOS_TABLES = ["assuntos", "processo_assuntos"]

# Timeouts em segundos
DUMP_TIMEOUT = 1800     # 30 min (dump local)
RESTORE_TIMEOUT = 3600  # 60 min (restore via internet)
PSQL_TIMEOUT = 300      # 5 min (comandos SQL avulsos)


class RailwaySync:
    """Sincroniza PostgreSQL local → Railway via pg_dump/pg_restore.

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

        logger.info("pg_dump: %s → %s", ", ".join(tables), Path(output_path).name)
        result = subprocess.run(
            cmd, env=self._local_env(),
            capture_output=True, text=True, timeout=DUMP_TIMEOUT,
        )
        if result.returncode != 0:
            raise RuntimeError(f"pg_dump falhou (rc={result.returncode}): {result.stderr.strip()}")

        size_mb = Path(output_path).stat().st_size / (1024 * 1024)
        logger.info("pg_dump concluído (%.1f MB).", size_mb)

    def _run_psql_railway(self, sql: str) -> str:
        """Executa SQL no Railway via psql.

        Args:
            sql: Comando SQL a executar.

        Returns:
            Saída stdout do psql.
        """
        cmd = [self._psql, self._railway_url, "-c", sql, "-v", "ON_ERROR_STOP=1"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=PSQL_TIMEOUT)
        if result.returncode != 0:
            raise RuntimeError(f"psql Railway falhou: {result.stderr.strip()}")
        return result.stdout

    def _run_pg_restore(self, dump_path: str, disable_triggers: bool = False) -> None:
        """Executa pg_restore no Railway.

        Args:
            dump_path: Caminho do arquivo .dump (formato custom).
            disable_triggers: Se True, desabilita triggers durante restore.
        """
        cmd = [
            self._pg_restore,
            "-d", self._railway_url,
            "--data-only", "--no-owner", "--no-privileges",
        ]
        if disable_triggers:
            cmd.append("--disable-triggers")
        cmd.append(dump_path)

        suffix = " (triggers desabilitados)" if disable_triggers else ""
        logger.info("pg_restore → Railway%s...", suffix)
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=RESTORE_TIMEOUT)
        if result.returncode != 0:
            raise RuntimeError(
                f"pg_restore falhou (rc={result.returncode}): {result.stderr.strip()}"
            )
        logger.info("pg_restore concluído.")

    # ── Sincronização por grupo de tabelas ────────────────────────────

    def sync_all(self, include_assuntos: bool = True) -> None:
        """Sincroniza todas as tabelas para Railway.

        Args:
            include_assuntos: Se False, pula assuntos e processo_assuntos.
        """
        logger.info("=" * 60)
        logger.info("SYNC: PostgreSQL local → Railway")

        self._sync_main_tables()

        if include_assuntos:
            self._sync_assuntos()

        self._verify_counts()
        logger.info("Sincronização Railway concluída.")

    def _sync_main_tables(self) -> None:
        """Dump e restore das 4 tabelas principais (sem FK complexa)."""
        dump_path = tempfile.mktemp(suffix=".dump", prefix="etl_main_")
        try:
            # 1. Dump local
            self._run_pg_dump(MAIN_TABLES, dump_path)

            # 2. Truncate no Railway
            tables_csv = ", ".join(MAIN_TABLES)
            logger.info("TRUNCATE %s no Railway...", tables_csv)
            self._run_psql_railway(f"TRUNCATE {tables_csv};")

            # 3. Restore no Railway
            self._run_pg_restore(dump_path)

        finally:
            _cleanup_file(dump_path)

    def _sync_assuntos(self) -> None:
        """Dump e restore de assuntos + processo_assuntos.

        Desabilita triggers temporariamente para evitar violação de FK
        auto-referencial (assuntos.codigo_pai → assuntos.codigo).
        """
        dump_path = tempfile.mktemp(suffix=".dump", prefix="etl_assuntos_")
        try:
            # 1. Dump local
            self._run_pg_dump(ASSUNTOS_TABLES, dump_path)

            # 2. Desabilitar triggers + truncate
            logger.info("Desabilitando triggers e truncando assuntos no Railway...")
            self._run_psql_railway(
                "ALTER TABLE assuntos DISABLE TRIGGER ALL; "
                "ALTER TABLE processo_assuntos DISABLE TRIGGER ALL; "
                "TRUNCATE processo_assuntos, assuntos;"
            )

            # 3. Restore com triggers desabilitados
            self._run_pg_restore(dump_path, disable_triggers=True)

            # 4. Reabilitar triggers
            logger.info("Reabilitando triggers no Railway...")
            self._run_psql_railway(
                "ALTER TABLE assuntos ENABLE TRIGGER ALL; "
                "ALTER TABLE processo_assuntos ENABLE TRIGGER ALL;"
            )

        finally:
            _cleanup_file(dump_path)

    def _verify_counts(self) -> None:
        """Verifica contagens nas tabelas Railway e loga resultado."""
        logger.info("Verificando contagens no Railway...")
        sql = (
            "SELECT 'processos_novos' AS tabela, COUNT(*) AS registros "
            "FROM processos_novos "
            "UNION ALL SELECT 'pecas_elaboradas', COUNT(*) FROM pecas_elaboradas "
            "UNION ALL SELECT 'pecas_finalizadas', COUNT(*) FROM pecas_finalizadas "
            "UNION ALL SELECT 'pendencias', COUNT(*) FROM pendencias "
            "UNION ALL SELECT 'assuntos', COUNT(*) FROM assuntos "
            "UNION ALL SELECT 'processo_assuntos', COUNT(*) FROM processo_assuntos "
            "ORDER BY 1;"
        )
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
