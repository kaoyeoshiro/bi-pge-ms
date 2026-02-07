"""Gera relatório completo sobre os dados migrados para PostgreSQL.

Consulta o banco pge_bi e produz um relatório em Markdown com:
- Inventário de dados (tabelas, colunas, tipos, contagens)
- Estatísticas descritivas
- Correlações entre tabelas
"""

import logging
from pathlib import Path
from datetime import datetime

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

import os

# Configuração
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

load_dotenv(Path(__file__).parent / ".env")

OUTPUT_FILE = Path(__file__).parent / "relatorio_dados.md"


def build_connection_string() -> str:
    """Monta a string de conexão PostgreSQL a partir das variáveis de ambiente."""
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    user = os.getenv("DB_USER", "postgres")
    password = os.getenv("DB_PASSWORD", "")
    dbname = os.getenv("DB_NAME", "pge_bi")
    return f"postgresql://{user}:{password}@{host}:{port}/{dbname}"


def query_df(engine, sql: str) -> pd.DataFrame:
    """Executa uma query SQL e retorna um DataFrame."""
    with engine.connect() as conn:
        return pd.read_sql(text(sql), conn)


def query_scalar(engine, sql: str):
    """Executa uma query SQL e retorna um valor escalar."""
    with engine.connect() as conn:
        result = conn.execute(text(sql))
        return result.scalar()


def df_to_markdown(df: pd.DataFrame) -> str:
    """Converte DataFrame para tabela Markdown."""
    return df.to_markdown(index=False)


def generate_section_inventory(engine) -> str:
    """Gera seção de inventário de dados."""
    logger.info("Gerando inventário de dados...")
    sections = []
    sections.append("## 1. Inventário de Dados\n")

    # Contagem geral
    tables = ["processos_novos", "pecas_elaboradas", "pendencias", "pecas_finalizadas"]
    counts = []
    for table in tables:
        count = query_scalar(engine, f"SELECT COUNT(*) FROM {table}")
        counts.append({"Tabela": table, "Registros": f"{count:,}"})

    total = sum(int(c["Registros"].replace(",", "")) for c in counts)
    counts.append({"Tabela": "**TOTAL**", "Registros": f"**{total:,}**"})

    sections.append("### 1.1 Contagem de Registros\n")
    sections.append(df_to_markdown(pd.DataFrame(counts)))
    sections.append("")

    # Schema detalhado
    sections.append("\n### 1.2 Schema das Tabelas\n")

    for table in tables:
        df_schema = query_df(engine, f"""
            SELECT
                column_name AS "Coluna",
                data_type AS "Tipo PostgreSQL",
                character_maximum_length AS "Tamanho Máx",
                is_nullable AS "Nulo?"
            FROM information_schema.columns
            WHERE table_name = '{table}'
            AND table_schema = 'public'
            ORDER BY ordinal_position
        """)
        sections.append(f"\n#### {table}\n")
        sections.append(df_to_markdown(df_schema))
        sections.append("")

    # Valores nulos por coluna
    sections.append("\n### 1.3 Valores Nulos por Tabela\n")

    for table in tables:
        df_cols = query_df(engine, f"""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = '{table}'
            AND table_schema = 'public'
            AND column_name != 'id'
            ORDER BY ordinal_position
        """)

        null_parts = []
        for col in df_cols["column_name"]:
            null_count = query_scalar(engine, f"""
                SELECT COUNT(*) FROM {table} WHERE {col} IS NULL
            """)
            total_count = query_scalar(engine, f"SELECT COUNT(*) FROM {table}")
            pct = (null_count / total_count * 100) if total_count > 0 else 0
            null_parts.append({
                "Coluna": col,
                "Nulos": f"{null_count:,}",
                "% Nulos": f"{pct:.2f}%",
            })

        sections.append(f"\n#### {table}\n")
        sections.append(df_to_markdown(pd.DataFrame(null_parts)))
        sections.append("")

    return "\n".join(sections)


