"""Carga de dados no PostgreSQL com upsert (ON CONFLICT)."""

import logging
from datetime import datetime

import psycopg2
import psycopg2.extras

from .config import PostgresConfig
from .oracle_queries import TABLE_ORACLE_PK

logger = logging.getLogger(__name__)

# ── Mapeamento de colunas por tabela ─────────────────────────────────

TABLE_COLUMNS: dict[str, list[str]] = {
    "processos_novos": [
        "cd_processo", "chefia", "data", "codigo_processo",
        "numero_processo", "numero_formatado", "procurador",
    ],
    "pecas_elaboradas": [
        "cd_documento", "chefia", "data", "usuario_criacao",
        "categoria", "modelo", "numero_processo", "numero_formatado", "procurador",
    ],
    "pecas_finalizadas": [
        "cd_documento", "chefia", "data_finalizacao", "usuario_finalizacao",
        "categoria", "modelo", "numero_processo", "numero_formatado", "procurador",
    ],
    "pendencias": [
        "cd_pendencia", "chefia", "data", "numero_processo",
        "numero_formatado", "area", "procurador", "usuario_cumpridor_pendencia",
        "categoria", "categoria_pendencia",
    ],
}

# Colunas atualizáveis (tudo exceto a PK Oracle)
TABLE_UPDATE_COLUMNS: dict[str, list[str]] = {
    table: [c for c in cols if c != TABLE_ORACLE_PK[table]]
    for table, cols in TABLE_COLUMNS.items()
}

# ── Migrações de schema (idempotentes) ───────────────────────────────

SCHEMA_MIGRATIONS = [
    # Adiciona coluna cd_processo em processos_novos
    """
    DO $$ BEGIN
        ALTER TABLE processos_novos ADD COLUMN cd_processo VARCHAR(50);
    EXCEPTION WHEN duplicate_column THEN NULL;
    END $$;
    """,
    # Converte cd_processo de BIGINT para VARCHAR se necessário
    """
    DO $$ BEGIN
        IF (SELECT data_type FROM information_schema.columns
            WHERE table_name = 'processos_novos' AND column_name = 'cd_processo') = 'bigint'
        THEN
            ALTER TABLE processos_novos ALTER COLUMN cd_processo TYPE VARCHAR(50);
        END IF;
    END $$;
    """,
    # Índice único parcial em cd_processo
    """
    CREATE UNIQUE INDEX IF NOT EXISTS uix_processos_novos_cd_processo
    ON processos_novos (cd_processo) WHERE cd_processo IS NOT NULL;
    """,
    # Adiciona coluna cd_documento em pecas_elaboradas
    """
    DO $$ BEGIN
        ALTER TABLE pecas_elaboradas ADD COLUMN cd_documento BIGINT;
    EXCEPTION WHEN duplicate_column THEN NULL;
    END $$;
    """,
    # Índice único parcial em cd_documento (pecas_elaboradas)
    """
    CREATE UNIQUE INDEX IF NOT EXISTS uix_pecas_elaboradas_cd_documento
    ON pecas_elaboradas (cd_documento) WHERE cd_documento IS NOT NULL;
    """,
    # Adiciona coluna cd_documento em pecas_finalizadas
    """
    DO $$ BEGIN
        ALTER TABLE pecas_finalizadas ADD COLUMN cd_documento BIGINT;
    EXCEPTION WHEN duplicate_column THEN NULL;
    END $$;
    """,
    # Índice único parcial em cd_documento (pecas_finalizadas)
    """
    CREATE UNIQUE INDEX IF NOT EXISTS uix_pecas_finalizadas_cd_documento
    ON pecas_finalizadas (cd_documento) WHERE cd_documento IS NOT NULL;
    """,
    # Índice único parcial em cd_pendencia
    """
    CREATE UNIQUE INDEX IF NOT EXISTS uix_pendencias_cd_pendencia
    ON pendencias (cd_pendencia) WHERE cd_pendencia IS NOT NULL;
    """,
    # Remove duplicatas de processo_assuntos antes de criar índice
    """
    DELETE FROM processo_assuntos a USING processo_assuntos b
    WHERE a.id > b.id
      AND a.numero_processo = b.numero_processo
      AND a.codigo_assunto = b.codigo_assunto;
    """,
    # Índice único em processo_assuntos
    """
    CREATE UNIQUE INDEX IF NOT EXISTS uix_proc_assuntos_np_ca
    ON processo_assuntos (numero_processo, codigo_assunto);
    """,
]


