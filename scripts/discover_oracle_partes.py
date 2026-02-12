"""Script de descoberta: tabelas de partes, advogados e valor da causa no Oracle SAJ.

Uso:
    1. Conectar na VPN-PGE
    2. Rodar: python scripts/discover_oracle_partes.py

Gera um relatorio em scripts/logs/discovery_partes.txt com:
  - Tabelas Oracle que contem PARTE, ADVOG, PESSOA, VALOR no nome
  - Colunas de cada tabela encontrada
  - Amostra de dados (5 primeiros registros)
  - Colunas de ESPJPROCESSO (para verificar VLCAUSA)
"""

import logging
import sys
from datetime import datetime
from pathlib import Path

# Permite rodar como `python scripts/discover_oracle_partes.py` de qualquer diretorio
sys.path.insert(0, str(Path(__file__).resolve().parent))

from etl.config import LOG_DIR, OracleConfig, TunnelConfig
from etl.extractor import _init_thick_mode
from etl.tunnel import OracleTunnel

import oracledb

logger = logging.getLogger(__name__)

# -- Queries de descoberta -----------------------------------------------------

DISCOVER_TABLES = """
SELECT TABLE_NAME
FROM ALL_TABLES
WHERE OWNER = 'SAJ'
  AND (
    TABLE_NAME LIKE '%PARTE%'
    OR TABLE_NAME LIKE '%ADVOG%'
    OR TABLE_NAME LIKE '%PESSOA%'
    OR TABLE_NAME LIKE '%VALOR%'
    OR TABLE_NAME LIKE '%NOME%'
    OR TABLE_NAME LIKE '%AUTOR%'
    OR TABLE_NAME LIKE '%REPR%'
    OR TABLE_NAME LIKE '%PROCUR%'
    OR TABLE_NAME LIKE '%LITIG%'
  )
ORDER BY TABLE_NAME
"""

DISCOVER_COLUMNS = """
SELECT COLUMN_NAME, DATA_TYPE, DATA_LENGTH, NULLABLE
FROM ALL_TAB_COLUMNS
WHERE OWNER = 'SAJ'
  AND TABLE_NAME = :table_name
ORDER BY COLUMN_ID
"""

COUNT_TABLE = "SELECT COUNT(*) FROM SAJ.{table}"
SAMPLE_TABLE = "SELECT * FROM SAJ.{table} WHERE ROWNUM <= 5"

DISCOVER_PROCESSO_COLS = """
SELECT COLUMN_NAME, DATA_TYPE, DATA_LENGTH, NULLABLE
FROM ALL_TAB_COLUMNS
WHERE OWNER = 'SAJ'
  AND TABLE_NAME = 'ESPJPROCESSO'
ORDER BY COLUMN_ID
"""

DISCOVER_CPF_CNPJ_COLS = """
SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE, DATA_LENGTH
FROM ALL_TAB_COLUMNS
WHERE OWNER = 'SAJ'
  AND (
    COLUMN_NAME LIKE '%CPF%'
    OR COLUMN_NAME LIKE '%CNPJ%'
    OR COLUMN_NAME LIKE '%OAB%'
    OR COLUMN_NAME LIKE '%NUINSCRICAO%'
    OR COLUMN_NAME LIKE '%NUCPF%'
    OR COLUMN_NAME LIKE '%NUCNPJ%'
    OR COLUMN_NAME LIKE '%RG%'
    OR COLUMN_NAME LIKE '%DOCUMENTO%'
  )
ORDER BY TABLE_NAME, COLUMN_NAME
"""

DISCOVER_VALOR_COLS = """
SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE, DATA_LENGTH
FROM ALL_TAB_COLUMNS
WHERE OWNER = 'SAJ'
  AND (
    COLUMN_NAME LIKE '%VALOR%'
    OR COLUMN_NAME LIKE '%VLCAUSA%'
    OR COLUMN_NAME LIKE '%VLACAO%'
    OR COLUMN_NAME LIKE '%MONTANTE%'
  )
ORDER BY TABLE_NAME, COLUMN_NAME
"""


