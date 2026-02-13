"""ETL: Partes do processo, advogados e valor da causa (Oracle -> PostgreSQL).

Extrai partes (autores, reus, advogados) e valor da acao de processos
distribuidos em um periodo, carregando no PostgreSQL sem normalizacao.

Uso:
    python scripts/etl_partes.py                          # ultimos 30 dias
    python scripts/etl_partes.py --inicio 2025-01-01 --fim 2026-02-11
    python scripts/etl_partes.py --inicio 2025-01-01 --fim 2026-02-11 --valor
"""

import argparse
import logging
import sys
import time
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from etl.config import BATCH_SIZE, OracleConfig, PostgresConfig, TunnelConfig
from etl.extractor import _init_thick_mode
from etl.tunnel import OracleTunnel

import oracledb
import psycopg2
from psycopg2.extras import execute_values

logger = logging.getLogger(__name__)

# -- DDL PostgreSQL -----------------------------------------------------------

DDL_PARTES_PROCESSO = """
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
"""

DDL_ADD_VALOR_ACAO = """
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'processos_novos' AND column_name = 'valor_acao'
    ) THEN
        ALTER TABLE processos_novos ADD COLUMN valor_acao NUMERIC;
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'processos_novos' AND column_name = 'tipo_valor'
    ) THEN
        ALTER TABLE processos_novos ADD COLUMN tipo_valor CHAR(1);
    END IF;
END $$;
"""

DDL_INDICES = """
CREATE INDEX IF NOT EXISTS idx_partes_numero_processo
    ON partes_processo (numero_processo);
CREATE INDEX IF NOT EXISTS idx_partes_cd_pessoa
    ON partes_processo (cd_pessoa);
CREATE INDEX IF NOT EXISTS idx_partes_polo
    ON partes_processo (polo);
CREATE INDEX IF NOT EXISTS idx_partes_cpf
    ON partes_processo (cpf) WHERE cpf IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_partes_cnpj
    ON partes_processo (cnpj) WHERE cnpj IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_partes_oab
    ON partes_processo (oab) WHERE oab IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_partes_nome
    ON partes_processo (nome);
"""

# -- Query Oracle: partes do processo -----------------------------------------

QUERY_PARTES = """
SELECT
    PP.CDPROCESSO        AS cd_processo,
    PP.NUSEQPARTE        AS seq_parte,
    PC.NUPROCESSO        AS numero_processo,
    PC.NUFORMATADO       AS numero_formatado,
    PP.CDPESSOA          AS cd_pessoa,
    NM.NMPESSOA          AS nome,
    TP.DEMASCSINGULAR    AS tipo_parte,
    TP.TPPARTE           AS polo,
    PP.FLPRINCIPAL       AS principal,
    P.TPPESSOA           AS tipo_pessoa,
    P.TPCATEGPESSOA      AS cd_categ_pessoa,
    DOC_CPF.NUDOCUMENTO  AS cpf,
    DOC_CNPJ.NUDOCUMENTO AS cnpj,
    DOC_RG.NUDOCUMENTO   AS rg,
    DOC_OAB.NUDOCFORMATADO AS oab,
    PC.VLACAO            AS valor_acao,
    PC.TPVALOR           AS tipo_valor
FROM SAJ.ESPJPROCPESSOA PP
JOIN SAJ.ESPJPROCESSO PC ON PC.CDPROCESSO = PP.CDPROCESSO
JOIN SAJ.ESPJDISTPROCESSO DP ON DP.CDPROCESSO = PC.CDPROCESSO
    AND DP.FLULTDIST = 'S'
JOIN SAJ.ESAJNOME NM ON NM.CDPESSOA = PP.CDPESSOA
    AND NM.TPNOME = 'N'
JOIN SAJ.ESAJTIPOPARTE TP ON TP.CDTIPOPARTE = PP.CDTIPOPARTE
LEFT JOIN SAJ.ESAJPESSOA P ON P.CDPESSOA = PP.CDPESSOA
LEFT JOIN SAJ.ESAJPESSOADOC DOC_CPF
    ON DOC_CPF.CDPESSOA = PP.CDPESSOA
    AND DOC_CPF.SGTIPODOCUMENTO = 'CPF '
    AND DOC_CPF.FLPRINCIPAL = 'S'
LEFT JOIN SAJ.ESAJPESSOADOC DOC_CNPJ
    ON DOC_CNPJ.CDPESSOA = PP.CDPESSOA
    AND DOC_CNPJ.SGTIPODOCUMENTO = 'CNPJ'
    AND DOC_CNPJ.FLPRINCIPAL = 'S'
LEFT JOIN SAJ.ESAJPESSOADOC DOC_RG
    ON DOC_RG.CDPESSOA = PP.CDPESSOA
    AND DOC_RG.SGTIPODOCUMENTO = 'RG  '
    AND DOC_RG.FLPRINCIPAL = 'S'
LEFT JOIN SAJ.ESAJPESSOADOC DOC_OAB
    ON DOC_OAB.CDPESSOA = PP.CDPESSOA
    AND DOC_OAB.SGTIPODOCUMENTO = 'OAB '
    AND DOC_OAB.FLPRINCIPAL = 'S'
WHERE PC.CDSITUACAOPROC IN (3, 4, 5)
  AND PC.CDPROCESSOSUP IS NULL
  AND PC.DTUSUINCLUSAO >= :start_date
  AND PC.DTUSUINCLUSAO < :end_date
"""

