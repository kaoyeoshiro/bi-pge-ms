"""Script único para atualização diária: Oracle → PG local → Railway.

Executa o pipeline completo em duas etapas:
  1. ETL Oracle → PostgreSQL local (incremental, últimos 30 dias)
  2. Sincronização PG local → Railway (produção)

Uso:
  python etl_diario.py                # Completo: ETL + sync Railway
  python etl_diario.py --etl-only     # Só ETL Oracle → PG local
  python etl_diario.py --sync-only    # Só sync PG local → Railway
  python etl_diario.py --full         # ETL full (desde 2021) + sync
  python etl_diario.py --no-assuntos  # Pula assuntos em ambas as etapas
  python etl_diario.py --tables processos_novos pecas_finalizadas

Requer:
  - VPN conectada (ou credenciais VPN_USER/VPN_PASSWORD no .env)
  - Oracle Instant Client em C:\\oracle\\instantclient_21_20
  - Binários PostgreSQL em E:\\Projetos\\PostgreSQL\\bin\\
  - Variáveis no .env: DB_ORACLE_*, VPN_*, DB_*, DB_PRODUCAO
"""

import argparse
import logging
import os
import sys
import time
from datetime import date, timedelta
from pathlib import Path

# Garante que o pacote etl é encontrado independente do CWD
sys.path.insert(0, str(Path(__file__).resolve().parent))

from etl.config import (
    ETL_TABLES,
    LOG_DIR,
    SLIDING_WINDOW_DAYS,
    START_DATE,
    OracleConfig,
    PostgresConfig,
    TunnelConfig,
)
from etl.extractor import OracleExtractor
from etl.loader import PostgresLoader
from etl.railway_sync import RailwaySync
from etl.tunnel import OracleTunnel


def _setup_logging() -> None:
    """Configura logging para console e arquivo diário."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOG_DIR / f"etl_diario_{date.today().isoformat()}.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_file, encoding="utf-8"),
        ],
    )


def _parse_args() -> argparse.Namespace:
    """Analisa argumentos da linha de comando."""
    parser = argparse.ArgumentParser(
        description="ETL diário: Oracle → PG local → Railway",
    )

    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--etl-only",
        action="store_true",
        help="Só executa ETL Oracle → PG local (não sincroniza com Railway)",
    )
    mode.add_argument(
        "--sync-only",
        action="store_true",
        help="Só sincroniza PG local → Railway (pula ETL Oracle)",
    )

    parser.add_argument(
        "--full",
        action="store_true",
        help=f"ETL completo desde {START_DATE} (padrão: últimos {SLIDING_WINDOW_DAYS} dias)",
    )
    parser.add_argument(
        "--no-assuntos",
        action="store_true",
        help="Pula assuntos em ambas as etapas",
    )
    parser.add_argument(
        "--tables",
        nargs="+",
        choices=ETL_TABLES,
        default=ETL_TABLES,
        help="Tabelas a processar no ETL (padrão: todas)",
    )

    return parser.parse_args()


# ── Etapa 1: ETL Oracle → PG local ───────────────────────────────────


def _run_etl(args: argparse.Namespace) -> None:
    """Extrai dados do Oracle e carrega no PostgreSQL local."""
    logger = logging.getLogger("etl_oracle")

    # Janela temporal
    end_date = date.today()
    if args.full:
        start_date = date.fromisoformat(START_DATE)
        logger.info("Modo FULL: %s até %s", start_date, end_date)
    else:
        start_date = end_date - timedelta(days=SLIDING_WINDOW_DAYS)
        logger.info(
            "Modo INCREMENTAL: %s até %s (%d dias)",
            start_date, end_date, SLIDING_WINDOW_DAYS,
        )

    # Componentes
    extractor = OracleExtractor(OracleConfig())
    loader = PostgresLoader(PostgresConfig())

    try:
        loader.connect()
        loader.ensure_schema()

        with OracleTunnel(TunnelConfig()):
            extractor.connect()

            # Tabelas principais
            for table in args.tables:
                logger.info("=" * 60)
                logger.info("Processando: %s", table)

                total = 0
                for batch in extractor.extract_table(table, start_date, end_date):
                    total += loader.upsert_batch(table, batch)

                pg_count = loader.get_table_count(table)
                pk_count = loader.get_oracle_pk_count(table)
                logger.info(
                    "  %s: %d upserted | PG total: %d | Com PK Oracle: %d",
                    table, total, pg_count, pk_count,
                )

            # Assuntos
            if not args.no_assuntos:
                logger.info("=" * 60)
                logger.info("Processando: assuntos")

                assuntos = extractor.extract_assuntos()
                loader.upsert_assuntos(assuntos)

                logger.info("Processando: vínculos processo-assunto")
                total_vinculos = 0
                for batch in extractor.extract_processo_assuntos(start_date, end_date):
                    total_vinculos += loader.upsert_processo_assuntos(batch)
                logger.info("  %d vínculos processados.", total_vinculos)

            extractor.close()

    finally:
        loader.close()


# ── Etapa 2: Sync PG local → Railway ─────────────────────────────────


def _run_sync(include_assuntos: bool) -> None:
    """Sincroniza PostgreSQL local → Railway (produção)."""
    railway_url = os.getenv("DB_PRODUCAO", "")
    if not railway_url:
        raise RuntimeError(
            "Variável DB_PRODUCAO não encontrada no .env. "
            "Defina a URL de conexão do Railway (postgresql://...)."
        )

    sync = RailwaySync(PostgresConfig(), railway_url)
    sync.sync_all(include_assuntos=include_assuntos)


# ── Pipeline principal ────────────────────────────────────────────────


def main() -> None:
    """Pipeline diário completo: Oracle → PG local → Railway."""
    _setup_logging()
    logger = logging.getLogger(__name__)
    args = _parse_args()

    start_time = time.monotonic()
    logger.info("=" * 60)
    logger.info("ETL DIÁRIO — BI PGE-MS")
    logger.info("=" * 60)

    try:
        # Etapa 1: ETL Oracle → PG local
        if not args.sync_only:
            logger.info("")
            logger.info(">>> ETAPA 1: ETL Oracle → PostgreSQL local")
            _run_etl(args)
            logger.info(">>> ETL concluído.")
        else:
            logger.info(">>> ETL Oracle pulado (--sync-only).")

        # Etapa 2: Sync PG local → Railway
        if not args.etl_only:
            logger.info("")
            logger.info(">>> ETAPA 2: Sincronização PG local → Railway")
            _run_sync(include_assuntos=not args.no_assuntos)
            logger.info(">>> Sincronização concluída.")
        else:
            logger.info(">>> Sincronização Railway pulada (--etl-only).")

    except Exception:
        logger.exception("ERRO no pipeline diário")
        sys.exit(1)

    elapsed = time.monotonic() - start_time
    minutes, seconds = divmod(int(elapsed), 60)
    logger.info("")
    logger.info("=" * 60)
    logger.info("CONCLUÍDO em %dm%02ds.", minutes, seconds)
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
