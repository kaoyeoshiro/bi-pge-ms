"""Constantes de domínio do BI PGE-MS."""

# Categorias de peças finalizadas que NÃO representam produção jurídica real.
# São atos administrativos (encaminhamento, arquivamento, ciência, movimentação
# processual) que não devem contar como KPI de produtividade.
#
# Diagnóstico realizado em 2026-02-07 com dados de PS/2026:
# - Encaminhamentos: roteamento de processo entre setores
# - Arquivamento / Arquivamento dos autos: ato de arquivar processo
# - Desarquivamento dos autos: ato de desarquivar processo
# - Ciência de Decisão / Despacho: mera ciência, sem produção de peça
# - Recusa do encaminhamento: recusa de roteamento
# - Informação Administrativa: informação interna não-jurídica
# - Decisão conflito: ato interno de conflito de competência
# - Desentranhamento: retirada de peça dos autos
# - Apensamento: junção física de autos
# - Autorizações para solicitação de autos: ato burocrático
# - Redirecionamento: movimentação interna de processo
CATEGORIAS_NAO_PRODUTIVAS: frozenset[str] = frozenset({
    "Encaminhamentos",
    "Arquivamento",
    "Arquivamento dos autos",
    "Desarquivamento dos autos",
    "Ciência de Decisão / Despacho",
    "Recusa do encaminhamento",
    "Informação Administrativa",
    "Decisão conflito",
    "Desentranhamento",
    "Apensamento",
    "Autorizações para solicitação de autos",
    "Redirecionamento",
})
