"""Queries SQL para extração de dados do Oracle SAJ/SPJMS.

Cada query retorna os campos necessários para o BI com as PKs Oracle
(cd_processo, cd_documento, cd_pendencia) para suportar upsert no PostgreSQL.

A chefia é extraída crua (CHEF.DECHEFIA) — a normalização (PS, PAT) é feita
no PostgreSQL via normalize_chefia_expr().
"""

# ── Processos novos ──────────────────────────────────────────────────

PROCESSOS_NOVOS = """
SELECT
    PC.CDPROCESSO       AS cd_processo,
    CHEF.DECHEFIA       AS chefia,
    PC.DTUSUINCLUSAO    AS data,
    PC.CDPROCESSO       AS codigo_processo,
    PC.NUPROCESSO       AS numero_processo,
    PC.NUFORMATADO      AS numero_formatado,
    NOME.NMPESSOA       AS procurador,
    PC.VLACAO           AS valor_acao,
    PC.TPVALOR          AS tipo_valor
FROM
    SAJ.ESPJPROCESSO PC
    JOIN SAJ.ESPJDISTPROCESSO DP ON DP.CDPROCESSO = PC.CDPROCESSO
        AND DP.FLULTDIST = 'S'
    JOIN SAJ.ESPJVARDIST VD ON VD.CDVARDIST = DP.CDVARDIST
    JOIN SAJ.ESPJCHEFIA CHEF ON VD.CDCHEFIA = CHEF.CDCHEFIA
    LEFT JOIN SAJ.ESAJNOME NOME ON NOME.CDPESSOA = DP.CDPROCURADOR
        AND NOME.TPNOME = 'N'
WHERE
    PC.DTUSUINCLUSAO >= :start_date
    AND PC.DTUSUINCLUSAO < :end_date
    AND PC.CDPROCESSOSUP IS NULL
    AND PC.CDSITUACAOPROC IN (3, 4, 5)
"""

# ── Peças elaboradas ─────────────────────────────────────────────────

PECAS_ELABORADAS = """
SELECT
    E.CDDOCUMENTO       AS cd_documento,
    CHEF.DECHEFIA        AS chefia,
    E.DTCRIACAO          AS data,
    USU.NMUSUARIO        AS usuario_criacao,
    CAT.NMCATEGORIA      AS categoria,
    MDL.NMMODELO         AS modelo,
    P.NUPROCESSO         AS numero_processo,
    P.NUFORMATADO        AS numero_formatado,
    NOME.NMPESSOA        AS procurador
FROM
    SAJ.EEDTDOCEMITIDO E
    JOIN SAJ.ESPJPROCESSO P ON E.CDPROCESSO = P.CDPROCESSO
    JOIN SAJ.ESPJDISTPROCESSO DP ON DP.CDPROCESSO = P.CDPROCESSO
        AND DP.FLULTDIST = 'S'
    JOIN SAJ.ESPJVARDIST V ON V.CDVARDIST = DP.CDVARDIST
    JOIN SAJ.ESPJCHEFIA CHEF ON V.CDCHEFIA = CHEF.CDCHEFIA
    JOIN SAJ.EEDTCATEGORIA CAT ON E.CDCATEGORIA = CAT.CDCATEGORIA
    JOIN SAJ.ESEGUSUARIO USU ON E.CDUSUARIOCRIACAO = USU.CDUSUARIO
    JOIN SAJ.EEDTMODELO MDL ON E.CDMODELO = MDL.CDMODELO
    LEFT JOIN SAJ.ESAJNOME NOME ON NOME.CDPESSOA = DP.CDPROCURADOR
        AND NOME.TPNOME = 'N'
WHERE
    V.FLFORAUSO = 'N'
    AND E.DTCRIACAO >= :start_date
    AND E.DTCRIACAO < :end_date
"""

# ── Peças finalizadas ────────────────────────────────────────────────

PECAS_FINALIZADAS = """
SELECT
    E.CDDOCUMENTO        AS cd_documento,
    CHEF.DECHEFIA         AS chefia,
    E.DTFINALIZACAO       AS data_finalizacao,
    USUFIN.NMUSUARIO      AS usuario_finalizacao,
    CAT.NMCATEGORIA       AS categoria,
    MDL.NMMODELO          AS modelo,
    P.NUPROCESSO          AS numero_processo,
    P.NUFORMATADO         AS numero_formatado,
    NOME.NMPESSOA         AS procurador
FROM
    SAJ.EEDTDOCEMITIDO E
    JOIN SAJ.ESPJPROCESSO P ON E.CDPROCESSO = P.CDPROCESSO
    JOIN SAJ.ESPJDISTPROCESSO DP ON DP.CDPROCESSO = P.CDPROCESSO
        AND DP.FLULTDIST = 'S'
    JOIN SAJ.ESPJVARDIST V ON V.CDVARDIST = DP.CDVARDIST
    JOIN SAJ.ESPJCHEFIA CHEF ON V.CDCHEFIA = CHEF.CDCHEFIA
    JOIN SAJ.EEDTCATEGORIA CAT ON E.CDCATEGORIA = CAT.CDCATEGORIA
    JOIN SAJ.EEDTMODELO MDL ON E.CDMODELO = MDL.CDMODELO
    JOIN SAJ.ESEGUSUARIO USUFIN ON E.CDUSUULTALTERACAO = USUFIN.CDUSUARIO
    LEFT JOIN SAJ.ESAJNOME NOME ON NOME.CDPESSOA = DP.CDPROCURADOR
        AND NOME.TPNOME = 'N'
WHERE
    E.TPEXCLUSAO IS NULL
    AND E.DTFINALIZACAO IS NOT NULL
    AND V.FLFORAUSO = 'N'
    AND E.DTFINALIZACAO >= :start_date
    AND E.DTFINALIZACAO < :end_date
"""

