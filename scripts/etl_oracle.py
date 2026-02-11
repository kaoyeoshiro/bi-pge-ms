"""ETL Oracle → PostgreSQL para o BI PGE-MS.

Extrai dados do Oracle SAJ/SPJMS via túnel SSH e carrega no PostgreSQL
local com upsert (ON CONFLICT) para carga incremental.

Uso:
    # Carga incremental (últimos 30 dias)
    python scripts/etl_oracle.py

    # Carga completa desde o início
    python scripts/etl_oracle.py --full

    # Somente assuntos
    python scripts/etl_oracle.py --assuntos

    # Tabela específica
    python scripts/etl_oracle.py --tables processos_novos pecas_finalizadas

Requer:
    - VPN conectada (ou credenciais VPN_USER/VPN_PASSWORD no .env)
    - Oracle Instant Client em C:\\oracle\\instantclient_21_20
    - Variáveis Oracle no .env (DB_ORACLE_USER, DB_ORACLE_PASSWORD)
"""

import argparse
import logging
import sys
from datetime import date, timedelta

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
from etl.tunnel import OracleTunnel


def _setup_logging() -> None:
    """Configura logging para console e arquivo."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOG_DIR / f"etl_{date.today().isoformat()}.log"

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
    parser = argparse.ArgumentParser(description="ETL Oracle → PostgreSQL para BI PGE-MS")
    parser.add_argument(
        "--full",
        action="store_true",
        help=f"Carga completa desde {START_DATE} (padrão: últimos {SLIDING_WINDOW_DAYS} dias)",
    )
    parser.add_argument(
        "--tables",
        nargs="+",
        choices=ETL_TABLES,
        default=ETL_TABLES,
        help="Tabelas a processar (padrão: todas)",
    )
    parser.add_argument(
        "--assuntos",
        action="store_true",
        help="Extrair e carregar árvore de assuntos e vínculos processo-assunto",
    )
    return parser.parse_args()


def main() -> None:
    """Executa o pipeline ETL Oracle → PostgreSQL."""
    _setup_logging()
    logger = logging.getLogger(__name__)
    args = _parse_args()

    # Define janela temporal
    end_date = date.today()
    if args.full:
        start_date = date.fromisoformat(START_DATE)
        logger.info("Modo FULL: %s até %s", start_date, end_date)
    else:
        start_date = end_date - timedelta(days=SLIDING_WINDOW_DAYS)
        logger.info("Modo INCREMENTAL: %s até %s (%d dias)", start_date, end_date, SLIDING_WINDOW_DAYS)

    # Configura componentes
    oracle_config = OracleConfig()
    pg_config = PostgresConfig()
    tunnel_config = TunnelConfig()

    extractor = OracleExtractor(oracle_config)
    loader = PostgresLoader(pg_config)

    try:
        # Conecta ao PostgreSQL e aplica migrações
        loader.connect()
        loader.ensure_schema()

        # Abre túnel SSH e conecta ao Oracle
        with OracleTunnel(tunnel_config):
            extractor.connect()

            # Extrai e carrega tabelas
            for table in args.tables:
                logger.info("=" * 60)
                logger.info("Processando: %s", table)

                total = 0
                for batch in extractor.extract_table(table, start_date, end_date):
                    count = loader.upsert_batch(table, batch)
                    total += count

                # Contagens de verificação
                pg_count = loader.get_table_count(table)
                pk_count = loader.get_oracle_pk_count(table)
                logger.info(
                    "  %s: %d upserted | PG total: %d | Com PK Oracle: %d",
                    table, total, pg_count, pk_count,
                )

            # Assuntos (se solicitado)
            if args.assuntos:
                logger.info("=" * 60)
                logger.info("Processando: assuntos")

                assuntos = extractor.extract_assuntos()
                loader.upsert_assuntos(assuntos)

                logger.info("Processando: vínculos processo-assunto")
                total_vinculos = 0
                for batch in extractor.extract_processo_assuntos(start_date, end_date):
                    count = loader.upsert_processo_assuntos(batch)
                    total_vinculos += count
                logger.info("  %d vínculos processo-assunto processados.", total_vinculos)

            extractor.close()

    except Exception:
        logger.exception("Erro no ETL")
        raise
    finally:
        loader.close()

    logger.info("=" * 60)
    logger.info("ETL concluído com sucesso.")


if __name__ == "__main__":
    main()
