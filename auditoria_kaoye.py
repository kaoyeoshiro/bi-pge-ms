"""Verifica produção de Kaoye Guazina Oshiro por ano (2021-2026)."""

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

NORM = r"TRIM(REGEXP_REPLACE({col}, E'\\s*\\(.*\\)$', '', 'g'))"
CAT_NP = (
    "('Encaminhamentos','Arquivamento','Arquivamento dos autos',"
    "'Desarquivamento dos autos','Ciência de Decisão / Despacho',"
    "'Recusa do encaminhamento','Informação Administrativa',"
    "'Decisão conflito','Desentranhamento','Apensamento',"
    "'Autorizações para solicitação de autos','Redirecionamento')"
)


def norm(col: str) -> str:
    return NORM.format(col=col)


async def main():
    conn = await asyncpg.connect(**DB_CONFIG)
    nome = "Kaoye Guazina Oshiro"

    # 1. Pecas finalizadas por ano (usuario_finalizacao)
    print("=== PECAS FINALIZADAS por ano (usuario_finalizacao) ===")
    rows = await conn.fetch(
        f"SELECT EXTRACT(YEAR FROM data_finalizacao)::int AS ano, COUNT(*) AS total "
        f"FROM pecas_finalizadas "
        f"WHERE {norm('usuario_finalizacao')} = $1 "
        f"  AND categoria NOT IN {CAT_NP} "
        f"  AND data_finalizacao IS NOT NULL "
        f"GROUP BY EXTRACT(YEAR FROM data_finalizacao) ORDER BY ano",
        nome,
    )
    for r in rows:
        print(f"  {r['ano']}: {r['total']:>8,}")

    # 2. Processos novos por ano
    print("\n=== PROCESSOS NOVOS por ano (procurador) ===")
    rows = await conn.fetch(
        f"SELECT EXTRACT(YEAR FROM data)::int AS ano, COUNT(*) AS total "
        f"FROM processos_novos "
        f"WHERE {norm('procurador')} = $1 AND data IS NOT NULL "
        f"GROUP BY EXTRACT(YEAR FROM data) ORDER BY ano",
        nome,
    )
    for r in rows:
        print(f"  {r['ano']}: {r['total']:>8,}")

    # 3. Pendencias por ano
    print("\n=== PENDENCIAS por ano (procurador) ===")
    rows = await conn.fetch(
        f"SELECT EXTRACT(YEAR FROM data)::int AS ano, COUNT(*) AS total "
        f"FROM pendencias "
        f"WHERE {norm('procurador')} = $1 AND data IS NOT NULL "
        f"GROUP BY EXTRACT(YEAR FROM data) ORDER BY ano",
        nome,
    )
    for r in rows:
        print(f"  {r['ano']}: {r['total']:>8,}")

    # 4. Pecas elaboradas por ano
    print("\n=== PECAS ELABORADAS por ano (usuario_criacao) ===")
    rows = await conn.fetch(
        f"SELECT EXTRACT(YEAR FROM data)::int AS ano, COUNT(*) AS total "
        f"FROM pecas_elaboradas "
        f"WHERE {norm('usuario_criacao')} = $1 AND data IS NOT NULL "
        f"GROUP BY EXTRACT(YEAR FROM data) ORDER BY ano",
        nome,
    )
    for r in rows:
        print(f"  {r['ano']}: {r['total']:>8,}")

    # 5. Media geral de procuradores por ano (pecas_finalizadas)
    print("\n=== MEDIA GERAL procuradores pecas_finalizadas por ano ===")
    rows = await conn.fetch(
        f"WITH por_proc_ano AS ( "
        f"  SELECT {norm('usuario_finalizacao')} AS proc, "
        f"    EXTRACT(YEAR FROM data_finalizacao)::int AS ano, "
        f"    COUNT(*) AS total "
        f"  FROM pecas_finalizadas "
        f"  WHERE usuario_finalizacao IS NOT NULL "
        f"    AND categoria NOT IN {CAT_NP} "
        f"    AND data_finalizacao IS NOT NULL "
        f"    AND {norm('usuario_finalizacao')} IN "
        f"      (SELECT name FROM user_roles WHERE role = 'procurador') "
        f"  GROUP BY {norm('usuario_finalizacao')}, "
        f"    EXTRACT(YEAR FROM data_finalizacao) "
        f") "
        f"SELECT ano, ROUND(AVG(total)) AS media, "
        f"  MIN(total) AS min_val, MAX(total) AS max_val, "
        f"  COUNT(*) AS n_procs "
        f"FROM por_proc_ano "
        f"WHERE ano BETWEEN 2021 AND 2026 "
        f"GROUP BY ano ORDER BY ano"
    )
    print(f"  {'Ano':<6} {'Media':>8} {'Min':>8} {'Max':>8} {'#Procs':>8}")
    for r in rows:
        print(
            f"  {r['ano']:<6} {r['media']:>8} {r['min_val']:>8,} "
            f"{r['max_val']:>8,} {r['n_procs']:>8}"
        )

    # 6. Rank de Kaoye entre procuradores (pecas_finalizadas)
    print("\n=== RANK de Kaoye entre procuradores (pecas_finalizadas) ===")
    rows = await conn.fetch(
        f"WITH por_proc_ano AS ( "
        f"  SELECT {norm('usuario_finalizacao')} AS proc, "
        f"    EXTRACT(YEAR FROM data_finalizacao)::int AS ano, "
        f"    COUNT(*) AS total "
        f"  FROM pecas_finalizadas "
        f"  WHERE usuario_finalizacao IS NOT NULL "
        f"    AND categoria NOT IN {CAT_NP} "
        f"    AND data_finalizacao IS NOT NULL "
        f"    AND {norm('usuario_finalizacao')} IN "
        f"      (SELECT name FROM user_roles WHERE role = 'procurador') "
        f"  GROUP BY {norm('usuario_finalizacao')}, "
        f"    EXTRACT(YEAR FROM data_finalizacao) "
        f"), "
        f"ranked AS ( "
        f"  SELECT *, "
        f"    RANK() OVER (PARTITION BY ano ORDER BY total DESC) AS rank, "
        f"    COUNT(*) OVER (PARTITION BY ano) AS total_procs "
        f"  FROM por_proc_ano "
        f") "
        f"SELECT ano, total, rank, total_procs "
        f"FROM ranked "
        f"WHERE proc = $1 AND ano BETWEEN 2021 AND 2026 "
        f"ORDER BY ano",
        nome,
    )
    print(f"  {'Ano':<6} {'Total':>8} {'Rank':>6} {'De':>6}")
    for r in rows:
        print(
            f"  {r['ano']:<6} {r['total']:>8,} "
            f"{r['rank']:>6} {r['total_procs']:>6}"
        )

    # 7. Série mensal detalhada 2021-2023 (pecas_finalizadas)
    print("\n=== SERIE MENSAL pecas_finalizadas 2021-2023 (usuario_finalizacao) ===")
    rows = await conn.fetch(
        f"SELECT TO_CHAR(data_finalizacao, 'YYYY-MM') AS periodo, COUNT(*) AS total "
        f"FROM pecas_finalizadas "
        f"WHERE {norm('usuario_finalizacao')} = $1 "
        f"  AND categoria NOT IN {CAT_NP} "
        f"  AND data_finalizacao IS NOT NULL "
        f"  AND EXTRACT(YEAR FROM data_finalizacao) BETWEEN 2021 AND 2023 "
        f"GROUP BY TO_CHAR(data_finalizacao, 'YYYY-MM') ORDER BY periodo",
        nome,
    )
    for r in rows:
        print(f"  {r['periodo']}: {r['total']:>6,}")

    # 8. Chefia de Kaoye
    print("\n=== CHEFIA de Kaoye (processos_novos) ===")
    rows = await conn.fetch(
        f"SELECT chefia, COUNT(*) AS total "
        f"FROM processos_novos "
        f"WHERE {norm('procurador')} = $1 "
        f"GROUP BY chefia ORDER BY total DESC LIMIT 5",
        nome,
    )
    for r in rows:
        print(f"  {r['chefia']}: {r['total']:>6,}")

    await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