# -- Query Oracle: atualizar valor_acao em processos_novos --------------------

QUERY_VALOR_ACAO = """
SELECT
    PC.NUPROCESSO  AS numero_processo,
    PC.VLACAO      AS valor_acao,
    PC.TPVALOR     AS tipo_valor
FROM SAJ.ESPJPROCESSO PC
WHERE PC.CDSITUACAOPROC IN (3, 4, 5)
  AND PC.CDPROCESSOSUP IS NULL
  AND PC.VLACAO IS NOT NULL
  AND PC.DTUSUINCLUSAO >= :start_date
  AND PC.DTUSUINCLUSAO < :end_date
"""

# -- Colunas para INSERT/UPSERT ----------------------------------------------

PARTES_COLUMNS = [
    "cd_processo", "seq_parte", "numero_processo", "numero_formatado",
    "cd_pessoa", "nome", "tipo_parte", "polo", "principal", "tipo_pessoa",
    "cd_categ_pessoa", "cpf", "cnpj", "rg", "oab", "valor_acao", "tipo_valor",
]

UPSERT_PARTES = f"""
INSERT INTO partes_processo ({', '.join(PARTES_COLUMNS)})
VALUES %s
ON CONFLICT (cd_processo, seq_parte) DO UPDATE SET
    numero_processo = EXCLUDED.numero_processo,
    numero_formatado = EXCLUDED.numero_formatado,
    cd_pessoa = EXCLUDED.cd_pessoa,
    nome = EXCLUDED.nome,
    tipo_parte = EXCLUDED.tipo_parte,
    polo = EXCLUDED.polo,
    principal = EXCLUDED.principal,
    tipo_pessoa = EXCLUDED.tipo_pessoa,
    cd_categ_pessoa = EXCLUDED.cd_categ_pessoa,
    cpf = EXCLUDED.cpf,
    cnpj = EXCLUDED.cnpj,
    rg = EXCLUDED.rg,
    oab = EXCLUDED.oab,
    valor_acao = EXCLUDED.valor_acao,
    tipo_valor = EXCLUDED.tipo_valor
"""

UPSERT_VALOR = """
UPDATE processos_novos
SET valor_acao = d.valor_acao,
    tipo_valor = d.tipo_valor
FROM (VALUES %s) AS d(numero_processo, valor_acao, tipo_valor)
WHERE processos_novos.numero_processo = d.numero_processo::bigint
"""


