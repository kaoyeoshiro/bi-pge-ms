"""Script de migração dos CSVs de processos jurídicos para PostgreSQL.

Lê os 4 arquivos CSV (processos-novos, pecas-elaboradas, pendencias, pecas-finalizadas),
cria as tabelas no banco pge_bi e importa todos os dados com validação de contagem.
"""

import logging
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

import os

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(Path(__file__).parent / "migracao.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

# Carregar variáveis de ambiente
load_dotenv(Path(__file__).parent / ".env")

DATA_DIR = Path(__file__).parent
CHUNK_SIZE = 10_000

# Mapeamento: nome_arquivo -> (nome_tabela, colunas_csv -> colunas_pg, ddl)
TABLE_DEFINITIONS: dict[str, dict] = {
    "processos-novos.csv": {
        "table_name": "processos_novos",
        "column_map": {
            "Chefia": "chefia",
            "Data": "data",
            "Código do Processo": "codigo_processo",
            "Número do Processo": "numero_processo",
            "Número Formatado": "numero_formatado",
            "Procurador": "procurador",
        },
        "ddl": """
            CREATE TABLE IF NOT EXISTS processos_novos (
                id SERIAL PRIMARY KEY,
                chefia VARCHAR(200),
                data TIMESTAMP,
                codigo_processo VARCHAR(50),
                numero_processo BIGINT,
                numero_formatado TEXT,
                procurador VARCHAR(300)
            );
        """,
    },
    "pecas-elaboradas.csv": {
        "table_name": "pecas_elaboradas",
        "column_map": {
            "Chefia": "chefia",
            "Data": "data",
            "Usuário Criação": "usuario_criacao",
            "Categoria": "categoria",
            "Modelo": "modelo",
            "Número do Processo": "numero_processo",
            "Número Formatado": "numero_formatado",
            "Procurador": "procurador",
        },
        "ddl": """
            CREATE TABLE IF NOT EXISTS pecas_elaboradas (
                id SERIAL PRIMARY KEY,
                chefia VARCHAR(200),
                data TIMESTAMP,
                usuario_criacao VARCHAR(300),
                categoria VARCHAR(300),
                modelo TEXT,
                numero_processo BIGINT,
                numero_formatado TEXT,
                procurador VARCHAR(300)
            );
        """,
    },
    "pendencias.csv": {
        "table_name": "pendencias",
        "column_map": {
            "Chefia": "chefia",
            "Data": "data",
            "Número do Processo": "numero_processo",
            "Número Formatado": "numero_formatado",
            "Área": "area",
            "Procurador": "procurador",
            "Usuário Cumpridor Pendência": "usuario_cumpridor_pendencia",
            "Categoria": "categoria",
            "Categoria Pendência": "categoria_pendencia",
            "CDPENDENCIA": "cd_pendencia",
        },
        "ddl": """
            CREATE TABLE IF NOT EXISTS pendencias (
                id SERIAL PRIMARY KEY,
                chefia VARCHAR(200),
                data TIMESTAMP,
                numero_processo BIGINT,
                numero_formatado TEXT,
                area VARCHAR(100),
                procurador VARCHAR(300),
                usuario_cumpridor_pendencia VARCHAR(300),
                categoria VARCHAR(300),
                categoria_pendencia VARCHAR(100),
                cd_pendencia BIGINT
            );
        """,
    },
    "pecas-finalizadas.csv": {
        "table_name": "pecas_finalizadas",
        "column_map": {
            "Chefia": "chefia",
            "Data de Finalização": "data_finalizacao",
            "Usuário Finalização": "usuario_finalizacao",
            "Categoria": "categoria",
            "Modelo": "modelo",
            "Número do Processo": "numero_processo",
            "Número Formatado": "numero_formatado",
            "Procurador": "procurador",
        },
        "ddl": """
            CREATE TABLE IF NOT EXISTS pecas_finalizadas (
                id SERIAL PRIMARY KEY,
                chefia VARCHAR(200),
                data_finalizacao TIMESTAMP,
                usuario_finalizacao VARCHAR(300),
                categoria VARCHAR(300),
                modelo TEXT,
                numero_processo BIGINT,
                numero_formatado TEXT,
                procurador VARCHAR(300)
            );
        """,
    },
}

INDEX_DEFINITIONS = [
    "CREATE INDEX IF NOT EXISTS idx_processos_novos_numero ON processos_novos(numero_processo);",
    "CREATE INDEX IF NOT EXISTS idx_processos_novos_chefia ON processos_novos(chefia);",
    "CREATE INDEX IF NOT EXISTS idx_processos_novos_procurador ON processos_novos(procurador);",
    "CREATE INDEX IF NOT EXISTS idx_processos_novos_data ON processos_novos(data);",
    "CREATE INDEX IF NOT EXISTS idx_pecas_elaboradas_numero ON pecas_elaboradas(numero_processo);",
    "CREATE INDEX IF NOT EXISTS idx_pecas_elaboradas_chefia ON pecas_elaboradas(chefia);",
    "CREATE INDEX IF NOT EXISTS idx_pecas_elaboradas_procurador ON pecas_elaboradas(procurador);",
    "CREATE INDEX IF NOT EXISTS idx_pecas_elaboradas_data ON pecas_elaboradas(data);",
    "CREATE INDEX IF NOT EXISTS idx_pecas_elaboradas_categoria ON pecas_elaboradas(categoria);",
    "CREATE INDEX IF NOT EXISTS idx_pendencias_numero ON pendencias(numero_processo);",
    "CREATE INDEX IF NOT EXISTS idx_pendencias_chefia ON pendencias(chefia);",
    "CREATE INDEX IF NOT EXISTS idx_pendencias_procurador ON pendencias(procurador);",
    "CREATE INDEX IF NOT EXISTS idx_pendencias_data ON pendencias(data);",
    "CREATE INDEX IF NOT EXISTS idx_pendencias_area ON pendencias(area);",
    "CREATE INDEX IF NOT EXISTS idx_pendencias_categoria ON pendencias(categoria);",
    "CREATE INDEX IF NOT EXISTS idx_pecas_finalizadas_numero ON pecas_finalizadas(numero_processo);",
    "CREATE INDEX IF NOT EXISTS idx_pecas_finalizadas_chefia ON pecas_finalizadas(chefia);",
    "CREATE INDEX IF NOT EXISTS idx_pecas_finalizadas_procurador ON pecas_finalizadas(procurador);",
    "CREATE INDEX IF NOT EXISTS idx_pecas_finalizadas_data ON pecas_finalizadas(data_finalizacao);",
    "CREATE INDEX IF NOT EXISTS idx_pecas_finalizadas_categoria ON pecas_finalizadas(categoria);",
]


def build_connection_string() -> str:
    """Monta a string de conexão PostgreSQL a partir das variáveis de ambiente."""
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    user = os.getenv("DB_USER", "postgres")
    password = os.getenv("DB_PASSWORD", "")
    dbname = os.getenv("DB_NAME", "pge_bi")
    return f"postgresql://{user}:{password}@{host}:{port}/{dbname}"


def create_tables(engine) -> None:
    """Cria as tabelas no banco de dados se não existirem."""
    with engine.begin() as conn:
        for csv_file, definition in TABLE_DEFINITIONS.items():
            table_name = definition["table_name"]
            logger.info(f"Criando tabela: {table_name}")
            conn.execute(text(f"DROP TABLE IF EXISTS {table_name} CASCADE;"))
            conn.execute(text(definition["ddl"]))
    logger.info("Todas as tabelas criadas com sucesso.")


def count_csv_rows(file_path: Path) -> int:
    """Conta as linhas de dados em um CSV (excluindo cabeçalho)."""
    count = 0
    with open(file_path, "r", encoding="utf-8") as f:
        next(f)  # pular cabeçalho
        for _ in f:
            count += 1
    return count


def import_csv(engine, csv_file: str, definition: dict) -> int:
    """Importa um arquivo CSV para a tabela PostgreSQL correspondente.

    Retorna o número de linhas importadas.
    """
    file_path = DATA_DIR / csv_file
    table_name = definition["table_name"]
    column_map = definition["column_map"]

    logger.info(f"Iniciando importação: {csv_file} -> {table_name}")

    total_imported = 0
    for i, chunk in enumerate(
        pd.read_csv(
            file_path,
            sep=";",
            encoding="utf-8",
            chunksize=CHUNK_SIZE,
            dtype=str,
            keep_default_na=False,
        )
    ):
        # Renomear colunas para nomes PostgreSQL
        chunk = chunk.rename(columns=column_map)

        # Manter apenas colunas mapeadas
        pg_columns = list(column_map.values())
        chunk = chunk[pg_columns]

        # Converter tipos
        for col in pg_columns:
            if col in ("data", "data_finalizacao"):
                chunk[col] = pd.to_datetime(chunk[col], errors="coerce")
            elif col in ("numero_processo", "cd_pendencia"):
                chunk[col] = pd.to_numeric(chunk[col], errors="coerce")
            else:
                # Substituir strings vazias por None para campos texto
                chunk[col] = chunk[col].replace("", None)

        chunk.to_sql(
            table_name,
            engine,
            if_exists="append",
            index=False,
            method="multi",
        )

        total_imported += len(chunk)
        if (i + 1) % 50 == 0:
            logger.info(f"  {table_name}: {total_imported:,} linhas importadas...")

    logger.info(f"  {table_name}: total de {total_imported:,} linhas importadas.")
    return total_imported


def create_indexes(engine) -> None:
    """Cria índices nas tabelas para otimizar consultas."""
    logger.info("Criando índices...")
    with engine.begin() as conn:
        for idx_sql in INDEX_DEFINITIONS:
            conn.execute(text(idx_sql))
    logger.info("Todos os índices criados com sucesso.")


def validate_counts(engine) -> None:
    """Valida que a contagem no banco bate com a contagem nos CSVs."""
    logger.info("Validando contagens...")
    all_ok = True

    for csv_file, definition in TABLE_DEFINITIONS.items():
        table_name = definition["table_name"]
        file_path = DATA_DIR / csv_file

        csv_count = count_csv_rows(file_path)

        with engine.connect() as conn:
            result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
            db_count = result.scalar()

        status = "OK" if csv_count == db_count else "DIVERGÊNCIA"
        if csv_count != db_count:
            all_ok = False

        logger.info(
            f"  {table_name}: CSV={csv_count:,} | DB={db_count:,} | {status}"
        )

    if all_ok:
        logger.info("Todas as contagens conferem!")
    else:
        logger.warning("Há divergências nas contagens. Verifique os dados.")


def main() -> None:
    """Função principal que orquestra a migração."""
    logger.info("=" * 60)
    logger.info("INÍCIO DA MIGRAÇÃO CSV -> PostgreSQL")
    logger.info("=" * 60)

    connection_string = build_connection_string()
    engine = create_engine(connection_string, pool_pre_ping=True)

    # Testar conexão
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    logger.info("Conexão com PostgreSQL estabelecida.")

    # Criar tabelas
    create_tables(engine)

    # Importar cada CSV
    for csv_file, definition in TABLE_DEFINITIONS.items():
        import_csv(engine, csv_file, definition)

    # Criar índices após importação (mais eficiente)
    create_indexes(engine)

    # Validar contagens
    validate_counts(engine)

    logger.info("=" * 60)
    logger.info("MIGRAÇÃO CONCLUÍDA COM SUCESSO")
    logger.info("=" * 60)

    engine.dispose()


if __name__ == "__main__":
    main()
