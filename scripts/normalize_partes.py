"""Normaliza partes_processo agrupando por CPF/CNPJ/cd_pessoa.

Cria/atualiza a tabela `partes_normalizadas` com metricas agregadas
por pessoa, contextualizadas em relacao ao polo do Estado.

Chave de normalizacao (prioridade):
  1. CNPJ — consolida municipios/orgaos com multiplos cd_pessoa
  2. CPF — consolida pessoas fisicas com multiplos cd_pessoa
  3. cd_pessoa — fallback para registros sem documento

Uso:
    python scripts/normalize_partes.py
"""

import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from etl.config import PostgresConfig

import psycopg2

logger = logging.getLogger(__name__)

# -- DDL -----------------------------------------------------------------------

DDL_PARTES_NORMALIZADAS = """
DROP TABLE IF EXISTS partes_normalizadas;
CREATE TABLE partes_normalizadas (
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
"""

DDL_INDICES = """
CREATE INDEX IF NOT EXISTS idx_pn_nome ON partes_normalizadas (nome);
CREATE INDEX IF NOT EXISTS idx_pn_cpf ON partes_normalizadas (cpf) WHERE cpf IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_pn_cnpj ON partes_normalizadas (cnpj) WHERE cnpj IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_pn_oab ON partes_normalizadas (oab) WHERE oab IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_pn_contra ON partes_normalizadas (qtd_contra_estado DESC);
CREATE INDEX IF NOT EXISTS idx_pn_executado ON partes_normalizadas (qtd_executado_estado DESC);
CREATE INDEX IF NOT EXISTS idx_pn_advogado ON partes_normalizadas (qtd_advogado DESC);
CREATE INDEX IF NOT EXISTS idx_pn_coreu ON partes_normalizadas (qtd_coreu_estado DESC);
CREATE INDEX IF NOT EXISTS idx_pn_valor ON partes_normalizadas (valor_total DESC);
"""

# -- Normalizacao via SQL puro -------------------------------------------------