def create_pg_tables(pg_conn) -> None:
    """Cria tabelas e indices no PostgreSQL."""
    cur = pg_conn.cursor()
    cur.execute(DDL_PARTES_PROCESSO)
    cur.execute(DDL_ADD_VALOR_ACAO)
    cur.execute(DDL_INDICES)
    pg_conn.commit()
    cur.close()
    logger.info("Tabelas e indices criados/verificados no PostgreSQL.")


def extract_and_load_partes(
    ora_conn,
    pg_conn,
    start_date: date,
    end_date: date,
) -> int:
    """Extrai partes do Oracle e carrega no PostgreSQL em batches."""
    logger.info("Extraindo partes (%s ate %s)...", start_date, end_date)

    ora_cur = ora_conn.cursor()
    ora_cur.arraysize = BATCH_SIZE
    ora_cur.execute(QUERY_PARTES, start_date=start_date, end_date=end_date)
    columns = [col[0].lower() for col in ora_cur.description]

    total = 0
    pg_cur = pg_conn.cursor()

    while True:
        rows = ora_cur.fetchmany(BATCH_SIZE)
        if not rows:
            break

        # Converte para lista de tuplas na ordem das colunas
        batch = []
        for row in rows:
            record = dict(zip(columns, row))
            # Limpa strings com espaços trailing (CHAR do Oracle)
            for key in ("cd_processo", "principal", "tipo_pessoa", "tipo_valor"):
                if record.get(key) and isinstance(record[key], str):
                    record[key] = record[key].strip()
            batch.append(tuple(record[col] for col in PARTES_COLUMNS))

        execute_values(pg_cur, UPSERT_PARTES, batch, page_size=1000)
        pg_conn.commit()
        total += len(batch)
        logger.info("  partes_processo: %d registros carregados...", total)

    ora_cur.close()
    pg_cur.close()
    logger.info("  partes_processo: %d registros totais.", total)
    return total


def extract_and_load_valor(
    ora_conn,
    pg_conn,
    start_date: date,
    end_date: date,
) -> int:
    """Extrai valor_acao do Oracle e atualiza processos_novos."""
    logger.info("Extraindo valor_acao (%s ate %s)...", start_date, end_date)

    ora_cur = ora_conn.cursor()
    ora_cur.arraysize = BATCH_SIZE
    ora_cur.execute(QUERY_VALOR_ACAO, start_date=start_date, end_date=end_date)

    total = 0
    pg_cur = pg_conn.cursor()

    while True:
        rows = ora_cur.fetchmany(BATCH_SIZE)
        if not rows:
            break

        batch = []
        for row in rows:
            numero_processo = row[0]
            valor_acao = row[1]
            tipo_valor = row[2].strip() if row[2] else row[2]
            batch.append((numero_processo, valor_acao, tipo_valor))

        execute_values(
            pg_cur,
            UPSERT_VALOR,
            batch,
            template="(%s, %s::numeric, %s::char(1))",
            page_size=1000,
        )
        pg_conn.commit()
        total += len(batch)
        logger.info("  valor_acao: %d registros atualizados...", total)

    ora_cur.close()
    pg_cur.close()
    logger.info("  valor_acao: %d registros totais.", total)
    return total


def _safe_print(msg: str) -> None:
    """Print seguro para Windows cp1252."""
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode("ascii", errors="replace").decode("ascii"))


# CTE reutilizavel: processos onde o Estado eh reu (polo 2)
_CTE_ESTADO_REU = """
    processos_estado_reu AS (
        SELECT DISTINCT cd_processo
        FROM partes_processo
        WHERE polo = 2
          AND (nome ILIKE '%%Estado de Mato Grosso%%' OR cnpj = '15412257000128')
    )
"""

# CTE reutilizavel: processos onde o Estado eh autor/exequente (polo 1)
_CTE_ESTADO_AUTOR = """
    processos_estado_autor AS (
        SELECT DISTINCT cd_processo
        FROM partes_processo
        WHERE polo = 1
          AND (nome ILIKE '%%Estado de Mato Grosso%%' OR cnpj = '15412257000128')
    )
"""


