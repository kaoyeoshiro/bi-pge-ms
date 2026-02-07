# Relatório de Dados — PGE/BI

**Gerado em:** 06/02/2026 20:24
**Banco de dados:** pge_bi (PostgreSQL 18.1)
**Período dos dados:** 2021 a 2026

---

## 1. Inventário de Dados

### 1.1 Contagem de Registros

| Tabela            | Registros     |
|:------------------|:--------------|
| processos_novos   | 135,091       |
| pecas_elaboradas  | 1,298,406     |
| pendencias        | 1,156,806     |
| pecas_finalizadas | 1,289,006     |
| **TOTAL**         | **3,879,309** |


### 1.2 Schema das Tabelas


#### processos_novos

| Coluna           | Tipo PostgreSQL             |   Tamanho Máx | Nulo?   |
|:-----------------|:----------------------------|--------------:|:--------|
| id               | integer                     |           nan | NO      |
| chefia           | character varying           |           200 | YES     |
| data             | timestamp without time zone |           nan | YES     |
| codigo_processo  | character varying           |            50 | YES     |
| numero_processo  | bigint                      |           nan | YES     |
| numero_formatado | text                        |           nan | YES     |
| procurador       | character varying           |           300 | YES     |


#### pecas_elaboradas

| Coluna           | Tipo PostgreSQL             |   Tamanho Máx | Nulo?   |
|:-----------------|:----------------------------|--------------:|:--------|
| id               | integer                     |           nan | NO      |
| chefia           | character varying           |           200 | YES     |
| data             | timestamp without time zone |           nan | YES     |
| usuario_criacao  | character varying           |           300 | YES     |
| categoria        | character varying           |           300 | YES     |
| modelo           | text                        |           nan | YES     |
| numero_processo  | bigint                      |           nan | YES     |
| numero_formatado | text                        |           nan | YES     |
| procurador       | character varying           |           300 | YES     |


#### pendencias

| Coluna                      | Tipo PostgreSQL             |   Tamanho Máx | Nulo?   |
|:----------------------------|:----------------------------|--------------:|:--------|
| id                          | integer                     |           nan | NO      |
| chefia                      | character varying           |           200 | YES     |
| data                        | timestamp without time zone |           nan | YES     |
| numero_processo             | bigint                      |           nan | YES     |
| numero_formatado            | text                        |           nan | YES     |
| area                        | character varying           |           100 | YES     |
| procurador                  | character varying           |           300 | YES     |
| usuario_cumpridor_pendencia | character varying           |           300 | YES     |
| categoria                   | character varying           |           300 | YES     |
| categoria_pendencia         | character varying           |           100 | YES     |
| cd_pendencia                | bigint                      |           nan | YES     |


#### pecas_finalizadas

| Coluna              | Tipo PostgreSQL             |   Tamanho Máx | Nulo?   |
|:--------------------|:----------------------------|--------------:|:--------|
| id                  | integer                     |           nan | NO      |
| chefia              | character varying           |           200 | YES     |
| data_finalizacao    | timestamp without time zone |           nan | YES     |
| usuario_finalizacao | character varying           |           300 | YES     |
| categoria           | character varying           |           300 | YES     |
| modelo              | text                        |           nan | YES     |
| numero_processo     | bigint                      |           nan | YES     |
| numero_formatado    | text                        |           nan | YES     |
| procurador          | character varying           |           300 | YES     |


### 1.3 Valores Nulos por Tabela


#### processos_novos

| Coluna           |   Nulos | % Nulos   |
|:-----------------|--------:|:----------|
| chefia           |       0 | 0.00%     |
| data             |       0 | 0.00%     |
| codigo_processo  |       0 | 0.00%     |
| numero_processo  |       0 | 0.00%     |
| numero_formatado |       4 | 0.00%     |
| procurador       |       0 | 0.00%     |


#### pecas_elaboradas

| Coluna           | Nulos   | % Nulos   |
|:-----------------|:--------|:----------|
| chefia           | 0       | 0.00%     |
| data             | 0       | 0.00%     |
| usuario_criacao  | 0       | 0.00%     |
| categoria        | 0       | 0.00%     |
| modelo           | 0       | 0.00%     |
| numero_processo  | 0       | 0.00%     |
| numero_formatado | 3,305   | 0.25%     |
| procurador       | 0       | 0.00%     |


#### pendencias