class PostgresLoader:
    """Carrega dados no PostgreSQL com upsert via ON CONFLICT."""

    def __init__(self, config: PostgresConfig) -> None:
        self._config = config
        self._conn = None

    def connect(self) -> None:
        """Abre conexão com o PostgreSQL."""
        cfg = self._config
        logger.info("Conectando ao PostgreSQL %s:%d/%s...", cfg.host, cfg.port, cfg.dbname)
        self._conn = psycopg2.connect(
            host=cfg.host,
            port=cfg.port,
            user=cfg.user,
            password=cfg.password,
            dbname=cfg.dbname,
        )
        self._conn.autocommit = False
        logger.info("Conectado ao PostgreSQL.")

    def close(self) -> None:
        """Fecha conexão com o PostgreSQL."""
        if self._conn:
            self._conn.close()
            self._conn = None
            logger.info("Conexão PostgreSQL encerrada.")

    def _ensure_connected(self) -> psycopg2.extensions.connection:
        """Garante que a conexão está ativa."""
        if self._conn is None:
            raise RuntimeError("Loader PostgreSQL não conectado. Chame connect() primeiro.")
        return self._conn

    def ensure_schema(self) -> None:
        """Aplica migrações de schema (colunas novas, índices) de forma idempotente."""
        conn = self._ensure_connected()
        logger.info("Verificando schema do banco...")
        with conn.cursor() as cur:
            for sql in SCHEMA_MIGRATIONS:
                cur.execute(sql)
        conn.commit()
        logger.info("Schema atualizado.")

    def upsert_batch(self, table: str, records: list[dict]) -> int:
        """Insere ou atualiza um batch de registros via ON CONFLICT.

        Args:
            table: Nome da tabela PostgreSQL.
            records: Lista de dicts com os dados a inserir/atualizar.

        Returns:
            Número de registros processados.
        """
        if not records:
            return 0

        conn = self._ensure_connected()
        columns = TABLE_COLUMNS[table]
        oracle_pk = TABLE_ORACLE_PK[table]
        update_cols = TABLE_UPDATE_COLUMNS[table]

        # Monta lista de valores
        values_list = []
        for rec in records:
            values = []
            for col in columns:
                val = rec.get(col)
                if isinstance(val, datetime):
                    val = val  # psycopg2 lida com datetime nativamente
                values.append(val)
            values_list.append(tuple(values))

        # Monta SQL de upsert
        cols_str = ", ".join(columns)
        placeholders = ", ".join(["%s"] * len(columns))
        pk_index = f"uix_{table}_{oracle_pk}"
        update_set = ", ".join(f"{c} = EXCLUDED.{c}" for c in update_cols)

        sql = (
            f"INSERT INTO {table} ({cols_str}) VALUES ({placeholders}) "
            f"ON CONFLICT ({oracle_pk}) WHERE {oracle_pk} IS NOT NULL "
            f"DO UPDATE SET {update_set}"
        )

        # Executa em lotes
        with conn.cursor() as cur:
            psycopg2.extras.execute_batch(cur, sql, values_list, page_size=1000)
        conn.commit()

        return len(values_list)

    def upsert_assuntos(self, assuntos: list[dict]) -> int:
        """Insere ou atualiza assuntos na tabela assuntos."""
        if not assuntos:
            return 0

        conn = self._ensure_connected()
        sql = """
            INSERT INTO assuntos (codigo, codigo_pai, nome, descricao, nivel, numero_fmt)
            VALUES (%(codigo)s, %(codigo_pai)s, %(nome)s, %(descricao)s, %(nivel)s, %(numero_fmt)s)
            ON CONFLICT (codigo) DO UPDATE SET
                codigo_pai = EXCLUDED.codigo_pai,
                nome = EXCLUDED.nome,
                descricao = EXCLUDED.descricao,
                nivel = EXCLUDED.nivel,
                numero_fmt = EXCLUDED.numero_fmt
        """

        with conn.cursor() as cur:
            psycopg2.extras.execute_batch(cur, sql, assuntos, page_size=1000)
        conn.commit()

        logger.info("  %d assuntos upserted.", len(assuntos))
        return len(assuntos)

    def upsert_processo_assuntos(self, vinculos: list[dict]) -> int:
        """Insere ou atualiza vínculos processo-assunto."""
        if not vinculos:
            return 0

        conn = self._ensure_connected()

        # Normaliza assunto_principal: Oracle usa 'S'/'N', PG usa boolean
        for v in vinculos:
            ap = v.get("assunto_principal", "N")
            v["assunto_principal"] = (ap == "S") if isinstance(ap, str) else bool(ap)

        sql = """
            INSERT INTO processo_assuntos (numero_processo, codigo_assunto, assunto_principal)
            VALUES (%(numero_processo)s, %(codigo_assunto)s, %(assunto_principal)s)
            ON CONFLICT (numero_processo, codigo_assunto)
            DO UPDATE SET assunto_principal = EXCLUDED.assunto_principal
        """

        with conn.cursor() as cur:
            psycopg2.extras.execute_batch(cur, sql, vinculos, page_size=1000)
        conn.commit()

        logger.info("  %d vínculos processo-assunto upserted.", len(vinculos))
        return len(vinculos)

    def get_table_count(self, table: str) -> int:
        """Retorna contagem de registros na tabela PostgreSQL."""
        conn = self._ensure_connected()
        with conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            return cur.fetchone()[0]

    def get_oracle_pk_count(self, table: str) -> int:
        """Retorna contagem de registros com PK Oracle preenchida."""
        conn = self._ensure_connected()
        oracle_pk = TABLE_ORACLE_PK.get(table)
        if not oracle_pk:
            return 0
        with conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) FROM {table} WHERE {oracle_pk} IS NOT NULL")
            return cur.fetchone()[0]