def print_summary(pg_conn, start_date: date, end_date: date) -> None:
    """Exibe resumo dos dados carregados."""
    cur = pg_conn.cursor()

    print("\n" + "=" * 70)
    print("RESUMO DA EXTRACAO")
    print("=" * 70)

    # Total de partes
    cur.execute("SELECT COUNT(*) FROM partes_processo")
    total = cur.fetchone()[0]
    print(f"\nTotal de registros em partes_processo: {total:,}")

    # Polo do Estado
    cur.execute("""
        SELECT polo, COUNT(DISTINCT cd_processo)
        FROM partes_processo
        WHERE nome ILIKE '%%Estado de Mato Grosso%%' OR cnpj = '15412257000128'
        GROUP BY polo ORDER BY polo
    """)
    print("\nPolo do Estado nos processos:")
    for polo, qtd in cur.fetchall():
        desc = {1: "ATIVO (autor)", 2: "PASSIVO (reu)", 3: "TERCEIRO", 4: "ADVOGADO"}.get(polo, str(polo))
        print(f"  Polo {polo} ({desc}): {qtd:,} processos")

    # Por polo/tipo
    cur.execute("""
        SELECT polo, tipo_parte, COUNT(*) as qtd
        FROM partes_processo
        GROUP BY polo, tipo_parte
        ORDER BY qtd DESC
        LIMIT 15
    """)
    print("\nDistribuicao por polo/tipo:")
    for polo, tipo, qtd in cur.fetchall():
        polo_desc = {1: "ATIVO", 2: "PASSIVO", 3: "TERCEIRO", 4: "ADVOGADO"}.get(polo, str(polo))
        _safe_print(f"  Polo {polo} ({polo_desc:8s}) | {tipo:<20s} | {qtd:>8,}")

    # Cobertura de documentos
    cur.execute("""
        SELECT
            COUNT(*) AS total,
            COUNT(cpf) AS com_cpf,
            COUNT(cnpj) AS com_cnpj,
            COUNT(rg) AS com_rg,
            COUNT(oab) AS com_oab,
            COUNT(CASE WHEN cpf IS NOT NULL OR cnpj IS NOT NULL THEN 1 END) AS com_cpf_ou_cnpj
        FROM partes_processo
    """)
    row = cur.fetchone()
    print(f"\nCobertura de documentos:")
    print(f"  Total partes:      {row[0]:>8,}")
    print(f"  Com CPF:           {row[1]:>8,} ({row[1]/row[0]*100:.1f}%)")
    print(f"  Com CNPJ:          {row[2]:>8,} ({row[2]/row[0]*100:.1f}%)")
    print(f"  Com RG:            {row[3]:>8,} ({row[3]/row[0]*100:.1f}%)")
    print(f"  Com OAB:           {row[4]:>8,} ({row[4]/row[0]*100:.1f}%)")
    print(f"  Com CPF ou CNPJ:   {row[5]:>8,} ({row[5]/row[0]*100:.1f}%)")

    # Valor da acao (processos distintos)
    cur.execute("""
        SELECT
            COUNT(DISTINCT cd_processo) AS total_proc,
            COUNT(DISTINCT CASE WHEN valor_acao IS NOT NULL THEN cd_processo END) AS com_valor,
            COUNT(DISTINCT CASE WHEN valor_acao > 0 THEN cd_processo END) AS valor_positivo,
            MIN(CASE WHEN valor_acao > 0 THEN valor_acao END) AS min_valor,
            MAX(valor_acao) AS max_valor,
            AVG(DISTINCT CASE WHEN valor_acao > 0 THEN valor_acao END) AS avg_valor
        FROM partes_processo
    """)
    row = cur.fetchone()
    print(f"\nValor da acao (processos distintos):")
    print(f"  Total processos:   {row[0]:>8,}")
    print(f"  Com valor:         {row[1]:>8,}")
    print(f"  Valor positivo:    {row[2]:>8,}")
    if row[3]:
        print(f"  Min valor:         R$ {row[3]:>14,.2f}")
        print(f"  Max valor:         R$ {row[4]:>14,.2f}")

    # -- TOP DEMANDANTES CONTRA O ESTADO --
    # Polo 1 em processos onde o Estado eh polo 2
    cur.execute(f"""
        WITH {_CTE_ESTADO_REU}
        SELECT
            p.nome, p.cpf, p.cnpj, p.tipo_parte,
            COUNT(DISTINCT p.cd_processo) AS qtd_processos,
            AVG(p.valor_acao) AS valor_medio
        FROM partes_processo p
        JOIN processos_estado_reu er ON er.cd_processo = p.cd_processo
        WHERE p.polo = 1
          AND p.nome NOT ILIKE '%%Estado de Mato Grosso%%'
          AND p.tipo_parte NOT IN ('Advogado')
        GROUP BY p.nome, p.cpf, p.cnpj, p.tipo_parte
        ORDER BY qtd_processos DESC
        LIMIT 15
    """)
    print("\nTOP 15 DEMANDANTES CONTRA O ESTADO (polo ativo, Estado eh reu):")
    for i, (nome, cpf, cnpj, tipo, qtd, valor) in enumerate(cur.fetchall(), 1):
        doc = cpf or cnpj or "sem doc"
        v = f"R$ {valor:,.0f}" if valor else "s/ valor"
        _safe_print(f"  {i:>2}. {nome[:45]:<45s} | {tipo:<12s} | {doc:<18s} | {qtd:>4} proc | {v}")

    # -- TOP EXECUTADOS PELO ESTADO --
    # Polo 2 em processos onde o Estado eh polo 1 (exequente/autor)
    cur.execute(f"""
        WITH {_CTE_ESTADO_AUTOR}
        SELECT
            p.nome, p.cpf, p.cnpj, p.tipo_parte,
            COUNT(DISTINCT p.cd_processo) AS qtd_processos,
            SUM(p.valor_acao) AS valor_total
        FROM partes_processo p
        JOIN processos_estado_autor ea ON ea.cd_processo = p.cd_processo
        WHERE p.polo = 2
          AND p.nome NOT ILIKE '%%Estado de Mato Grosso%%'
          AND p.tipo_parte NOT IN ('Advogado')
        GROUP BY p.nome, p.cpf, p.cnpj, p.tipo_parte
        ORDER BY qtd_processos DESC
        LIMIT 15
    """)
    print("\nTOP 15 EXECUTADOS PELO ESTADO (polo passivo, Estado eh autor/exequente):")
    for i, (nome, cpf, cnpj, tipo, qtd, valor) in enumerate(cur.fetchall(), 1):
        doc = cpf or cnpj or "sem doc"
        v = f"R$ {valor:,.0f}" if valor else "s/ valor"
        _safe_print(f"  {i:>2}. {nome[:45]:<45s} | {tipo:<12s} | {doc:<18s} | {qtd:>3} proc | {v}")

    # -- TOP ADVOGADOS CONTRA O ESTADO (excl. Defensoria/PGE) --
    cur.execute(f"""
        WITH {_CTE_ESTADO_REU}
        SELECT
            p.nome, p.oab,
            COUNT(DISTINCT p.cd_processo) AS qtd_processos
        FROM partes_processo p
        JOIN processos_estado_reu er ON er.cd_processo = p.cd_processo
        WHERE p.polo = 4
          AND p.oab IS NOT NULL
          AND p.nome NOT ILIKE '%%Procuradoria-geral do Estado%%'
        GROUP BY p.nome, p.oab
        ORDER BY qtd_processos DESC
        LIMIT 15
    """)
    print("\nTOP 15 ADVOGADOS CONTRA O ESTADO (excl. PGE):")
    for i, (nome, oab, qtd) in enumerate(cur.fetchall(), 1):
        _safe_print(f"  {i:>2}. {nome[:50]:<50s} | OAB {oab:<12s} | {qtd:>4} processos")

    # -- CO-REUS (mesmo polo do Estado) --
    cur.execute(f"""
        WITH {_CTE_ESTADO_REU}
        SELECT
            p.nome, p.cpf, p.cnpj, p.tipo_parte,
            COUNT(DISTINCT p.cd_processo) AS qtd_processos
        FROM partes_processo p
        JOIN processos_estado_reu er ON er.cd_processo = p.cd_processo
        WHERE p.polo = 2
          AND p.nome NOT ILIKE '%%Estado de Mato Grosso%%'
          AND p.tipo_parte NOT IN ('Advogado')
        GROUP BY p.nome, p.cpf, p.cnpj, p.tipo_parte
        ORDER BY qtd_processos DESC
        LIMIT 15
    """)
    print("\nTOP 15 CO-REUS (mesmo polo do Estado, Estado eh reu):")
    for i, (nome, cpf, cnpj, tipo, qtd) in enumerate(cur.fetchall(), 1):
        doc = cpf or cnpj or "sem doc"
        _safe_print(f"  {i:>2}. {nome[:45]:<45s} | {tipo:<15s} | {doc:<18s} | {qtd:>4}")

    # Valor da acao em processos_novos
    cur.execute("""
        SELECT
            COUNT(*) AS total,
            COUNT(valor_acao) AS com_valor,
            COUNT(CASE WHEN valor_acao > 0 THEN 1 END) AS positivo
        FROM processos_novos
    """)
    row = cur.fetchone()
    print(f"\nValor da acao em processos_novos:")
    print(f"  Total processos:   {row[0]:>8,}")
    print(f"  Com valor:         {row[1]:>8,}")
    print(f"  Valor positivo:    {row[2]:>8,}")

    cur.close()
    print("\n" + "=" * 70)


