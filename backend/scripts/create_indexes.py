"""Script para criar índices compostos e materialized view no banco."""

import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

COMPOSITE_INDEXES = [
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_pe_data_chefia ON pecas_elaboradas(data, chefia);",
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_pe_data_procurador ON pecas_elaboradas(data, procurador);",
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_pe_data_categoria ON pecas_elaboradas(data, categoria);",
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_pf_data_chefia ON pecas_finalizadas(data_finalizacao, chefia);",
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_pf_data_procurador ON pecas_finalizadas(data_finalizacao, procurador);",
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_pd_data_chefia ON pendencias(data, chefia);",
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_pd_data_area ON pendencias(data, area);",
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_pd_area_catpend ON pendencias(area, categoria_pendencia);",
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_pn_data_chefia ON processos_novos(data, chefia);",
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_pn_data_procurador ON processos_novos(data, procurador);",
]

MATERIALIZED_VIEW = """
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_resumo_mensal AS
WITH periodos AS (
    SELECT DISTINCT periodo FROM (
        SELECT TO_CHAR(data, 'YYYY-MM') AS periodo FROM processos_novos WHERE data IS NOT NULL
        UNION
        SELECT TO_CHAR(data, 'YYYY-MM') FROM pecas_elaboradas WHERE data IS NOT NULL
        UNION
        SELECT TO_CHAR(data_finalizacao, 'YYYY-MM') FROM pecas_finalizadas WHERE data_finalizacao IS NOT NULL
        UNION
        SELECT TO_CHAR(data, 'YYYY-MM') FROM pendencias WHERE data IS NOT NULL
    ) sub
),
pn AS (SELECT TO_CHAR(data, 'YYYY-MM') AS p, COUNT(*) AS c FROM processos_novos WHERE data IS NOT NULL GROUP BY 1),
pe AS (SELECT TO_CHAR(data, 'YYYY-MM') AS p, COUNT(*) AS c FROM pecas_elaboradas WHERE data IS NOT NULL GROUP BY 1),
pf AS (SELECT TO_CHAR(data_finalizacao, 'YYYY-MM') AS p, COUNT(*) AS c FROM pecas_finalizadas WHERE data_finalizacao IS NOT NULL GROUP BY 1),
pd AS (SELECT TO_CHAR(data, 'YYYY-MM') AS p, COUNT(*) AS c FROM pendencias WHERE data IS NOT NULL GROUP BY 1)
SELECT
    periodos.periodo,
    COALESCE(pn.c, 0) AS processos_novos,
    COALESCE(pe.c, 0) AS pecas_elaboradas,
    COALESCE(pf.c, 0) AS pecas_finalizadas,
    COALESCE(pd.c, 0) AS pendencias
FROM periodos
LEFT JOIN pn ON periodos.periodo = pn.p
LEFT JOIN pe ON periodos.periodo = pe.p
LEFT JOIN pf ON periodos.periodo = pf.p
LEFT JOIN pd ON periodos.periodo = pd.p
ORDER BY periodos.periodo;
"""


def main() -> None:
    """Cria índices compostos e materialized view."""
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    user = os.getenv("DB_USER", "postgres")
    password = os.getenv("DB_PASSWORD", "")
    dbname = os.getenv("DB_NAME", "pge_bi")
    conn_str = f"postgresql://{user}:{password}@{host}:{port}/{dbname}"

    engine = create_engine(conn_str, isolation_level="AUTOCOMMIT")

    logger.info("Criando índices compostos...")
    with engine.connect() as conn:
        for idx_sql in COMPOSITE_INDEXES:
            try:
                logger.info(f"  Executando: {idx_sql[:60]}...")
                conn.execute(text(idx_sql))
            except Exception as e:
                logger.warning(f"  Índice já existe ou erro: {e}")

    logger.info("Criando materialized view mv_resumo_mensal...")
    with engine.connect() as conn:
        try:
            conn.execute(text(MATERIALIZED_VIEW))
            logger.info("  Materialized view criada com sucesso.")
        except Exception as e:
            logger.warning(f"  View já existe ou erro: {e}")
            # Tenta refresh se já existe
            try:
                conn.execute(text("REFRESH MATERIALIZED VIEW mv_resumo_mensal;"))
                logger.info("  Materialized view atualizada.")
            except Exception as e2:
                logger.error(f"  Erro ao atualizar view: {e2}")

    engine.dispose()
    logger.info("Script finalizado.")


if __name__ == "__main__":
    main()