NORMALIZE_SQL = """
INSERT INTO partes_normalizadas (
    chave_tipo, chave_valor, nome, cpf, cnpj, oab, tipo_pessoa,
    qtd_processos, qtd_contra_estado, qtd_executado_estado,
    qtd_advogado, qtd_coreu_estado, valor_total, valor_medio
)
WITH
-- Polo do Estado em cada processo (so polo 1 e 2, ignorando polo 4 = PGE advogado)
polo_estado AS (
    SELECT cd_processo, MIN(polo) AS polo_estado
    FROM partes_processo
    WHERE polo IN (1, 2)
      AND (nome ILIKE '%%Estado de Mato Grosso%%' OR cnpj = '15412257000128')
    GROUP BY cd_processo
),
-- Chave de normalizacao por registro: CNPJ > CPF > cd_pessoa
partes_com_chave AS (
    SELECT
        p.*,
        CASE
            WHEN p.cnpj IS NOT NULL THEN 'CNPJ'
            WHEN p.cpf IS NOT NULL  THEN 'CPF'
            ELSE 'CD'
        END AS chave_tipo,
        CASE
            WHEN p.cnpj IS NOT NULL THEN p.cnpj
            WHEN p.cpf IS NOT NULL  THEN p.cpf
            ELSE p.cd_pessoa::TEXT
        END AS chave_valor
    FROM partes_processo p
    WHERE p.cd_pessoa IS NOT NULL
),
-- Nome mais frequente por chave (MODE via ROW_NUMBER)
nome_freq AS (
    SELECT chave_tipo, chave_valor, nome,
           ROW_NUMBER() OVER (
               PARTITION BY chave_tipo, chave_valor
               ORDER BY COUNT(*) DESC, nome
           ) AS rn
    FROM partes_com_chave
    GROUP BY chave_tipo, chave_valor, nome
),
-- Documentos consolidados por chave
docs AS (
    SELECT
        chave_tipo,
        chave_valor,
        MAX(cpf) AS cpf,
        MAX(cnpj) AS cnpj,
        MAX(oab) AS oab,
        MAX(tipo_pessoa) AS tipo_pessoa
    FROM partes_com_chave
    GROUP BY chave_tipo, chave_valor
),
-- Metricas por chave
metricas AS (
    SELECT
        pc.chave_tipo,
        pc.chave_valor,
        COUNT(DISTINCT pc.cd_processo) AS qtd_processos,
        COUNT(DISTINCT pc.cd_processo) FILTER (
            WHERE pe.polo_estado = 2 AND pc.polo = 1
        ) AS qtd_contra_estado,
        COUNT(DISTINCT pc.cd_processo) FILTER (
            WHERE pe.polo_estado = 1 AND pc.polo = 2
        ) AS qtd_executado_estado,
        COUNT(DISTINCT pc.cd_processo) FILTER (
            WHERE pc.polo = 4 AND pe.polo_estado IS NOT NULL
        ) AS qtd_advogado,
        COUNT(DISTINCT pc.cd_processo) FILTER (
            WHERE pe.polo_estado = 2 AND pc.polo = 2
              AND pc.nome NOT ILIKE '%%Estado de Mato Grosso%%'
        ) AS qtd_coreu_estado
    FROM partes_com_chave pc
    LEFT JOIN polo_estado pe ON pe.cd_processo = pc.cd_processo
    GROUP BY pc.chave_tipo, pc.chave_valor
),
-- Valor por chave (distintos por processo para evitar duplicacao)
valor AS (
    SELECT
        chave_tipo,
        chave_valor,
        COALESCE(SUM(val), 0) AS valor_total,
        COALESCE(AVG(val), 0) AS valor_medio
    FROM (
        SELECT DISTINCT chave_tipo, chave_valor, cd_processo, valor_acao AS val
        FROM partes_com_chave
        WHERE valor_acao IS NOT NULL AND valor_acao > 0
    ) sub
    GROUP BY chave_tipo, chave_valor
)
SELECT
    d.chave_tipo,
    d.chave_valor,
    n.nome,
    d.cpf,
    d.cnpj,
    d.oab,
    d.tipo_pessoa,
    m.qtd_processos,
    m.qtd_contra_estado,
    m.qtd_executado_estado,
    m.qtd_advogado,
    m.qtd_coreu_estado,
    COALESCE(v.valor_total, 0),
    COALESCE(v.valor_medio, 0)
FROM docs d
JOIN nome_freq n ON n.chave_tipo = d.chave_tipo
    AND n.chave_valor = d.chave_valor AND n.rn = 1
JOIN metricas m ON m.chave_tipo = d.chave_tipo
    AND m.chave_valor = d.chave_valor
LEFT JOIN valor v ON v.chave_tipo = d.chave_tipo
    AND v.chave_valor = d.chave_valor;
"""


def normalize(pg_conn) -> int:
    """Executa a normalizacao e retorna o total de registros."""
    cur = pg_conn.cursor()

    logger.info("Criando tabela partes_normalizadas...")
    cur.execute(DDL_PARTES_NORMALIZADAS)
    pg_conn.commit()

    logger.info("Executando normalizacao (pode levar alguns segundos)...")
    t0 = time.monotonic()
    cur.execute(NORMALIZE_SQL)
    pg_conn.commit()
    elapsed = time.monotonic() - t0

    logger.info("Criando indices...")
    cur.execute(DDL_INDICES)
    pg_conn.commit()

    cur.execute("SELECT COUNT(*) FROM partes_normalizadas")
    total = cur.fetchone()[0]
    logger.info("Normalizacao concluida em %.1fs: %d pessoas.", elapsed, total)

    cur.close()
    return total


def _safe_print(msg: str) -> None:
    """Print seguro para Windows cp1252."""
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode("ascii", errors="replace").decode("ascii"))