| Coluna                      |   Nulos | % Nulos   |
|:----------------------------|--------:|:----------|
| chefia                      |       0 | 0.00%     |
| data                        |       0 | 0.00%     |
| numero_processo             |       0 | 0.00%     |
| numero_formatado            |      10 | 0.00%     |
| area                        |       0 | 0.00%     |
| procurador                  |       0 | 0.00%     |
| usuario_cumpridor_pendencia |       0 | 0.00%     |
| categoria                   |       0 | 0.00%     |
| categoria_pendencia         |       0 | 0.00%     |
| cd_pendencia                |       0 | 0.00%     |


#### pecas_finalizadas

| Coluna              | Nulos   | % Nulos   |
|:--------------------|:--------|:----------|
| chefia              | 0       | 0.00%     |
| data_finalizacao    | 0       | 0.00%     |
| usuario_finalizacao | 0       | 0.00%     |
| categoria           | 0       | 0.00%     |
| modelo              | 0       | 0.00%     |
| numero_processo     | 0       | 0.00%     |
| numero_formatado    | 3,031   | 0.24%     |
| procurador          | 0       | 0.00%     |


---

## 2. Estatísticas Descritivas

### 2.1 Distribuição Temporal

#### Processos Novos por Ano

|   Ano |   Processos Novos |
|------:|------------------:|
|  2021 |             26377 |
|  2022 |             25807 |
|  2023 |             25355 |
|  2024 |             26657 |
|  2025 |             28154 |
|  2026 |              2741 |


#### Peças Elaboradas por Ano

|   Ano |   Peças Elaboradas |
|------:|-------------------:|
|  2021 |             201434 |
|  2022 |             225455 |
|  2023 |             259827 |
|  2024 |             287053 |
|  2025 |             299919 |
|  2026 |              24718 |


#### Pendências por Ano

|   Ano |   Pendências |
|------:|-------------:|
|  2021 |       178535 |
|  2022 |       205349 |
|  2023 |       242216 |
|  2024 |       255817 |
|  2025 |       258081 |
|  2026 |        16808 |


#### Peças Finalizadas por Ano

|   Ano |   Peças Finalizadas |
|------:|--------------------:|
|  2021 |              200193 |
|  2022 |              223808 |
|  2023 |              257413 |
|  2024 |              286155 |
|  2025 |              297441 |
|  2026 |               23996 |


### 2.2 Top 15 Chefias (por volume de processos novos)

| Chefia                                     |   Processos |
|:-------------------------------------------|------------:|
| PITCD                                      |       24282 |
| PJ- Procuradoria Judicial                  |       21937 |
| CJUR - DETRAN                              |       15790 |
| PP - Procuradoria de Pessoal               |       13592 |
| PPREC - Procuradoria de Precatórios        |       13054 |
| PS (Cartório)                              |       11416 |
| PCS - Cumprimento de Sentença              |       11225 |
| PS (Baixo Impacto)                         |        8505 |
| PAT - Procuradoria de Assuntos Tributários |        8374 |
| PPREV                                      |        2666 |
| CJUR - SEFAZ                               |        1738 |
| CJUR-SED                                   |         608 |
| CJUR - AGEHAB                              |         454 |
| PRB - Brasilia                             |         316 |
| CJUR - SEMADESC                            |         276 |


### 2.3 Top 15 Procuradores (por peças elaboradas)

| Procurador                                  |   Peças Elaboradas |
|:--------------------------------------------|-------------------:|
| Kaoye Guazina Oshiro                        |             169306 |
| Leonardo da Matta Lavorato Schafflör Guerra |             157174 |
| Eimar Souza Schröder Rosa                   |             119129 |
| Eimar Souza Schröder Rosa (Precatórios)     |             118780 |
| Procurador do Tributário                    |             113850 |
| Sérgio W. Annibal                           |              37792 |
| Fábio Hilário Martinez de Oliveira          |              36042 |
| Procurador Arquivado/Extinto                |              34019 |
| Julizar Barbosa Trindade Junior             |              29539 |
| FERNANDO RODRIGUES DE SOUSA                 |              29254 |
| Renato Woolley de Carvalho Martins          |              28482 |
| Marcos Costa Vianna Moog                    |              28344 |
| Wilson Maingué Neto                         |              27936 |
| Adalberto Neves Miranda                     |              26472 |
| Daniela Corrêa Basmage                      |              24619 |


### 2.4 Top 20 Categorias de Peças