# ── Pendências ───────────────────────────────────────────────────────

PENDENCIAS = """
SELECT
    P.CDPENDENCIA         AS cd_pendencia,
    CHEF.DECHEFIA          AS chefia,
    P.DTUSUINCLUSAO        AS data,
    PC.NUPROCESSO          AS numero_processo,
    PC.NUFORMATADO         AS numero_formatado,
    A.DEAREA               AS area,
    NOME.NMPESSOA          AS procurador,
    U.NMUSUARIO            AS usuario_cumpridor_pendencia,
    EC.NMCATEGORIA         AS categoria,
    C.DECATEGORIAPEND      AS categoria_pendencia
FROM
    SAJ.ESPJPENDENCIAPRAZO P
    JOIN SAJ.ESPJDISTPENDENCIA DIST ON DIST.CDPENDENCIA = P.CDPENDENCIA
        AND DIST.FLULTDIST = 'S'
    JOIN SAJ.ESPJCATEGORIAPEND C ON P.CDCATEGORIAPEND = C.CDCATEGORIAPEND
    JOIN SAJ.ESPJPROCESSO PC ON PC.CDPROCESSO = P.CDPROCESSO
    JOIN SAJ.ESPJAREA A ON PC.CDAREA = A.CDAREA
    JOIN SAJ.ESEGUSUARIO U ON P.CDUSUARIOCUMP = U.CDUSUARIO
    JOIN SAJ.ESPJVARDIST VD ON VD.CDVARDIST = DIST.CDVARDIST
    JOIN SAJ.ESPJCHEFIA CHEF ON VD.CDCHEFIA = CHEF.CDCHEFIA
    JOIN SAJ.EEDTCATEGORIA EC ON P.CDCATEGORIA = EC.CDCATEGORIA
    JOIN SAJ.ESPJPROCURADORIA PROC ON VD.CDPROCURADORIA = PROC.CDPROCURADORIA
    JOIN SAJ.ESAJNOME NOME ON NOME.CDPESSOA = DIST.CDPROCURADOR
        AND NOME.TPNOME = 'N'
WHERE
    P.CDCATEGORIAPEND IN (3, 4)
    AND P.FLEXCLUIDA = 'N'
    AND P.FLMOVEXCLUIDA = 'N'
    AND P.DTUSUINCLUSAO >= :start_date
    AND P.DTUSUINCLUSAO < :end_date
"""

# ── Assuntos (árvore completa) ───────────────────────────────────────

ASSUNTOS = """
SELECT
    A.CDASSUNTO           AS codigo,
    A.CDASSUNTOPAI        AS codigo_pai,
    A.DEASSUNTO           AS nome,
    A.DEASSUNTOCONSULTA   AS descricao,
    A.NUNIVEL             AS nivel,
    A.NUASSUNTOFORMATADO  AS numero_fmt
FROM
    SAJ.ESPJASSUNTO A
"""

# ── Vínculos processo-assunto ────────────────────────────────────────

PROCESSO_ASSUNTOS = """
SELECT
    P.NUPROCESSO          AS numero_processo,
    PA.CDASSUNTO          AS codigo_assunto,
    PA.FLPRINCIPAL        AS assunto_principal
FROM
    SAJ.ESPJPROCASSUNTO PA
    JOIN SAJ.ESPJPROCESSO P ON PA.CDPROCESSO = P.CDPROCESSO
    JOIN SAJ.ESPJDISTPROCESSO DP ON DP.CDPROCESSO = P.CDPROCESSO
        AND DP.FLULTDIST = 'S'
    JOIN SAJ.ESPJVARDIST V ON V.CDVARDIST = DP.CDVARDIST
WHERE
    V.FLFORAUSO = 'N'
    AND DP.DTDISTRIBUICAO >= :start_date
    AND DP.DTDISTRIBUICAO < :end_date
"""

# ── Chefias distintas (para verificação) ─────────────────────────────

DISCOVER_CHEFIAS = """
SELECT DISTINCT CHEF.DECHEFIA AS chefia
FROM SAJ.ESPJCHEFIA CHEF
ORDER BY CHEF.DECHEFIA
"""

# ── Mapeamentos ──────────────────────────────────────────────────────

TABLE_QUERIES: dict[str, str] = {
    "processos_novos": PROCESSOS_NOVOS,
    "pecas_elaboradas": PECAS_ELABORADAS,
    "pecas_finalizadas": PECAS_FINALIZADAS,
    "pendencias": PENDENCIAS,
}

TABLE_ORACLE_PK: dict[str, str] = {
    "processos_novos": "cd_processo",
    "pecas_elaboradas": "cd_documento",
    "pecas_finalizadas": "cd_documento",
    "pendencias": "cd_pendencia",
}
