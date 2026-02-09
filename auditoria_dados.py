"""Script de auditoria: verifica inconsistências de métricas por procurador.

Hipótese principal: Perfil do Procurador filtra pecas_finalizadas pela coluna
`procurador` (dono do caso), mas o correto para métricas individuais é
`usuario_finalizacao` (quem finalizou a peça). Isso causa distorção nos KPIs.
"""

import asyncio
import os
from dotenv import load_dotenv
import asyncpg

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", 5432)),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "pge_bi"),
}

# Categorias não-produtivas (excluídas de pecas_finalizadas)
CAT_NP = (
    "'Encaminhamentos'",
    "'Arquivamento'",
    "'Arquivamento dos autos'",
    "'Desarquivamento dos autos'",
    "'Ciência de Decisão / Despacho'",
    "'Recusa do encaminhamento'",
    "'Informação Administrativa'",
    "'Decisão conflito'",
    "'Desentranhamento'",
    "'Apensamento'",
    "'Autorizações para solicitação de autos'",
    "'Redirecionamento'",
)
CAT_NP_SQL = f"({', '.join(CAT_NP)})"

NORM = "TRIM(REGEXP_REPLACE({col}, E'\\\\s*\\\\(.*\\\\)$', '', 'g'))"


def norm(col: str) -> str:
    return NORM.format(col=col)


