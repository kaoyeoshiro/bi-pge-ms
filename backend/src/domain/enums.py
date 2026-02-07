"""Enumerações do domínio."""

from enum import StrEnum


class TableName(StrEnum):
    """Nomes válidos de tabelas do sistema."""

    PROCESSOS_NOVOS = "processos_novos"
    PECAS_ELABORADAS = "pecas_elaboradas"
    PENDENCIAS = "pendencias"
    PECAS_FINALIZADAS = "pecas_finalizadas"


class Granularity(StrEnum):
    """Granularidade temporal para agrupamentos."""

    MENSAL = "mensal"
    ANUAL = "anual"


class ExportFormat(StrEnum):
    """Formatos de exportação suportados."""

    CSV = "csv"
    EXCEL = "excel"