| Categoria                                     |   Quantidade |
|:----------------------------------------------|-------------:|
| Petições diversas                             |       314814 |
| ADI - Anotações de Dispensa de Recurso        |       110177 |
| Ciência                                       |       102237 |
| Manifestação em 5 Dias                        |        73810 |
| Ofícios                                       |        66749 |
| Arquivamento                                  |        64747 |
| Contestação                                   |        61973 |
| Encaminhamentos                               |        31756 |
| Manifestação em 10 Dias                       |        25106 |
| Contrarrazões de Recurso (2 Grau)             |        24145 |
| Manifestação em Cálculos                      |        20717 |
| EFE - Ciência                                 |        20699 |
| Solicitação de Cálculos                       |        20651 |
| Manifestação em Cadastro de Requisição        |        20132 |
| Cálculos Periciais                            |        19531 |
| Pedido de Informações/Providências - Resposta |        18063 |
| Informações/Providências PCDA                 |        17940 |
| Produção de provas                            |        15504 |
| Impugnação ao Cumprimento de Sentença         |        15055 |
| Embargos de Declaração 1º Grau                |        13015 |


### 2.5 Distribuição por Área Jurídica (pendências)

| Área            |   Pendências |   % do Total |
|:----------------|-------------:|-------------:|
| Pessoal         |       394611 |        34.11 |
| Saúde           |       333620 |        28.84 |
| Residual        |       195843 |        16.93 |
| Execução Fiscal |        77310 |         6.68 |
| ITCD            |        75708 |         6.54 |
| Tributária      |        49804 |         4.31 |
| Fiscal          |        19494 |         1.69 |
| Educação        |         2929 |         0.25 |
| Meio Ambiente   |         2856 |         0.25 |
| Administrativa  |         2678 |         0.23 |
| Precatórios     |         1827 |         0.16 |
| Créditos        |          126 |         0.01 |


### 2.6 Categorias de Pendência

| Tipo                     |   Quantidade |   % do Total |
|:-------------------------|-------------:|-------------:|
| Manifestação opcional    |      1059806 |        91.61 |
| Manifestação obrigatória |        97000 |         8.39 |


### 2.7 Valores Únicos por Coluna


#### processos_novos

| Coluna           | Valores Únicos   |
|:-----------------|:-----------------|
| chefia           | 33               |
| codigo_processo  | 135,091          |
| numero_processo  | 135,091          |
| numero_formatado | 135,072          |
| procurador       | 77               |


#### pecas_elaboradas

| Coluna          | Valores Únicos   |
|:----------------|:-----------------|
| chefia          | 34               |
| usuario_criacao | 493              |
| categoria       | 195              |
| numero_processo | 199,673          |
| procurador      | 85               |


#### pendencias

| Coluna              | Valores Únicos   |
|:--------------------|:-----------------|
| chefia              | 37               |
| numero_processo     | 198,026          |
| area                | 12               |
| procurador          | 109              |
| categoria           | 112              |
| categoria_pendencia | 2                |


#### pecas_finalizadas

| Coluna              | Valores Únicos   |
|:--------------------|:-----------------|
| chefia              | 34               |
| usuario_finalizacao | 278              |
| categoria           | 194              |
| numero_processo     | 199,526          |
| procurador          | 84               |


---

## 3. Correlações e Relacionamentos Entre Tabelas

### 3.1 Chave Principal de Ligação

O campo `numero_processo` é a chave que conecta todas as 4 tabelas.

Fluxo: **Processo Novo** -> **Peças Elaboradas** -> **Peças Finalizadas** + **Pendências**


### 3.2 Cobertura de Processos Entre Tabelas

|                                |   Quantidade |
|:-------------------------------|-------------:|
| Processos Únicos (novos)       |       135091 |
| Processos c/ Peças Elaboradas  |       199673 |
| Processos c/ Peças Finalizadas |       199526 |
| Processos c/ Pendências        |       198026 |
| Novos c/ Elaboradas            |       130303 |
| Novos c/ Pendências            |       131818 |
| Novos c/ Finalizadas           |       130154 |


### 3.3 Peças Elaboradas por Processo

|   Mínimo |   Média |   Mediana |   Máximo |   Desvio Padrão |
|---------:|--------:|----------:|---------:|----------------:|
|        1 |     6.5 |         4 |     2347 |           10.98 |


### 3.4 Pendências por Processo

|   Mínimo |   Média |   Mediana |   Máximo |   Desvio Padrão |
|---------:|--------:|----------:|---------:|----------------:|
|        1 |    5.84 |         4 |     2950 |           11.29 |


### 3.5 Taxa de Conclusão (Elaboradas vs Finalizadas)

|   Peças Elaboradas |   Peças Finalizadas |   Taxa de Conclusão (%) |
|-------------------:|--------------------:|------------------------:|
|        1.29841e+06 |         1.28901e+06 |                   99.28 |


