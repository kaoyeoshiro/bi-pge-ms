"""Script complementar: testa queries finais de partes, advogados e valor da causa.

Resolve o vinculo ESPJPROCPESSOAIMP -> ESPJPROCESSO e testa as queries
de extracao candidatas.
"""

import logging
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from etl.config import LOG_DIR, OracleConfig, TunnelConfig
from etl.extractor import _init_thick_mode
from etl.tunnel import OracleTunnel

import oracledb

logger = logging.getLogger(__name__)

DISCOVER_COLUMNS = """
SELECT COLUMN_NAME, DATA_TYPE, DATA_LENGTH, NULLABLE
FROM ALL_TAB_COLUMNS
WHERE OWNER = 'SAJ'
  AND TABLE_NAME = :table_name
ORDER BY COLUMN_ID
"""


def discover(output_path: Path) -> None:
    """Executa a descoberta complementar."""
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
        try:
            print(msg)
        except UnicodeEncodeError:
            print(msg.encode("ascii", errors="replace").decode("ascii"))

    def run_query(label: str, sql: str, params: dict | None = None, limit: int = 20) -> list:
        """Executa query e loga resultado."""
        log("")
        log("=" * 80)
        log(label)
        log("=" * 80)
        log(f"SQL: {sql.strip()[:500]}...")
        try:
            cur = conn.cursor()
            if params:
                cur.execute(sql, **params)
            else:
                cur.execute(sql)
            col_names = [c[0] for c in cur.description]
            rows = cur.fetchmany(limit)
            cur.close()
            log(f"Colunas: {', '.join(col_names)}")
            log(f"Registros retornados: {len(rows)}")
            for i, row in enumerate(rows):
                log(f"  [{i+1}]")
                for cn, val in zip(col_names, row):
                    val_str = str(val) if val is not None else "NULL"
                    # Truncar valores muito longos
                    if len(val_str) > 200:
                        val_str = val_str[:200] + "..."
                    log(f"    {cn}: {val_str}")
            return rows
        except Exception as e:
            log(f"ERRO: {e}")
            return []

    log(f"Data: {datetime.now():%Y-%m-%d %H:%M:%S}")

    # ── 1. Estrutura de ESPJPROCESSOIMP ──────────────────────────────
    run_query(
        "1. COLUNAS DE ESPJPROCESSOIMP (verificar link com ESPJPROCESSO)",
        DISCOVER_COLUMNS,
        {"table_name": "ESPJPROCESSOIMP"},
    )

    # ── 2. Amostra ESPJPROCESSOIMP com link ─────────────────────────
    run_query(
        "2. AMOSTRA ESPJPROCESSOIMP (10 registros)",
        "SELECT * FROM SAJ.ESPJPROCESSOIMP WHERE ROWNUM <= 10",
    )

    # ── 3. Tentar JOIN ESPJPROCESSOIMP -> ESPJPROCESSO ──────────────
    run_query(
        "3A. JOIN ESPJPROCESSOIMP -> ESPJPROCESSO via CDPROCESSO (se existir)",
        """
        SELECT IMP.CDPROCESSOIMP, IMP.CDPROCESSO,
               PC.NUPROCESSO, PC.NUFORMATADO
        FROM SAJ.ESPJPROCESSOIMP IMP
        JOIN SAJ.ESPJPROCESSO PC ON PC.CDPROCESSO = IMP.CDPROCESSO
        WHERE ROWNUM <= 10
        """,
    )

    # ── 4. JOIN ESPJPROCPESSOAIMP -> ESPJPROCESSOIMP -> ESPJPROCESSO ──
    run_query(
        "3B. CHAIN: ESPJPROCPESSOAIMP -> ESPJPROCESSOIMP -> ESPJPROCESSO (10 registros)",
        """
        SELECT PP.NMPESSOA, PP.DETIPOPARTE, PP.NUCNPJ_CPF, PP.NUOAB,
               PP.TPPESSOA, PP.TPPARTEADVOGADO, PP.TPGENERO,
               IMP.CDPROCESSO,
               PC.NUPROCESSO, PC.NUFORMATADO
        FROM SAJ.ESPJPROCPESSOAIMP PP
        JOIN SAJ.ESPJPROCESSOIMP IMP ON IMP.CDPROCESSOIMP = PP.CDPROCESSOIMP
        JOIN SAJ.ESPJPROCESSO PC ON PC.CDPROCESSO = IMP.CDPROCESSO
        WHERE ROWNUM <= 10
        """,
    )

    # ── 5. Query via ESPJPROCPESSOA (caminho normalizado) ───────────
    run_query(
        "4. ESPJPROCPESSOA + ESAJNOME + ESAJTIPOPARTE + ESAJPESSOADOC (10 registros)",
        """
        SELECT
            PP.CDPROCESSO,
            PC.NUPROCESSO,
            PC.NUFORMATADO,
            PP.NUSEQPARTE,
            PP.CDPESSOA,
            NM.NMPESSOA,
            TP.DEMASCSINGULAR AS TIPO_PARTE,
            TP.TPPARTE AS POLO,
            PP.FLPRINCIPAL,
            P.TPPESSOA,
            P.TPCATEGPESSOA,
            CP.DECATEGPESSOA,
            DOC_CPF.NUDOCUMENTO AS CPF,
            DOC_CNPJ.NUDOCUMENTO AS CNPJ,
            DOC_RG.NUDOCUMENTO AS RG
        FROM SAJ.ESPJPROCPESSOA PP
        JOIN SAJ.ESPJPROCESSO PC ON PC.CDPROCESSO = PP.CDPROCESSO
        JOIN SAJ.ESAJNOME NM ON NM.CDPESSOA = PP.CDPESSOA AND NM.TPNOME = 'N'
        JOIN SAJ.ESAJTIPOPARTE TP ON TP.CDTIPOPARTE = PP.CDTIPOPARTE
        LEFT JOIN SAJ.ESAJPESSOA P ON P.CDPESSOA = PP.CDPESSOA
        LEFT JOIN SAJ.ESPJCATEGPESSOA CP ON CP.CDCATEGPESSOA = P.TPCATEGPESSOA
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
        WHERE ROWNUM <= 10
        """,
    )

    # ── 6. Contagem por polo (autor/reu) ────────────────────────────
    run_query(
        "5. CONTAGEM POR POLO (TPPARTE) EM ESPJPROCPESSOA",
        """
        SELECT TP.TPPARTE AS POLO,
               TP.DEMASCSINGULAR AS TIPO_PARTE,
               COUNT(*) AS QTD
        FROM SAJ.ESPJPROCPESSOA PP
        JOIN SAJ.ESAJTIPOPARTE TP ON TP.CDTIPOPARTE = PP.CDTIPOPARTE
        GROUP BY TP.TPPARTE, TP.DEMASCSINGULAR
        ORDER BY QTD DESC
        """,
        limit=30,
    )

    # ── 7. Tipos de doc em ESAJPESSOADOC ────────────────────────────
    run_query(
        "6. TIPOS DE DOCUMENTO EM ESAJPESSOADOC",
        """
        SELECT SGTIPODOCUMENTO, COUNT(*) AS QTD
        FROM SAJ.ESAJPESSOADOC
        GROUP BY SGTIPODOCUMENTO
        ORDER BY QTD DESC
        """,
    )

    # ── 8. Verificar OAB via ESAJPESSOADOC ──────────────────────────
    run_query(
        "7. OAB EM ESAJPESSOADOC (amostra)",
        """
        SELECT CDPESSOA, SGTIPODOCUMENTO, NUDOCUMENTO, NUDOCFORMATADO
        FROM SAJ.ESAJPESSOADOC
        WHERE SGTIPODOCUMENTO LIKE '%OAB%'
        AND ROWNUM <= 10
        """,
    )

    # ── 9. VLACAO na tabela de processos ────────────────────────────
    run_query(
        "8. VLACAO E VLSENTENCIADO EM ESPJPROCESSO (amostra com valores > 0)",
        """
        SELECT PC.CDPROCESSO, PC.NUPROCESSO, PC.NUFORMATADO,
               PC.VLACAO, PC.VLSENTENCIADO, PC.TPVALOR
        FROM SAJ.ESPJPROCESSO PC
        WHERE PC.VLACAO > 0
        AND ROWNUM <= 15
        """,
    )

    # ── 10. Estatisticas de VLACAO ──────────────────────────────────
    run_query(
        "9. ESTATISTICAS DE VLACAO",
        """
        SELECT
            COUNT(*) AS TOTAL,
            COUNT(VLACAO) AS COM_VLACAO,
            SUM(CASE WHEN VLACAO > 0 THEN 1 ELSE 0 END) AS VLACAO_POSITIVO,
            SUM(CASE WHEN VLACAO = 0 THEN 1 ELSE 0 END) AS VLACAO_ZERO,
            SUM(CASE WHEN VLACAO IS NULL THEN 1 ELSE 0 END) AS VLACAO_NULO,
            MIN(VLACAO) AS MIN_VLACAO,
            MAX(VLACAO) AS MAX_VLACAO,
            COUNT(VLSENTENCIADO) AS COM_VLSENTENCIADO,
            SUM(CASE WHEN VLSENTENCIADO > 0 THEN 1 ELSE 0 END) AS VLSENT_POSITIVO
        FROM SAJ.ESPJPROCESSO
        WHERE CDSITUACAOPROC IN (3, 4, 5)
          AND CDPROCESSOSUP IS NULL
        """,
    )

    # ── 11. Contagem de partes por tipo e com/sem CPF ───────────────
    run_query(
        "10. COBERTURA: PARTES COM/SEM CPF/CNPJ (via ESAJPESSOADOC)",
        """
        SELECT
            COUNT(*) AS TOTAL_PARTES,
            SUM(CASE WHEN DOC.CDPESSOA IS NOT NULL THEN 1 ELSE 0 END) AS COM_DOC,
            SUM(CASE WHEN DOC.CDPESSOA IS NULL THEN 1 ELSE 0 END) AS SEM_DOC
        FROM SAJ.ESPJPROCPESSOA PP
        LEFT JOIN SAJ.ESAJPESSOADOC DOC
            ON DOC.CDPESSOA = PP.CDPESSOA
            AND DOC.SGTIPODOCUMENTO IN ('CPF ', 'CNPJ')
            AND DOC.FLPRINCIPAL = 'S'
        """,
    )

    # ── 12. TOP 10 maiores demandantes (autores com mais processos) ──
    run_query(
        "11. TOP 10 MAIORES DEMANDANTES (polo ativo, mais processos)",
        """
        SELECT NM.NMPESSOA, COUNT(DISTINCT PP.CDPROCESSO) AS QTD_PROCESSOS,
               DOC.NUDOCUMENTO AS CPF_CNPJ
        FROM SAJ.ESPJPROCPESSOA PP
        JOIN SAJ.ESAJTIPOPARTE TP ON TP.CDTIPOPARTE = PP.CDTIPOPARTE
        JOIN SAJ.ESAJNOME NM ON NM.CDPESSOA = PP.CDPESSOA AND NM.TPNOME = 'N'
        LEFT JOIN SAJ.ESAJPESSOADOC DOC
            ON DOC.CDPESSOA = PP.CDPESSOA
            AND DOC.SGTIPODOCUMENTO IN ('CPF ', 'CNPJ')
            AND DOC.FLPRINCIPAL = 'S'
        WHERE TP.TPPARTE = 1
        GROUP BY NM.NMPESSOA, DOC.NUDOCUMENTO
        ORDER BY QTD_PROCESSOS DESC
        FETCH FIRST 10 ROWS ONLY
        """,
    )

    # ── 13. TOP 10 advogados (mais processos) ───────────────────────
    run_query(
        "12. TOP 10 ADVOGADOS (mais processos, via ESPJPROCPESSOAIMP)",
        """
        SELECT PP.NMPESSOA, PP.NUOAB, COUNT(DISTINCT IMP.CDPROCESSO) AS QTD_PROCESSOS
        FROM SAJ.ESPJPROCPESSOAIMP PP
        JOIN SAJ.ESPJPROCESSOIMP IMP ON IMP.CDPROCESSOIMP = PP.CDPROCESSOIMP
        WHERE PP.TPPARTEADVOGADO IS NOT NULL
          AND PP.NUOAB IS NOT NULL
        GROUP BY PP.NMPESSOA, PP.NUOAB
        ORDER BY QTD_PROCESSOS DESC
        FETCH FIRST 10 ROWS ONLY
        """,
    )

    # ── 14. Query candidata final: PARTES_PROCESSO ──────────────────
    run_query(
        "13. QUERY CANDIDATA FINAL: PARTES_PROCESSO (30 registros)",
        """
        SELECT
            PP.CDPROCESSO        AS cd_processo,
            PC.NUPROCESSO        AS numero_processo,
            PC.NUFORMATADO       AS numero_formatado,
            PP.NUSEQPARTE        AS seq_parte,
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
            PC.VLACAO            AS valor_acao,
            PC.VLSENTENCIADO     AS valor_sentenciado,
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
        WHERE PC.CDSITUACAOPROC IN (3, 4, 5)
          AND PC.CDPROCESSOSUP IS NULL
          AND ROWNUM <= 30
        """,
    )

    # ── 15. Advogados via ESPJPROCPESSOAIMP com link ────────────────
    run_query(
        "14. QUERY CANDIDATA: ADVOGADOS VIA ESPJPROCPESSOAIMP (20 registros)",
        """
        SELECT
            IMP.CDPROCESSO       AS cd_processo,
            PC.NUPROCESSO        AS numero_processo,
            PC.NUFORMATADO       AS numero_formatado,
            PP.NUSEQPARTE        AS seq_parte,
            PP.NMPESSOA          AS nome,
            PP.DETIPOPARTE       AS tipo_parte,
            PP.NUCNPJ_CPF        AS cpf_cnpj,
            PP.NUOAB             AS oab,
            PP.TPPESSOA          AS tipo_pessoa,
            PP.TPPARTEADVOGADO   AS tp_advogado,
            PP.TPGENERO          AS genero,
            PP.CDPESSOA          AS cd_pessoa
        FROM SAJ.ESPJPROCPESSOAIMP PP
        JOIN SAJ.ESPJPROCESSOIMP IMP ON IMP.CDPROCESSOIMP = PP.CDPROCESSOIMP
        JOIN SAJ.ESPJPROCESSO PC ON PC.CDPROCESSO = IMP.CDPROCESSO
        WHERE PP.TPPARTEADVOGADO IS NOT NULL
          AND PC.CDSITUACAOPROC IN (3, 4, 5)
          AND PC.CDPROCESSOSUP IS NULL
          AND ROWNUM <= 20
        """,
    )

    # ── 16. Contagem total para estimar volume ──────────────────────
    run_query(
        "15. CONTAGEM: VOLUME ESTIMADO DAS NOVAS TABELAS",
        """
        SELECT
            (SELECT COUNT(*) FROM SAJ.ESPJPROCPESSOA) AS TOTAL_PROCPESSOA,
            (SELECT COUNT(*) FROM SAJ.ESPJPROCPESSOAIMP) AS TOTAL_PROCPESSOAIMP,
            (SELECT COUNT(*)
             FROM SAJ.ESPJPROCPESSOA PP
             JOIN SAJ.ESPJPROCESSO PC ON PC.CDPROCESSO = PP.CDPROCESSO
             WHERE PC.CDSITUACAOPROC IN (3, 4, 5)
               AND PC.CDPROCESSOSUP IS NULL
            ) AS PARTES_ATIVOS,
            (SELECT COUNT(*)
             FROM SAJ.ESPJPROCPESSOAIMP PP
             JOIN SAJ.ESPJPROCESSOIMP IMP ON IMP.CDPROCESSOIMP = PP.CDPROCESSOIMP
             JOIN SAJ.ESPJPROCESSO PC ON PC.CDPROCESSO = IMP.CDPROCESSO
             WHERE PC.CDSITUACAOPROC IN (3, 4, 5)
               AND PC.CDPROCESSOSUP IS NULL
            ) AS PARTES_IMP_ATIVOS
        FROM DUAL
        """,
    )

    conn.close()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info("Relatorio salvo em: %s", output_path)


def main() -> None:
    """Ponto de entrada."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    output = LOG_DIR / "discovery_partes2.txt"

    with OracleTunnel(TunnelConfig()):
        discover(output)


if __name__ == "__main__":
    main()