def generate_section_statistics(engine) -> str:
    """Gera seção de estatísticas descritivas."""
    logger.info("Gerando estatísticas descritivas...")
    sections = []
    sections.append("## 2. Estatísticas Descritivas\n")

    # Distribuição temporal
    sections.append("### 2.1 Distribuição Temporal\n")

    # Processos novos por ano
    df_year = query_df(engine, """
        SELECT
            EXTRACT(YEAR FROM data) AS "Ano",
            COUNT(*) AS "Processos Novos"
        FROM processos_novos
        WHERE data IS NOT NULL
        GROUP BY EXTRACT(YEAR FROM data)
        ORDER BY "Ano"
    """)
    sections.append("#### Processos Novos por Ano\n")
    sections.append(df_to_markdown(df_year))
    sections.append("")

    # Peças elaboradas por ano
    df_pecas_ano = query_df(engine, """
        SELECT
            EXTRACT(YEAR FROM data) AS "Ano",
            COUNT(*) AS "Peças Elaboradas"
        FROM pecas_elaboradas
        WHERE data IS NOT NULL
        GROUP BY EXTRACT(YEAR FROM data)
        ORDER BY "Ano"
    """)
    sections.append("\n#### Peças Elaboradas por Ano\n")
    sections.append(df_to_markdown(df_pecas_ano))
    sections.append("")

    # Pendências por ano
    df_pend_ano = query_df(engine, """
        SELECT
            EXTRACT(YEAR FROM data) AS "Ano",
            COUNT(*) AS "Pendências"
        FROM pendencias
        WHERE data IS NOT NULL
        GROUP BY EXTRACT(YEAR FROM data)
        ORDER BY "Ano"
    """)
    sections.append("\n#### Pendências por Ano\n")
    sections.append(df_to_markdown(df_pend_ano))
    sections.append("")

    # Finalizadas por ano
    df_fin_ano = query_df(engine, """
        SELECT
            EXTRACT(YEAR FROM data_finalizacao) AS "Ano",
            COUNT(*) AS "Peças Finalizadas"
        FROM pecas_finalizadas
        WHERE data_finalizacao IS NOT NULL
        GROUP BY EXTRACT(YEAR FROM data_finalizacao)
        ORDER BY "Ano"
    """)
    sections.append("\n#### Peças Finalizadas por Ano\n")
    sections.append(df_to_markdown(df_fin_ano))
    sections.append("")

    # Top 15 chefias
    sections.append("\n### 2.2 Top 15 Chefias (por volume de processos novos)\n")
    df_chefias = query_df(engine, """
        SELECT chefia AS "Chefia", COUNT(*) AS "Processos"
        FROM processos_novos
        WHERE chefia IS NOT NULL
        GROUP BY chefia
        ORDER BY COUNT(*) DESC
        LIMIT 15
    """)
    sections.append(df_to_markdown(df_chefias))
    sections.append("")

    # Top 15 procuradores
    sections.append("\n### 2.3 Top 15 Procuradores (por peças elaboradas)\n")
    df_proc = query_df(engine, """
        SELECT procurador AS "Procurador", COUNT(*) AS "Peças Elaboradas"
        FROM pecas_elaboradas
        WHERE procurador IS NOT NULL
        GROUP BY procurador
        ORDER BY COUNT(*) DESC
        LIMIT 15
    """)
    sections.append(df_to_markdown(df_proc))
    sections.append("")

    # Top 20 categorias
    sections.append("\n### 2.4 Top 20 Categorias de Peças\n")
    df_cat = query_df(engine, """
        SELECT categoria AS "Categoria", COUNT(*) AS "Quantidade"
        FROM pecas_elaboradas
        WHERE categoria IS NOT NULL
        GROUP BY categoria
        ORDER BY COUNT(*) DESC
        LIMIT 20
    """)
    sections.append(df_to_markdown(df_cat))
    sections.append("")

    # Distribuição de áreas jurídicas
    sections.append("\n### 2.5 Distribuição por Área Jurídica (pendências)\n")
    df_area = query_df(engine, """
        SELECT area AS "Área", COUNT(*) AS "Pendências",
               ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) AS "% do Total"
        FROM pendencias
        WHERE area IS NOT NULL
        GROUP BY area
        ORDER BY COUNT(*) DESC
    """)
    sections.append(df_to_markdown(df_area))
    sections.append("")

    # Categorias de pendência
    sections.append("\n### 2.6 Categorias de Pendência\n")
    df_cat_pend = query_df(engine, """
        SELECT categoria_pendencia AS "Tipo", COUNT(*) AS "Quantidade",
               ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) AS "% do Total"
        FROM pendencias
        WHERE categoria_pendencia IS NOT NULL
        GROUP BY categoria_pendencia
        ORDER BY COUNT(*) DESC
    """)
    sections.append(df_to_markdown(df_cat_pend))
    sections.append("")

    # Valores únicos por coluna
    sections.append("\n### 2.7 Valores Únicos por Coluna\n")

    unique_queries = {
        "processos_novos": ["chefia", "codigo_processo", "numero_processo", "numero_formatado", "procurador"],
        "pecas_elaboradas": ["chefia", "usuario_criacao", "categoria", "numero_processo", "procurador"],
        "pendencias": ["chefia", "numero_processo", "area", "procurador", "categoria", "categoria_pendencia"],
        "pecas_finalizadas": ["chefia", "usuario_finalizacao", "categoria", "numero_processo", "procurador"],
    }

    for table, columns in unique_queries.items():
        rows = []
        for col in columns:
            uniq = query_scalar(engine, f"SELECT COUNT(DISTINCT {col}) FROM {table} WHERE {col} IS NOT NULL")
            rows.append({"Coluna": col, "Valores Únicos": f"{uniq:,}"})
        sections.append(f"\n#### {table}\n")
        sections.append(df_to_markdown(pd.DataFrame(rows)))
        sections.append("")

    return "\n".join(sections)