### 3.6 Tempo Médio de Finalização (dias)

Diferença entre data mais antiga de elaboração e data mais recente de finalização por processo.

|   Média (dias) |   Mediana (dias) |   Mínimo (dias) |   Máximo (dias) |
|---------------:|-----------------:|----------------:|----------------:|
|         466.35 |            283.2 |     2.31481e-05 |         1856.86 |


### 3.7 Produtividade por Procurador (Top 15)

Peças elaboradas + finalizadas por procurador.

| Procurador                                  |   Elaboradas |   Finalizadas |   Total |
|:--------------------------------------------|-------------:|--------------:|--------:|
| Kaoye Guazina Oshiro                        |       169306 |        168074 |  337380 |
| Leonardo da Matta Lavorato Schafflör Guerra |       157174 |        155458 |  312632 |
| Eimar Souza Schröder Rosa                   |       119129 |        118545 |  237674 |
| Eimar Souza Schröder Rosa (Precatórios)     |       118780 |        118149 |  236929 |
| Procurador do Tributário                    |       113850 |        113148 |  226998 |
| Sérgio W. Annibal                           |        37792 |         37543 |   75335 |
| Fábio Hilário Martinez de Oliveira          |        36042 |         35663 |   71705 |
| Procurador Arquivado/Extinto                |        34019 |         33835 |   67854 |
| Julizar Barbosa Trindade Junior             |        29539 |         29435 |   58974 |
| FERNANDO RODRIGUES DE SOUSA                 |        29254 |         29023 |   58277 |
| Renato Woolley de Carvalho Martins          |        28482 |         28327 |   56809 |
| Marcos Costa Vianna Moog                    |        28344 |         28336 |   56680 |
| Wilson Maingué Neto                         |        27936 |         27628 |   55564 |
| Adalberto Neves Miranda                     |        26472 |         26456 |   52928 |
| Daniela Corrêa Basmage                      |        24619 |         24530 |   49149 |


### 3.8 Produtividade por Chefia (Top 15)

| Chefia                                     |   Processos Novos |   Peças Elaboradas |   Peças Finalizadas |   Pendências |
|:-------------------------------------------|------------------:|-------------------:|--------------------:|-------------:|
| PITCD                                      |             24282 |              84355 |               84227 |        74629 |
| PJ- Procuradoria Judicial                  |             21937 |              65428 |               65034 |        82855 |
| CJUR - DETRAN                              |             15790 |              59568 |               59171 |        62061 |
| PP - Procuradoria de Pessoal               |             13592 |              92868 |               91987 |       189738 |
| PPREC - Procuradoria de Precatórios        |             13054 |             237909 |              236694 |        49309 |
| PS (Cartório)                              |             11416 |             156889 |              155175 |        31639 |
| PCS - Cumprimento de Sentença              |             11225 |             190545 |              188676 |       170596 |
| PS (Baixo Impacto)                         |              8505 |             169308 |              168076 |         1197 |
| PAT - Procuradoria de Assuntos Tributários |              8374 |             185805 |              184730 |       115492 |
| PPREV                                      |              2666 |              15260 |               15135 |        16796 |
| CJUR - SEFAZ                               |              1738 |              17264 |               17243 |        18509 |
| CJUR-SED                                   |               608 |               3192 |                3171 |         3318 |
| CJUR - AGEHAB                              |               454 |               3168 |                3162 |         2525 |
| PRB - Brasilia                             |               316 |               6326 |                6226 |        22587 |
| CJUR - SEMADESC                            |               276 |               2257 |                2191 |         2318 |


### 3.9 Top 10 Categorias em Pendências Obrigatórias

| Categoria                                           |   Pendências Obrigatórias |
|:----------------------------------------------------|--------------------------:|
| Contestação                                         |                     69914 |
| Agravo de Instrumento (art. 1.015) Outros Tribunais |                      4913 |
| Apelação                                            |                      4365 |
| Informações MS                                      |                      3381 |
| Embargos de Declaração 2º Grau TJMS                 |                      3097 |
| Manifestação em 72h                                 |                      1987 |
| Petições diversas                                   |                      1557 |
| Manifestação em 5 Dias                              |                      1441 |
| ADI - Anotações de Dispensa de Recurso              |                      1377 |
| Recurso Inominado                                   |                      1322 |


### 3.10 Processos Novos sem Nenhuma Atividade

Processos que existem em `processos_novos` mas não aparecem em nenhuma outra tabela.

- Total de processos novos: **135,091**
- Processos sem atividade: **1,416** (1.05%)
