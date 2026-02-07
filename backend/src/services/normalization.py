"""Funções de normalização SQL para unificar valores duplicados no banco."""

from sqlalchemy import Column, case, func


CHEFIA_PS_NORMALIZADA = "PS - Procuradoria de Saúde"


def normalize_chefia_expr(col: Column) -> Column:
    """Retorna expressão SQL que unifica variantes de PS em 'PS - Procuradoria de Saúde'.

    Exemplos transformados:
    - 'PS (Baixo Impacto)' → 'PS - Procuradoria de Saúde'
    - 'PS (Cartório)' → 'PS - Procuradoria de Saúde'
    - 'PS (Comum)' → 'PS - Procuradoria de Saúde'
    - 'PS (Estratégico)' → 'PS - Procuradoria de Saúde'
    - 'Procuradoria da Saúde (2º grau)' → 'PS - Procuradoria de Saúde'
    """
    return case(
        (col.op("~")(r"^PS\s*\("), CHEFIA_PS_NORMALIZADA),
        (col.op("~*")(r"Procuradoria\s+d[ae]\s+Sa[uú]de"), CHEFIA_PS_NORMALIZADA),
        else_=col,
    )


def normalize_chefia_sql(col_expr: str) -> str:
    """Gera expressão CASE WHEN SQL para normalização de chefia (uso em raw SQL).

    Args:
        col_expr: Expressão SQL da coluna (ex: 'tabela.chefia').
    """
    return (
        f"CASE "
        f"WHEN {col_expr} ~ '^PS\\s*\\(' THEN '{CHEFIA_PS_NORMALIZADA}' "
        f"WHEN {col_expr} ~* 'Procuradoria\\s+d[ae]\\s+Sa[uú]de' THEN '{CHEFIA_PS_NORMALIZADA}' "
        f"ELSE {col_expr} END"
    )


def normalize_procurador_expr(col: Column) -> Column:
    """Remove sufixos entre parênteses do nome do procurador.

    Exemplo: 'Eimar Souza Schröder Rosa (Precatórios)' → 'Eimar Souza Schröder Rosa'
    """
    return func.trim(func.regexp_replace(col, r"\s*\(.*\)$", "", "g"))