def main() -> None:
    """Ponto de entrada."""
    parser = argparse.ArgumentParser(description="ETL: partes, advogados e valor da causa")
    parser.add_argument("--inicio", type=str, default="2025-01-01",
                        help="Data inicio (YYYY-MM-DD)")
    parser.add_argument("--fim", type=str, default="2026-02-11",
                        help="Data fim exclusivo (YYYY-MM-DD)")
    parser.add_argument("--valor", action="store_true",
                        help="Tambem atualizar valor_acao em processos_novos")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    start_date = datetime.strptime(args.inicio, "%Y-%m-%d").date()
    end_date = datetime.strptime(args.fim, "%Y-%m-%d").date()

    logger.info("Periodo: %s ate %s", start_date, end_date)

    # Conexao PostgreSQL
    pg_cfg = PostgresConfig()
    pg_conn = psycopg2.connect(
        host=pg_cfg.host,
        port=pg_cfg.port,
        user=pg_cfg.user,
        password=pg_cfg.password,
        dbname=pg_cfg.dbname,
    )
    logger.info("Conectado ao PostgreSQL.")

    # Cria tabelas
    create_pg_tables(pg_conn)

    # Conexao Oracle via tunel
    with OracleTunnel(TunnelConfig()):
        ora_cfg = OracleConfig()
        _init_thick_mode()
        ora_conn = oracledb.connect(
            user=ora_cfg.user,
            password=ora_cfg.password,
            dsn=ora_cfg.dsn,
        )
        logger.info("Conectado ao Oracle.")

        t0 = time.monotonic()

        # 1. Extrair partes
        n_partes = extract_and_load_partes(ora_conn, pg_conn, start_date, end_date)

        # 2. Atualizar valor_acao em processos_novos (opcional ou por padrao)
        if args.valor or True:  # sempre executa por ora
            n_valor = extract_and_load_valor(ora_conn, pg_conn, start_date, end_date)
        else:
            n_valor = 0

        elapsed = time.monotonic() - t0
        logger.info(
            "ETL concluido em %.1fs: %d partes, %d valores atualizados.",
            elapsed, n_partes, n_valor,
        )

        ora_conn.close()

    # Resumo
    print_summary(pg_conn, start_date, end_date)
    pg_conn.close()


if __name__ == "__main__":
    main()