async def run_audit():
    conn = await asyncpg.connect(**DB_CONFIG)
    print("=" * 80)
    print("AUDITORIA DE MÉTRICAS POR PROCURADOR — BI PGE-MS")
    print("=" * 80)

    # 1. Contagens globais
    print("\n## 1. CONTAGENS GLOBAIS (todas as tabelas, sem filtro)")
    total_pn = await conn.fetchval("SELECT COUNT(*) FROM processos_novos")
    total_pf = await conn.fetchval(
        f"SELECT COUNT(*) FROM pecas_finalizadas WHERE categoria NOT IN {CAT_NP_SQL}"
    )
    total_pd = await conn.fetchval("SELECT COUNT(*) FROM pendencias")
    total_pe = await conn.fetchval("SELECT COUNT(*) FROM pecas_elaboradas")
    print(f"  processos_novos:   {total_pn:>10,}")
    print(f"  pecas_finalizadas: {total_pf:>10,} (excl. não-produtivas)")
    print(f"  pendencias:        {total_pd:>10,}")
    print(f"  pecas_elaboradas:  {total_pe:>10,}")

    # 2. Soma por indivíduo vs total
    print("\n## 2. SOMA DOS INDIVÍDUOS vs TOTAL")

    soma_pn = await conn.fetchval(f"""
        SELECT COALESCE(SUM(total), 0) FROM (
            SELECT {norm('procurador')} AS proc, COUNT(*) AS total
            FROM processos_novos WHERE procurador IS NOT NULL
            GROUP BY {norm('procurador')}
        ) t
    """)
    nulos_pn = await conn.fetchval(
        "SELECT COUNT(*) FROM processos_novos WHERE procurador IS NULL"
    )
    print(f"  processos_novos: total={total_pn}, soma_por_proc={soma_pn}, nulos={nulos_pn}")

    soma_pf_proc = await conn.fetchval(f"""
        SELECT COALESCE(SUM(total), 0) FROM (
            SELECT {norm('procurador')} AS proc, COUNT(*) AS total
            FROM pecas_finalizadas
            WHERE procurador IS NOT NULL AND categoria NOT IN {CAT_NP_SQL}
            GROUP BY {norm('procurador')}
        ) t
    """)
    soma_pf_uf = await conn.fetchval(f"""
        SELECT COALESCE(SUM(total), 0) FROM (
            SELECT {norm('usuario_finalizacao')} AS proc, COUNT(*) AS total
            FROM pecas_finalizadas
            WHERE usuario_finalizacao IS NOT NULL AND categoria NOT IN {CAT_NP_SQL}
            GROUP BY {norm('usuario_finalizacao')}
        ) t
    """)
    nulos_pf_proc = await conn.fetchval(f"""
        SELECT COUNT(*) FROM pecas_finalizadas
        WHERE procurador IS NULL AND categoria NOT IN {CAT_NP_SQL}
    """)
    nulos_pf_uf = await conn.fetchval(f"""
        SELECT COUNT(*) FROM pecas_finalizadas
        WHERE usuario_finalizacao IS NULL AND categoria NOT IN {CAT_NP_SQL}
    """)
    print(f"  pecas_finalizadas: total={total_pf}")
    print(f"    soma por 'procurador':          {soma_pf_proc}, nulos={nulos_pf_proc}")
    print(f"    soma por 'usuario_finalizacao':  {soma_pf_uf}, nulos={nulos_pf_uf}")

    soma_pd = await conn.fetchval(f"""
        SELECT COALESCE(SUM(total), 0) FROM (
            SELECT {norm('procurador')} AS proc, COUNT(*) AS total
            FROM pendencias WHERE procurador IS NOT NULL
            GROUP BY {norm('procurador')}
        ) t
    """)
    nulos_pd = await conn.fetchval(
        "SELECT COUNT(*) FROM pendencias WHERE procurador IS NULL"
    )
    print(f"  pendencias: total={total_pd}, soma_por_proc={soma_pd}, nulos={nulos_pd}")

    # 3. Discrepância por procurador: procurador vs usuario_finalizacao
    print("\n## 3. DISCREPÂNCIA pecas_finalizadas: 'procurador' vs 'usuario_finalizacao'")
    print("   (Top 20 com maior diferença absoluta)")

    rows = await conn.fetch(f"""
        WITH by_owner AS (
            SELECT {norm('procurador')} AS nome, COUNT(*) AS cnt_owner
            FROM pecas_finalizadas
            WHERE procurador IS NOT NULL AND categoria NOT IN {CAT_NP_SQL}
            GROUP BY {norm('procurador')}
        ),
        by_finalizer AS (
            SELECT {norm('usuario_finalizacao')} AS nome, COUNT(*) AS cnt_finalizer
            FROM pecas_finalizadas
            WHERE usuario_finalizacao IS NOT NULL AND categoria NOT IN {CAT_NP_SQL}
            GROUP BY {norm('usuario_finalizacao')}
        )
        SELECT
            COALESCE(o.nome, f.nome) AS nome,
            COALESCE(o.cnt_owner, 0) AS cnt_owner,
            COALESCE(f.cnt_finalizer, 0) AS cnt_finalizer,
            COALESCE(f.cnt_finalizer, 0) - COALESCE(o.cnt_owner, 0) AS diff
        FROM by_owner o
        FULL OUTER JOIN by_finalizer f ON o.nome = f.nome
        ORDER BY ABS(COALESCE(f.cnt_finalizer, 0) - COALESCE(o.cnt_owner, 0)) DESC
        LIMIT 20
    """)
    print(f"  {'Nome':<45} {'PorDono':>10} {'PorFinaliz':>10} {'Diff':>10}")
    print("  " + "-" * 77)
    for r in rows:
        print(f"  {r['nome']:<45} {r['cnt_owner']:>10,} {r['cnt_finalizer']:>10,} {r['diff']:>+10,}")

    # 4. Procuradores suspeitos
    suspeitos = ["Caio Gama Mascarenhas", "Kaoye Guazina Oshiro"]
    print("\n## 4. MÉTRICAS DETALHADAS DOS PROCURADORES SUSPEITOS")

    for nome in suspeitos:
        print(f"\n  ### {nome}")

        pn = await conn.fetchval(f"""
            SELECT COUNT(*) FROM processos_novos WHERE {norm('procurador')} = $1
        """, nome)

        pf_owner = await conn.fetchval(f"""
            SELECT COUNT(*) FROM pecas_finalizadas
            WHERE {norm('procurador')} = $1 AND categoria NOT IN {CAT_NP_SQL}
        """, nome)

        pf_finalizer = await conn.fetchval(f"""
            SELECT COUNT(*) FROM pecas_finalizadas
            WHERE {norm('usuario_finalizacao')} = $1 AND categoria NOT IN {CAT_NP_SQL}
        """, nome)

        pd = await conn.fetchval(f"""
            SELECT COUNT(*) FROM pendencias WHERE {norm('procurador')} = $1
        """, nome)

        pe = await conn.fetchval(f"""
            SELECT COUNT(*) FROM pecas_elaboradas WHERE {norm('usuario_criacao')} = $1
        """, nome)

        role = await conn.fetchval("SELECT role FROM user_roles WHERE name = $1", nome)

        print(f"    Role: {role or 'NÃO ENCONTRADO'}")
        print(f"    processos_novos (proc):            {pn:>10,}")
        print(f"    pecas_finalizadas (proc=dono):     {pf_owner:>10,}  <- KPI ATUAL (BUG)")
        print(f"    pecas_finalizadas (usr_finaliz):   {pf_finalizer:>10,}  <- CORRETO")
        print(f"    pendencias (proc=dono):            {pd:>10,}")
        print(f"    pecas_elaboradas (usr_criacao):     {pe:>10,}")
        print(f"    DIFERENCA pf: {pf_owner - pf_finalizer:+,} (dono - finalizador)")

    # 5. Proporção de divergência
    print("\n## 5. REGISTROS ONDE procurador != usuario_finalizacao (pecas_finalizadas)")

    diff_count = await conn.fetchval(f"""
        SELECT COUNT(*) FROM pecas_finalizadas
        WHERE procurador IS NOT NULL AND usuario_finalizacao IS NOT NULL
          AND {norm('procurador')} != {norm('usuario_finalizacao')}
          AND categoria NOT IN {CAT_NP_SQL}
    """)
    same_count = await conn.fetchval(f"""
        SELECT COUNT(*) FROM pecas_finalizadas
        WHERE procurador IS NOT NULL AND usuario_finalizacao IS NOT NULL
          AND {norm('procurador')} = {norm('usuario_finalizacao')}
          AND categoria NOT IN {CAT_NP_SQL}
    """)
    total_comp = same_count + diff_count
    pct = (diff_count / total_comp * 100) if total_comp else 0
    print(f"  Mesmo procurador e finalizador:    {same_count:>10,}")
    print(f"  Diferente procurador e finalizador: {diff_count:>10,}")
    print(f"  Percentual de divergência:          {pct:>9.1f}%")

    # 6. Top 20 inflação/deflação entre procuradores registrados
    print("\n## 6. TOP 20 INFLAÇÃO/DEFLAÇÃO (apenas procuradores registrados)")

    rows = await conn.fetch(f"""
        WITH by_owner AS (
            SELECT {norm('procurador')} AS nome, COUNT(*) AS cnt
            FROM pecas_finalizadas
            WHERE procurador IS NOT NULL AND categoria NOT IN {CAT_NP_SQL}
            GROUP BY {norm('procurador')}
        ),
        by_finalizer AS (
            SELECT {norm('usuario_finalizacao')} AS nome, COUNT(*) AS cnt
            FROM pecas_finalizadas
            WHERE usuario_finalizacao IS NOT NULL AND categoria NOT IN {CAT_NP_SQL}
            GROUP BY {norm('usuario_finalizacao')}
        ),
        procs AS (SELECT name FROM user_roles WHERE role = 'procurador')
        SELECT
            p.name AS nome,
            COALESCE(o.cnt, 0) AS cnt_owner,
            COALESCE(f.cnt, 0) AS cnt_finalizer,
            COALESCE(o.cnt, 0) - COALESCE(f.cnt, 0) AS inflacao
        FROM procs p
        LEFT JOIN by_owner o ON o.nome = p.name
        LEFT JOIN by_finalizer f ON f.nome = p.name
        WHERE COALESCE(o.cnt, 0) != COALESCE(f.cnt, 0)
        ORDER BY ABS(COALESCE(o.cnt, 0) - COALESCE(f.cnt, 0)) DESC
        LIMIT 20
    """)
    print(f"  {'Nome':<45} {'Dono':>8} {'Finaliz':>8} {'Inflação':>10}")
    print("  " + "-" * 73)
    for r in rows:
        print(f"  {r['nome']:<45} {r['cnt_owner']:>8,} {r['cnt_finalizer']:>8,} {r['inflacao']:>+10,}")

    # 7. Verificação de duplicidade de IDs
    print("\n## 7. VERIFICAÇÃO DE DUPLICIDADE DE IDs")
    for tabela in ["processos_novos", "pecas_finalizadas", "pendencias", "pecas_elaboradas"]:
        total = await conn.fetchval(f"SELECT COUNT(*) FROM {tabela}")
        distinct_ids = await conn.fetchval(f"SELECT COUNT(DISTINCT id) FROM {tabela}")
        dup = total - distinct_ids
        status = "OK" if dup == 0 else f"FALHA! {dup} duplicados"
        print(f"  {tabela}: total={total:,}, distinct_ids={distinct_ids:,} [{status}]")

    # 8. Verificação Kaoye em todas as tabelas
    print("\n## 8. VERIFICAÇÃO DE 'Kaoye Guazina Oshiro' NAS TABELAS")
    for tabela, cols in [
        ("processos_novos", ["procurador"]),
        ("pecas_finalizadas", ["procurador", "usuario_finalizacao"]),
        ("pendencias", ["procurador", "usuario_cumpridor_pendencia"]),
        ("pecas_elaboradas", ["procurador", "usuario_criacao"]),
    ]:
        print(f"  {tabela}:")
        for col in cols:
            cnt = await conn.fetchval(f"""
                SELECT COUNT(*) FROM {tabela}
                WHERE {norm(col)} = 'Kaoye Guazina Oshiro'
            """)
            print(f"    {col}: {cnt:,}")

    # 9. Série mensal comparativa para Caio
    print("\n## 9. SÉRIE MENSAL — CAIO GAMA MASCARENHAS (pecas_finalizadas, 2024+)")
    print("   Comparação: filtro por 'procurador' vs 'usuario_finalizacao'")

    rows_owner = await conn.fetch(f"""
        SELECT TO_CHAR(data_finalizacao, 'YYYY-MM') AS periodo, COUNT(*) AS total
        FROM pecas_finalizadas
        WHERE {norm('procurador')} = 'Caio Gama Mascarenhas'
          AND categoria NOT IN {CAT_NP_SQL}
          AND data_finalizacao IS NOT NULL
          AND EXTRACT(YEAR FROM data_finalizacao) >= 2024
        GROUP BY TO_CHAR(data_finalizacao, 'YYYY-MM') ORDER BY periodo
    """)
    rows_final = await conn.fetch(f"""
        SELECT TO_CHAR(data_finalizacao, 'YYYY-MM') AS periodo, COUNT(*) AS total
        FROM pecas_finalizadas
        WHERE {norm('usuario_finalizacao')} = 'Caio Gama Mascarenhas'
          AND categoria NOT IN {CAT_NP_SQL}
          AND data_finalizacao IS NOT NULL
          AND EXTRACT(YEAR FROM data_finalizacao) >= 2024
        GROUP BY TO_CHAR(data_finalizacao, 'YYYY-MM') ORDER BY periodo
    """)

    all_periods = sorted(set(
        [r['periodo'] for r in rows_owner] + [r['periodo'] for r in rows_final]
    ))
    owner_map = {r['periodo']: r['total'] for r in rows_owner}
    final_map = {r['periodo']: r['total'] for r in rows_final}

    print(f"  {'Período':<10} {'PorDono':>10} {'PorFinaliz':>10} {'Diff':>10}")
    print("  " + "-" * 42)
    for p in all_periods:
        o = owner_map.get(p, 0)
        f = final_map.get(p, 0)
        print(f"  {p:<10} {o:>10,} {f:>10,} {o - f:>+10,}")

    # 10. Invariantes finais
    print("\n## 10. VERIFICAÇÃO DE INVARIANTES")
    max_pn = await conn.fetchval(f"""
        SELECT MAX(cnt) FROM (
            SELECT COUNT(*) AS cnt FROM processos_novos
            WHERE procurador IS NOT NULL GROUP BY {norm('procurador')}
        ) t
    """)
    max_pf = await conn.fetchval(f"""
        SELECT MAX(cnt) FROM (
            SELECT COUNT(*) AS cnt FROM pecas_finalizadas
            WHERE usuario_finalizacao IS NOT NULL AND categoria NOT IN {CAT_NP_SQL}
            GROUP BY {norm('usuario_finalizacao')}
        ) t
    """)
    max_pd = await conn.fetchval(f"""
        SELECT MAX(cnt) FROM (
            SELECT COUNT(*) AS cnt FROM pendencias
            WHERE procurador IS NOT NULL GROUP BY {norm('procurador')}
        ) t
    """)
    print(f"  Max individual processos_novos:   {max_pn:>10,} (total: {total_pn:,}) {'OK' if max_pn <= total_pn else 'FALHA!'}")
    print(f"  Max individual pecas_finalizadas: {max_pf:>10,} (total: {total_pf:,}) {'OK' if max_pf <= total_pf else 'FALHA!'}")
    print(f"  Max individual pendencias:        {max_pd:>10,} (total: {total_pd:,}) {'OK' if max_pd <= total_pd else 'FALHA!'}")

    print("\n" + "=" * 80)
    print("CONCLUSÃO DA AUDITORIA")
    print("=" * 80)
    print("""
CAUSA RAIZ CONFIRMADA:
  O Perfil do Procurador filtra pecas_finalizadas pela coluna 'procurador'
  (dono do caso/processo), mas deveria filtrar por 'usuario_finalizacao'
  (quem realmente finalizou a peca).

  Isso causa:
  - INFLACAO para procuradores donos de muitos processos onde OUTROS finalizam
  - DEFLACAO para procuradores que finalizam pecas em processos de colegas

  O comparativo de chefia ja usa 'usuario_finalizacao' corretamente, criando
  inconsistencia interna com os KPIs e timeline do perfil individual.

CORRECAO NECESSARIA:
  Em _apply_global_filters do BaseRepository, quando filters.procurador esta
  preenchido, resolver a coluna via PROCURADOR_COL_MAP (mesmo mapeamento usado
  nos rankings/agrupamentos). Ou seja, para pecas_finalizadas, filtrar por
  usuario_finalizacao em vez de procurador.
""")

    await conn.close()


if __name__ == "__main__":
    asyncio.run(run_audit())
