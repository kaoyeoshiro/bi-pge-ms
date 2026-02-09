# Relatório de Auditoria — Métricas por Procurador (BI PGE-MS)

## Sintoma

Ao filtrar por procurador individual no "Perfil do Procurador", os números de **Peças Finalizadas** aparecem distorcidos:

- **Kaoye Guazina Oshiro**: KPI mostrava 166.081 peças finalizadas (real: 38.814)
- **Caio Gama Mascarenhas**: KPI mostrava 4.666 (real: 12.009)
- A visão geral (agregada) estava consistente; o problema só aparecia ao filtrar por indivíduo.

## Causa Raiz Confirmada

### O bug

O filtro `filters.procurador` em `_apply_global_filters()` usava a coluna **`procurador`** (dono do caso/processo) para **todas** as tabelas, incluindo `pecas_finalizadas`.

Porém, em `pecas_finalizadas`, o dono do caso (`procurador`) é diferente de quem finalizou a peça (`usuario_finalizacao`) em **72,9% dos registros** (861.404 de 1.181.670).

### O efeito

| Cenário | Resultado errado |
|---|---|
| Procurador é dono de muitos processos mas OUTROS finalizam as peças | **Inflação** — KPI mostra peças que outros fizeram nos seus processos |
| Procurador finaliza muitas peças em processos de OUTROS colegas | **Deflação** — KPI não mostra peças que ele realmente fez |

### Inconsistência interna

O **comparativo de chefia** já usava `usuario_finalizacao` corretamente (via `COMPARATIVO_PERSON_COL`), criando discrepância com os KPIs/timeline do perfil individual.

## Evidências Numéricas

### Discrepância por procurador (pecas_finalizadas)

| Procurador | Por Dono (bug) | Por Finalizador (correto) | Diferença |
|---|---:|---:|---:|
| Kaoye Guazina Oshiro | 166.081 | 38.814 | +127.267 |
| Leonardo da Matta L. S. Guerra | 154.732 | 13.201 | +141.531 |
| Eimar Souza Schröder Rosa | 200.577 | 76.893 | +123.684 |
| Caio Gama Mascarenhas | 4.666 | 12.009 | -7.343 |
| Leandro Pedro de Melo | 0 | 52.609 | -52.609 |
| Fabio Jun Capucho | 0 | 38.936 | -38.936 |

### Verificações complementares

- **Duplicidade de IDs**: Nenhuma em nenhuma tabela (0 duplicados)
- **Soma individual = total**: Confirmada para todas as tabelas
- **Máximo individual < total**: OK para todas as tabelas
- **Valores negativos em séries**: Nenhum encontrado

## Antes/Depois — Kaoye Guazina Oshiro

| Métrica | ANTES (bug) | DEPOIS (corrigido) |
|---|---:|---:|
| Processos Novos | 8.501 | 8.501 (sem alteração) |
| Peças Finalizadas | **166.081** | **38.814** |
| Pendências | 62.057 | 62.057 (sem alteração) |

## Antes/Depois — Caio Gama Mascarenhas

| Métrica | ANTES (bug) | DEPOIS (corrigido) |
|---|---:|---:|
| Processos Novos | 1.560 | 1.560 (sem alteração) |
| Peças Finalizadas | **4.666** | **12.009** |
| Pendências | 15.016 | 15.016 (sem alteração) |

## Correção Aplicada

### Mudança principal (`base_repository.py:77-82`)

```python
# ANTES (bug):
if filters.procurador:
    proc_expr = self._get_filter_expr("procurador")  # Sempre coluna 'procurador'
    stmt = stmt.where(proc_expr.in_(filters.procurador))

# DEPOIS (corrigido):
if filters.procurador:
    # Usa coluna resolvida (PROCURADOR_COL_MAP): em pecas_finalizadas
    # filtra por usuario_finalizacao (quem finalizou), não por procurador
    proc_expr = self._get_group_expr("procurador")  # Resolve via PROCURADOR_COL_MAP
    stmt = stmt.where(proc_expr.in_(filters.procurador))
```

### Como funciona

`_get_group_expr("procurador")` chama `_resolve_column("procurador")` que consulta `PROCURADOR_COL_MAP`:

| Tabela | Coluna resolvida | Significado |
|---|---|---|
| processos_novos | `procurador` | Dono do caso (sem alteração) |
| pecas_finalizadas | `usuario_finalizacao` | Quem finalizou a peça (**corrigido**) |
| pendencias | `procurador` | Dono do caso (sem alteração) |
| pecas_elaboradas | `procurador` | Dono do caso (sem alteração) |

## Arquivos Alterados

| Arquivo | Alteração |
|---|---|
| `backend/src/repositories/base_repository.py` | Correção do filtro de procurador (L77-82) + docstring (L208-212) |
| `backend/src/config.py` | Adicionado `extra: "ignore"` para tolerar variáveis extras no .env |
| `backend/tests/integration/test_perfil_procurador_metricas.py` | **Novo** — 5 testes de integração validando a correção |
| `backend/tests/integration/test_comparativo_validacao.py` | Corrigido fixture `empty_filters` (desabilitar filtros que a query direta não replica) |

## Como Validar

### 1. Rodar testes automatizados

```bash
cd backend
python -m pytest tests/ -v
# Esperado: 57 passed
```

### 2. Rodar script de auditoria SQL

```bash
cd ..
python auditoria_dados.py
# Verificar que "PorDono" e "PorFinaliz" batem para os procuradores suspeitos
```

### 3. Validar manualmente no BI

1. Abrir Perfil do Procurador → selecionar "Kaoye Guazina Oshiro"
2. KPI "Peças Finalizadas" deve mostrar ~38.814 (não 166.081)
3. Abrir Perfil da Chefia da mesma chefia → Comparativo
4. O valor de "Peças Finalizadas" para Kaoye deve bater com o KPI do perfil

## Hipóteses Investigadas e Descartadas

| # | Hipótese | Resultado |
|---|---|---|
| 1 | Duplicidade por JOIN | Descartada — queries são sobre tabelas únicas, sem JOIN |
| 2 | Erro de granularidade | Descartada — COUNT(*) sobre registros únicos |
| 3 | **Chave errada para filtro por procurador** | **CONFIRMADA** — causa raiz |
| 4 | Falta de DISTINCT | Descartada — IDs são únicos em todas as tabelas |
| 5 | Período aplicado errado | Descartada — mesma lógica para todas as tabelas |
| 6 | Dados históricos acumulando | Descartada — sem mistura de dados |
| 7 | Procurador trocado por assessor | Descartada — roles são respeitados |
| 8 | Fallback para procurador padrão | Descartada — nenhum fallback no código |
| 9 | Erro de cache | Descartada — cache com TTL 5min, sem invalidação mas sem distorção |
| 10 | Erro na série mensal | Descartada — séries corretas após a correção |

## Definições de Métricas (Documentação)

| Métrica | Tabela | Evento que gera registro | Coluna de atribuição (procurador) |
|---|---|---|---|
| Processos Novos | `processos_novos` | Distribuição de processo novo | `procurador` (dono do caso) |
| Peças Finalizadas | `pecas_finalizadas` | Finalização de peça jurídica | `usuario_finalizacao` (quem finalizou) |
| Pendências | `pendencias` | Criação de pendência em processo | `procurador` (dono do caso) |
| Peças Elaboradas | `pecas_elaboradas` | Criação de peça jurídica | `usuario_criacao` (quem criou) |
