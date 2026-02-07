"""Funções de normalização SQL para unificar valores duplicados no banco."""

from sqlalchemy import Column, case, func


def normalize_chefia_expr(col: Column) -> Column:
    """Retorna expressão SQL que unifica variantes de PS em 'PS - Procuradoria de Saúde'.

    Exemplos transformados:
    - 'PS (Baixo Impacto)' → 'PS - Procuradoria de Saúde'
    - 'PS (Cartório)' → 'PS - Procuradoria de Saúde'
    - 'PS (Comum)' → 'PS - Procuradoria de Saúde'
    - 'PS (Estratégico)' → 'PS - Procuradoria de Saúde'
    """
    return case(
        (col.op("~")(r"^PS\s*\("), "PS - Procuradoria de Saúde"),
        else_=col,
    )


def normalize_procurador_expr(col: Column) -> Column:
    """Remove sufixos entre parênteses do nome do procurador.

    Exemplo: 'Eimar Souza Schröder Rosa (Precatórios)' → 'Eimar Souza Schröder Rosa'
    """
    return func.trim(func.regexp_replace(col, r"\s*\(.*\)$", "", "g"))