def print_summary(pg_conn) -> None:
    """Exibe resumo da normalizacao."""
    cur = pg_conn.cursor()

    print("\n" + "=" * 70)
    print("RESUMO DA NORMALIZACAO")
    print("=" * 70)

    cur.execute("SELECT COUNT(*) FROM partes_normalizadas")
    print(f"\nTotal de pessoas normalizadas: {cur.fetchone()[0]:,}")

    cur.execute("""
        SELECT chave_tipo, COUNT(*)
        FROM partes_normalizadas
        GROUP BY chave_tipo ORDER BY chave_tipo
    """)
    print("\nTipo de chave:")
    for tipo, qtd in cur.fetchall():
        print(f"  {tipo}: {qtd:,}")

    cur.execute("""
        SELECT
            COUNT(*) FILTER (WHERE qtd_contra_estado > 0) AS demandantes,
            COUNT(*) FILTER (WHERE qtd_executado_estado > 0) AS executados,
            COUNT(*) FILTER (WHERE qtd_advogado > 0) AS advogados,
            COUNT(*) FILTER (WHERE qtd_coreu_estado > 0) AS coreus
        FROM partes_normalizadas
    """)
    r = cur.fetchone()
    print(f"\nPor papel:")
    print(f"  Demandantes contra Estado: {r[0]:>8,}")
    print(f"  Executados pelo Estado:    {r[1]:>8,}")
    print(f"  Advogados:                 {r[2]:>8,}")
    print(f"  Co-reus do Estado:         {r[3]:>8,}")

    # TOP 15 demandantes
    cur.execute("""
        SELECT nome, cpf, cnpj, qtd_contra_estado, valor_total
        FROM partes_normalizadas
        WHERE qtd_contra_estado > 0
          AND nome NOT ILIKE '%%Estado de Mato Grosso%%'
        ORDER BY qtd_contra_estado DESC
        LIMIT 15
    """)
    print("\nTOP 15 DEMANDANTES CONTRA O ESTADO:")
    for i, (nome, cpf, cnpj, qtd, valor) in enumerate(cur.fetchall(), 1):
        doc = cpf or cnpj or "sem doc"
        v = f"R$ {valor:,.0f}" if valor else "s/ valor"
        _safe_print(f"  {i:>2}. {nome[:45]:<45s} | {doc:<18s} | {qtd:>4} proc | {v}")

    # TOP 15 executados
    cur.execute("""
        SELECT nome, cpf, cnpj, qtd_executado_estado, valor_total
        FROM partes_normalizadas
        WHERE qtd_executado_estado > 0
          AND nome NOT ILIKE '%%Estado de Mato Grosso%%'
        ORDER BY qtd_executado_estado DESC
        LIMIT 15
    """)
    print("\nTOP 15 EXECUTADOS PELO ESTADO:")
    for i, (nome, cpf, cnpj, qtd, valor) in enumerate(cur.fetchall(), 1):
        doc = cpf or cnpj or "sem doc"
        v = f"R$ {valor:,.0f}" if valor else "s/ valor"
        _safe_print(f"  {i:>2}. {nome[:45]:<45s} | {doc:<18s} | {qtd:>3} proc | {v}")

    # TOP 15 advogados
    cur.execute("""
        SELECT nome, oab, qtd_advogado
        FROM partes_normalizadas
        WHERE qtd_advogado > 0
          AND nome NOT ILIKE '%%Procuradoria-geral do Estado%%'
        ORDER BY qtd_advogado DESC
        LIMIT 15
    """)
    print("\nTOP 15 ADVOGADOS (excl. PGE):")
    for i, (nome, oab, qtd) in enumerate(cur.fetchall(), 1):
        oab_str = oab or "sem OAB"
        _safe_print(f"  {i:>2}. {nome[:50]:<50s} | {oab_str:<12s} | {qtd:>5} proc")

    # TOP 15 co-reus
    cur.execute("""
        SELECT nome, cpf, cnpj, qtd_coreu_estado
        FROM partes_normalizadas
        WHERE qtd_coreu_estado > 0
          AND nome NOT ILIKE '%%Estado de Mato Grosso%%'
        ORDER BY qtd_coreu_estado DESC
        LIMIT 15
    """)
    print("\nTOP 15 CO-REUS (mesmo polo do Estado):")
    for i, (nome, cpf, cnpj, qtd) in enumerate(cur.fetchall(), 1):
        doc = cpf or cnpj or "sem doc"
        _safe_print(f"  {i:>2}. {nome[:50]:<50s} | {doc:<18s} | {qtd:>5} proc")

    cur.close()
    print("\n" + "=" * 70)


def main() -> None:
    """Ponto de entrada."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    pg_cfg = PostgresConfig()
    pg_conn = psycopg2.connect(
        host=pg_cfg.host,
        port=pg_cfg.port,
        user=pg_cfg.user,
        password=pg_cfg.password,
        dbname=pg_cfg.dbname,
    )
    logger.info("Conectado ao PostgreSQL.")

    normalize(pg_conn)
    print_summary(pg_conn)

    pg_conn.close()


if __name__ == "__main__":
    main()