def discover(output_path: Path) -> None:
    """Executa a descoberta e grava o relatorio."""
    config = OracleConfig()
    _init_thick_mode()

    conn = oracledb.connect(
        user=config.user,
        password=config.password,
        dsn=config.dsn,
    )
    logger.info("Conectado ao Oracle.")

    lines: list[str] = []

    def log(msg: str = "") -> None:
        lines.append(msg)
        # print seguro para Windows cp1252
        try:
            print(msg)
        except UnicodeEncodeError:
            print(msg.encode("ascii", errors="replace").decode("ascii"))

    log("=" * 80)
    log("DESCOBERTA DE TABELAS -- PARTES, ADVOGADOS, VALOR DA CAUSA")
    log(f"Data: {datetime.now():%Y-%m-%d %H:%M:%S}")
    log("=" * 80)

    # -- 1. Colunas de ESPJPROCESSO -------------------------------------------
    log("")
    log("-" * 40)
    log("1. COLUNAS DE SAJ.ESPJPROCESSO (verificar VLCAUSA, etc)")
    log("-" * 40)
    cur = conn.cursor()
    cur.execute(DISCOVER_PROCESSO_COLS)
    for row in cur.fetchall():
        col_name, dtype, dlen, nullable = row
        log(f"  {col_name:<35} {dtype:<15} {dlen:<6} {'NULL' if nullable == 'Y' else 'NOT NULL'}")
    cur.close()

    # -- 2. Tabelas com termos relevantes -------------------------------------
    log("")
    log("-" * 40)
    log("2. TABELAS COM PARTE/ADVOG/PESSOA/VALOR/NOME/AUTOR/REPR/PROCUR/LITIG")
    log("-" * 40)
    cur = conn.cursor()
    cur.execute(DISCOVER_TABLES)
    tables = [row[0] for row in cur.fetchall()]
    cur.close()
    log(f"  Encontradas: {len(tables)} tabelas")
    for t in tables:
        log(f"  - SAJ.{t}")

    # -- 3. Colunas e amostra de cada tabela encontrada -----------------------
    for t in tables:
        log("")
        log("-" * 40)
        log(f"3. TABELA: SAJ.{t}")
        log("-" * 40)

        # Contagem
        try:
            cur = conn.cursor()
            cur.execute(COUNT_TABLE.format(table=t))
            count = cur.fetchone()[0]
            cur.close()
            log(f"  Total de registros: {count:,}")
        except Exception as e:
            log(f"  Erro ao contar: {e}")
            count = 0

        # Colunas
        cur = conn.cursor()
        cur.execute(DISCOVER_COLUMNS, table_name=t)
        cols = cur.fetchall()
        cur.close()
        log(f"  Colunas ({len(cols)}):")
        for col_name, dtype, dlen, nullable in cols:
            log(f"    {col_name:<35} {dtype:<15} {dlen:<6} {'NULL' if nullable == 'Y' else 'NOT NULL'}")

        # Amostra
        if count > 0:
            try:
                cur = conn.cursor()
                cur.execute(SAMPLE_TABLE.format(table=t))
                col_names = [c[0] for c in cur.description]
                sample_rows = cur.fetchall()
                cur.close()
                log(f"  Amostra ({len(sample_rows)} registros):")
                for i, row in enumerate(sample_rows):
                    log(f"    [{i+1}]")
                    for cn, val in zip(col_names, row):
                        val_str = str(val) if val is not None else "NULL"
                        log(f"      {cn}: {val_str}")
            except Exception as e:
                log(f"  Erro ao amostrar: {e}")

    # -- 4. Colunas de CPF/CNPJ/OAB em qualquer tabela -----------------------
    log("")
    log("-" * 40)
    log("4. COLUNAS COM CPF/CNPJ/OAB/RG/DOCUMENTO EM TODO O SCHEMA")
    log("-" * 40)
    cur = conn.cursor()
    cur.execute(DISCOVER_CPF_CNPJ_COLS)
    cpf_cols = cur.fetchall()
    cur.close()
    log(f"  Encontradas: {len(cpf_cols)} colunas")
    for table_name, col_name, dtype, dlen in cpf_cols:
        log(f"  SAJ.{table_name}.{col_name} ({dtype}, {dlen})")

    # -- 5. Colunas de VALOR em qualquer tabela -------------------------------
    log("")
    log("-" * 40)
    log("5. COLUNAS DE VALOR (VLCAUSA, etc) EM TODO O SCHEMA")
    log("-" * 40)
    cur = conn.cursor()
    cur.execute(DISCOVER_VALOR_COLS)
    valor_cols = cur.fetchall()
    cur.close()
    log(f"  Encontradas: {len(valor_cols)} colunas")
    for table_name, col_name, dtype, dlen in valor_cols:
        log(f"  SAJ.{table_name}.{col_name} ({dtype}, {dlen})")

    # -- 6. Teste rapido: JOIN processo -> parte (se existir) -----------------
    log("")
    log("-" * 40)
    log("6. TENTATIVA DE JOIN: PROCESSO -> PARTES (amostra de 10)")
    log("-" * 40)

    parte_tables = [t for t in tables if "PARTE" in t and "ADVOG" not in t]
    for pt in parte_tables:
        try:
            cur = conn.cursor()
            cur.execute(DISCOVER_COLUMNS, table_name=pt)
            pt_cols = [c[0] for c in cur.fetchall()]
            cur.close()

            if "CDPROCESSO" not in pt_cols:
                log(f"  SAJ.{pt}: sem CDPROCESSO, pulando JOIN")
                continue

            join_query = f"""
                SELECT PT.*, PC.NUPROCESSO, PC.NUFORMATADO
                FROM SAJ.{pt} PT
                JOIN SAJ.ESPJPROCESSO PC ON PC.CDPROCESSO = PT.CDPROCESSO
                WHERE ROWNUM <= 10
            """
            cur = conn.cursor()
            cur.execute(join_query)
            join_cols = [c[0] for c in cur.description]
            join_rows = cur.fetchall()
            cur.close()

            log(f"  SAJ.{pt} JOIN ESPJPROCESSO -- {len(join_rows)} registros:")
            for i, row in enumerate(join_rows):
                log(f"    [{i+1}]")
                for cn, val in zip(join_cols, row):
                    val_str = str(val) if val is not None else "NULL"
                    log(f"      {cn}: {val_str}")
        except Exception as e:
            log(f"  Erro no JOIN com SAJ.{pt}: {e}")

    # -- 7. Teste: ESAJNOME com outros TPNOME --------------------------------
    log("")
    log("-" * 40)
    log("7. TIPOS DE NOME EM ESAJNOME (TPNOME)")
    log("-" * 40)
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT TPNOME, COUNT(*) AS QTD
            FROM SAJ.ESAJNOME
            GROUP BY TPNOME
            ORDER BY QTD DESC
        """)
        for tpnome, qtd in cur.fetchall():
            log(f"  TPNOME='{tpnome}': {qtd:,} registros")
        cur.close()
    except Exception as e:
        log(f"  Erro: {e}")

    # -- 8. Tabela ESAJPESSOA (dados completos de pessoa) ---------------------
    log("")
    log("-" * 40)
    log("8. COLUNAS DE SAJ.ESAJPESSOA (se existir)")
    log("-" * 40)
    try:
        cur = conn.cursor()
        cur.execute(DISCOVER_COLUMNS, table_name="ESAJPESSOA")
        pessoa_cols = cur.fetchall()
        cur.close()
        if pessoa_cols:
            log(f"  Colunas ({len(pessoa_cols)}):")
            for col_name, dtype, dlen, nullable in pessoa_cols:
                log(f"    {col_name:<35} {dtype:<15} {dlen:<6} {'NULL' if nullable == 'Y' else 'NOT NULL'}")
            # Amostra
            cur = conn.cursor()
            cur.execute("SELECT * FROM SAJ.ESAJPESSOA WHERE ROWNUM <= 5")
            sample_cols = [c[0] for c in cur.description]
            sample_rows = cur.fetchall()
            cur.close()
            log(f"  Amostra ({len(sample_rows)} registros):")
            for i, row in enumerate(sample_rows):
                log(f"    [{i+1}]")
                for cn, val in zip(sample_cols, row):
                    val_str = str(val) if val is not None else "NULL"
                    log(f"      {cn}: {val_str}")
        else:
            log("  Tabela nao encontrada.")
    except Exception as e:
        log(f"  Erro: {e}")

    conn.close()

    # -- Salva relatorio ------------------------------------------------------
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info("Relatorio salvo em: %s", output_path)


def main() -> None:
    """Ponto de entrada: configura logging e executa descoberta."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    output = LOG_DIR / "discovery_partes.txt"

    # Gerencia VPN + tunel SSH automaticamente
    with OracleTunnel(TunnelConfig()):
        discover(output)


if __name__ == "__main__":
    main()