def generate_section_correlations(engine) -> str:
    """Gera seção de correlações entre tabelas."""
    logger.info("Gerando análise de correlações...")
    sections = []
    sections.append("## 3. Correlações e Relacionamentos Entre Tabelas\n")

    # Chave de ligação
    sections.append("### 3.1 Chave Principal de Ligação\n")
    sections.append("O campo `numero_processo` é a chave que conecta todas as 4 tabelas.\n")
    sections.append("Fluxo: **Processo Novo** -> **Peças Elaboradas** -> **Peças Finalizadas** + **Pendências**\n")

    # Cobertura de processos entre tabelas
    sections.append("\n### 3.2 Cobertura de Processos Entre Tabelas\n")

    df_coverage = query_df(engine, """
        WITH processos AS (
            SELECT DISTINCT numero_processo FROM processos_novos WHERE numero_processo IS NOT NULL
        ),
        elaboradas AS (
            SELECT DISTINCT numero_processo FROM pecas_elaboradas WHERE numero_processo IS NOT NULL
        ),
        finalizadas AS (
            SELECT DISTINCT numero_processo FROM pecas_finalizadas WHERE numero_processo IS NOT NULL
        ),
        pends AS (
            SELECT DISTINCT numero_processo FROM pendencias WHERE numero_processo IS NOT NULL
        )
        SELECT
            (SELECT COUNT(*) FROM processos) AS "Processos Únicos (novos)",
            (SELECT COUNT(*) FROM elaboradas) AS "Processos c/ Peças Elaboradas",
            (SELECT COUNT(*) FROM finalizadas) AS "Processos c/ Peças Finalizadas",
            (SELECT COUNT(*) FROM pends) AS "Processos c/ Pendências",
            (SELECT COUNT(*) FROM processos p JOIN elaboradas e ON p.numero_processo = e.numero_processo) AS "Novos c/ Elaboradas",
            (SELECT COUNT(*) FROM processos p JOIN pends d ON p.numero_processo = d.numero_processo) AS "Novos c/ Pendências",
            (SELECT COUNT(*) FROM processos p JOIN finalizadas f ON p.numero_processo = f.numero_processo) AS "Novos c/ Finalizadas"
    """)
    sections.append(df_coverage.T.rename(columns={0: "Quantidade"}).to_markdown())
    sections.append("")

    # Peças por processo
    sections.append("\n### 3.3 Peças Elaboradas por Processo\n")
    df_pecas_proc = query_df(engine, """
        SELECT
            MIN(cnt) AS "Mínimo",
            ROUND(AVG(cnt), 2) AS "Média",
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY cnt) AS "Mediana",
            MAX(cnt) AS "Máximo",
            ROUND(STDDEV(cnt), 2) AS "Desvio Padrão"
        FROM (
            SELECT numero_processo, COUNT(*) AS cnt
            FROM pecas_elaboradas
            WHERE numero_processo IS NOT NULL
            GROUP BY numero_processo
        ) sub
    """)
    sections.append(df_to_markdown(df_pecas_proc))
    sections.append("")

    # Pendências por processo
    sections.append("\n### 3.4 Pendências por Processo\n")
    df_pend_proc = query_df(engine, """
        SELECT
            MIN(cnt) AS "Mínimo",
            ROUND(AVG(cnt), 2) AS "Média",
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY cnt) AS "Mediana",
            MAX(cnt) AS "Máximo",
            ROUND(STDDEV(cnt), 2) AS "Desvio Padrão"
        FROM (
            SELECT numero_processo, COUNT(*) AS cnt
            FROM pendencias
            WHERE numero_processo IS NOT NULL
            GROUP BY numero_processo
        ) sub
    """)
    sections.append(df_to_markdown(df_pend_proc))
    sections.append("")

    # Taxa de conclusão: elaboradas vs finalizadas
    sections.append("\n### 3.5 Taxa de Conclusão (Elaboradas vs Finalizadas)\n")
    df_taxa = query_df(engine, """
        WITH elab AS (
            SELECT COUNT(*) AS total FROM pecas_elaboradas
        ),
        fin AS (
            SELECT COUNT(*) AS total FROM pecas_finalizadas
        )
        SELECT
            elab.total AS "Peças Elaboradas",
            fin.total AS "Peças Finalizadas",
            ROUND(fin.total * 100.0 / NULLIF(elab.total, 0), 2) AS "Taxa de Conclusão (%)"
        FROM elab, fin
    """)
    sections.append(df_to_markdown(df_taxa))
    sections.append("")

    # Tempo médio entre elaboração e finalização (por processo)
    sections.append("\n### 3.6 Tempo Médio de Finalização (dias)\n")
    sections.append("Diferença entre data mais antiga de elaboração e data mais recente de finalização por processo.\n")
    df_tempo = query_df(engine, """
        SELECT
            ROUND(AVG(diff_days)::numeric, 2) AS "Média (dias)",
            ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY diff_days)::numeric, 2) AS "Mediana (dias)",
            MIN(diff_days) AS "Mínimo (dias)",
            MAX(diff_days) AS "Máximo (dias)"
        FROM (
            SELECT
                e.numero_processo,
                EXTRACT(EPOCH FROM (MAX(f.data_finalizacao) - MIN(e.data))) / 86400 AS diff_days
            FROM pecas_elaboradas e
            JOIN pecas_finalizadas f ON e.numero_processo = f.numero_processo
            WHERE e.data IS NOT NULL AND f.data_finalizacao IS NOT NULL
            GROUP BY e.numero_processo
            HAVING EXTRACT(EPOCH FROM (MAX(f.data_finalizacao) - MIN(e.data))) >= 0
        ) sub
        WHERE diff_days >= 0
    """)
    sections.append(df_to_markdown(df_tempo))
    sections.append("")

    # Produtividade por procurador
    sections.append("\n### 3.7 Produtividade por Procurador (Top 15)\n")
    sections.append("Peças elaboradas + finalizadas por procurador.\n")
    df_prod = query_df(engine, """
        SELECT
            COALESCE(e.procurador, f.procurador) AS "Procurador",
            COALESCE(e.elaboradas, 0) AS "Elaboradas",
            COALESCE(f.finalizadas, 0) AS "Finalizadas",
            COALESCE(e.elaboradas, 0) + COALESCE(f.finalizadas, 0) AS "Total"
        FROM (
            SELECT procurador, COUNT(*) AS elaboradas
            FROM pecas_elaboradas
            WHERE procurador IS NOT NULL
            GROUP BY procurador
        ) e
        FULL OUTER JOIN (
            SELECT procurador, COUNT(*) AS finalizadas
            FROM pecas_finalizadas
            WHERE procurador IS NOT NULL
            GROUP BY procurador
        ) f ON e.procurador = f.procurador
        ORDER BY COALESCE(e.elaboradas, 0) + COALESCE(f.finalizadas, 0) DESC
        LIMIT 15
    """)
    sections.append(df_to_markdown(df_prod))
    sections.append("")

    # Produtividade por chefia
    sections.append("\n### 3.8 Produtividade por Chefia (Top 15)\n")
    df_prod_chefia = query_df(engine, """
        SELECT
            COALESCE(p.chefia, e.chefia) AS "Chefia",
            COALESCE(p.processos, 0) AS "Processos Novos",
            COALESCE(e.elaboradas, 0) AS "Peças Elaboradas",
            COALESCE(f.finalizadas, 0) AS "Peças Finalizadas",
            COALESCE(d.pendencias, 0) AS "Pendências"
        FROM (
            SELECT chefia, COUNT(*) AS processos
            FROM processos_novos WHERE chefia IS NOT NULL
            GROUP BY chefia
        ) p
        FULL OUTER JOIN (
            SELECT chefia, COUNT(*) AS elaboradas
            FROM pecas_elaboradas WHERE chefia IS NOT NULL
            GROUP BY chefia
        ) e ON p.chefia = e.chefia
        FULL OUTER JOIN (
            SELECT chefia, COUNT(*) AS finalizadas
            FROM pecas_finalizadas WHERE chefia IS NOT NULL
            GROUP BY chefia
        ) f ON COALESCE(p.chefia, e.chefia) = f.chefia
        FULL OUTER JOIN (
            SELECT chefia, COUNT(*) AS pendencias
            FROM pendencias WHERE chefia IS NOT NULL
            GROUP BY chefia
        ) d ON COALESCE(p.chefia, e.chefia, f.chefia) = d.chefia
        ORDER BY COALESCE(p.processos, 0) DESC
        LIMIT 15
    """)
    sections.append(df_to_markdown(df_prod_chefia))
    sections.append("")

    # Correlação: categorias mais comuns em pendências obrigatórias
    sections.append("\n### 3.9 Top 10 Categorias em Pendências Obrigatórias\n")
    df_cat_obr = query_df(engine, """
        SELECT
            categoria AS "Categoria",
            COUNT(*) AS "Pendências Obrigatórias"
        FROM pendencias
        WHERE categoria_pendencia = 'Manifestação obrigatória'
        AND categoria IS NOT NULL
        GROUP BY categoria
        ORDER BY COUNT(*) DESC
        LIMIT 10
    """)
    sections.append(df_to_markdown(df_cat_obr))
    sections.append("")

    # Processos sem nenhuma peça (órfãos)
    sections.append("\n### 3.10 Processos Novos sem Nenhuma Atividade\n")
    sections.append("Processos que existem em `processos_novos` mas não aparecem em nenhuma outra tabela.\n")
    df_orphans = query_df(engine, """
        SELECT COUNT(*) AS "Processos Órfãos"
        FROM processos_novos pn
        WHERE pn.numero_processo IS NOT NULL
        AND NOT EXISTS (SELECT 1 FROM pecas_elaboradas pe WHERE pe.numero_processo = pn.numero_processo)
        AND NOT EXISTS (SELECT 1 FROM pendencias pd WHERE pd.numero_processo = pn.numero_processo)
        AND NOT EXISTS (SELECT 1 FROM pecas_finalizadas pf WHERE pf.numero_processo = pn.numero_processo)
    """)
    total_proc = query_scalar(engine, "SELECT COUNT(*) FROM processos_novos WHERE numero_processo IS NOT NULL")
    orphan_count = df_orphans["Processos Órfãos"].iloc[0]
    pct_orphan = orphan_count / total_proc * 100 if total_proc > 0 else 0

    sections.append(f"- Total de processos novos: **{total_proc:,}**")
    sections.append(f"- Processos sem atividade: **{orphan_count:,}** ({pct_orphan:.2f}%)")
    sections.append("")

    return "\n".join(sections)


def main() -> None:
    """Função principal que gera o relatório completo."""
    logger.info("Iniciando geração do relatório...")

    connection_string = build_connection_string()
    engine = create_engine(connection_string, pool_pre_ping=True)

    # Cabeçalho do relatório
    report_parts = []
    report_parts.append(f"# Relatório de Dados — PGE/BI")
    report_parts.append(f"\n**Gerado em:** {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    report_parts.append(f"**Banco de dados:** pge_bi (PostgreSQL 18.1)")
    report_parts.append(f"**Período dos dados:** 2021 a 2026\n")
    report_parts.append("---\n")

    # Seções
    report_parts.append(generate_section_inventory(engine))
    report_parts.append("\n---\n")
    report_parts.append(generate_section_statistics(engine))
    report_parts.append("\n---\n")
    report_parts.append(generate_section_correlations(engine))

    # Escrever relatório
    report_content = "\n".join(report_parts)
    OUTPUT_FILE.write_text(report_content, encoding="utf-8")

    logger.info(f"Relatório salvo em: {OUTPUT_FILE}")
    engine.dispose()


if __name__ == "__main__":
    main()
