# ETL Oracle → PostgreSQL — BI PGE-MS

## Visão geral

O ETL extrai dados do **Oracle SAJ/SPJMS** (via VPN + túnel SSH) e carrega no **PostgreSQL** local com upsert (`ON CONFLICT`), garantindo carga incremental sem duplicação.

```
[sua máquina] → VPN-PGE → SSH (10.21.9.206) → Oracle (10.2.12.215:1521/SPJMS)
                                               ↓
                                          PostgreSQL local (pge_bi)
```

## Pré-requisitos

| Requisito | Caminho / Valor |
|-----------|----------------|
| Python 3.10+ | `python --version` |
| Oracle Instant Client | `C:\oracle\instantclient_21_20` |
| VPN-PGE configurada | `rasdial` para verificar |
| Chave SSH no servidor | `rcosta@PGE.ms` em `10.21.9.206` |
| PostgreSQL local | `localhost:5432/pge_bi` |

### Variáveis no `.env` (raiz do projeto)

```env
# Oracle
DB_ORACLE_USER=seu_usuario
DB_ORACLE_PASSWORD=sua_senha

# VPN
VPN_USER=seu_usuario_vpn
VPN_PASSWORD=sua_senha_vpn

# PostgreSQL local
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=sua_senha_pg
DB_NAME=pge_bi
```

### Dependências Python

```bash
pip install oracledb psycopg2-binary python-dotenv
```

## Como rodar

### Carga incremental (uso diário)

Extrai os últimos **30 dias** de todas as tabelas + assuntos:

```bash
cd E:\Projetos\BI\scripts
python etl_oracle.py
```

### Carga completa (primeira vez ou reconstrução)

Extrai desde **01/01/2021** até hoje:

```bash
python etl_oracle.py --full
```

### Tabelas específicas

```bash
python etl_oracle.py --tables processos_novos pecas_finalizadas
```

### Sem assuntos

```bash
python etl_oracle.py --no-assuntos
```

## O que o script faz (passo a passo)

1. **Conecta ao PostgreSQL** local e aplica migrações de schema (colunas de PK Oracle, índices)
2. **Verifica/conecta VPN** (`rasdial VPN-PGE`)
3. **Abre túnel SSH** (`localhost:1521` → `10.2.12.215:1521` via `10.21.9.206`)
4. **Conecta ao Oracle** em thick mode (necessário para Oracle 11g)
5. **Para cada tabela** (processos_novos, pecas_elaboradas, pecas_finalizadas, pendencias):
   - Extrai registros filtrados pela janela de data, em batches de 5.000
   - Faz upsert no PostgreSQL via `INSERT ... ON CONFLICT (pk_oracle) DO UPDATE`
6. **Assuntos** (incluído por padrão):
   - Extrai árvore completa de assuntos (7.229 nós)
   - Extrai vínculos processo-assunto da janela de data
   - Upsert em ambas as tabelas
7. **Fecha conexões** e encerra o túnel SSH

## Tabelas e chaves

| Tabela PG | PK Oracle | Tipo | Coluna de data |
|-----------|-----------|------|---------------|
| `processos_novos` | `cd_processo` | VARCHAR | `data` |
| `pecas_elaboradas` | `cd_documento` | BIGINT | `data` |
| `pecas_finalizadas` | `cd_documento` | BIGINT | `data_finalizacao` |
| `pendencias` | `cd_pendencia` | BIGINT | `data` |
| `assuntos` | `codigo` | INTEGER | — |
| `processo_assuntos` | `(numero_processo, codigo_assunto)` | composta | — |

## Atualizar produção (Railway)

Após rodar o ETL localmente, o banco de produção precisa ser atualizado manualmente:

### 1. Dump das tabelas principais

```bash
set PGPASSWORD=sua_senha_local
"E:\Projetos\PostgreSQL\bin\pg_dump.exe" -h localhost -p 5432 -U postgres -d pge_bi ^
  --data-only --no-owner --no-privileges ^
  -t processos_novos -t pecas_elaboradas -t pecas_finalizadas -t pendencias ^
  -f scripts\dump_data.sql
```

### 2. Preparar o dump (adicionar TRUNCATE + transação)

Abrir `dump_data.sql` e adicionar no **início**:

```sql
BEGIN;
TRUNCATE processos_novos, pecas_elaboradas, pecas_finalizadas, pendencias;
```

E no **final**:

```sql
COMMIT;
```

### 3. Restaurar em produção

```bash
"E:\Projetos\PostgreSQL\bin\psql.exe" ^
  "postgresql://postgres:SENHA@maglev.proxy.rlwy.net:28752/railway" ^
  -f scripts\dump_data.sql -v ON_ERROR_STOP=1
```

### 4. Atualizar assuntos em produção

```bash
REM Limpar tabelas de assuntos
"E:\Projetos\PostgreSQL\bin\psql.exe" ^
  "postgresql://postgres:SENHA@maglev.proxy.rlwy.net:28752/railway" ^
  -c "ALTER TABLE assuntos DISABLE TRIGGER ALL; ALTER TABLE processo_assuntos DISABLE TRIGGER ALL; TRUNCATE processo_assuntos, assuntos; ALTER TABLE assuntos ENABLE TRIGGER ALL; ALTER TABLE processo_assuntos ENABLE TRIGGER ALL;"

REM Dump em formato custom
set PGPASSWORD=sua_senha_local
"E:\Projetos\PostgreSQL\bin\pg_dump.exe" -h localhost -p 5432 -U postgres -d pge_bi ^
  --data-only --no-owner --no-privileges ^
  -t assuntos -t processo_assuntos ^
  -Fc -f scripts\dump_assuntos.dump

REM Restaurar com triggers desabilitados
set PGPASSWORD=SENHA_RAILWAY
"E:\Projetos\PostgreSQL\bin\pg_restore.exe" ^
  --host=maglev.proxy.rlwy.net --port=28752 ^
  --username=postgres --dbname=railway ^
  --data-only --no-owner --no-privileges --disable-triggers ^
  scripts\dump_assuntos.dump
```

### 5. Verificar contagens

```bash
"E:\Projetos\PostgreSQL\bin\psql.exe" ^
  "postgresql://postgres:SENHA@maglev.proxy.rlwy.net:28752/railway" ^
  -c "SELECT 'processos_novos', COUNT(*) FROM processos_novos UNION ALL SELECT 'pecas_elaboradas', COUNT(*) FROM pecas_elaboradas UNION ALL SELECT 'pecas_finalizadas', COUNT(*) FROM pecas_finalizadas UNION ALL SELECT 'pendencias', COUNT(*) FROM pendencias UNION ALL SELECT 'assuntos', COUNT(*) FROM assuntos UNION ALL SELECT 'processo_assuntos', COUNT(*) FROM processo_assuntos ORDER BY 1;"
```

### 6. Limpar dumps

```bash
del scripts\dump_data.sql scripts\dump_assuntos.dump
```

## Logs

Os logs são salvos em `scripts/logs/etl_YYYY-MM-DD.log` e também exibidos no terminal.

## Volumes de dados (referência fev/2026)

| Tabela | Registros |
|--------|----------:|
| processos_novos | ~138k |
| pecas_elaboradas | ~1.32M |
| pecas_finalizadas | ~1.31M |
| pendencias | ~1.16M |
| assuntos | ~7.2k |
| processo_assuntos | ~1M |

## Estrutura dos scripts

```
scripts/
├── etl_oracle.py          # Script principal (CLI)
├── etl/
│   ├── __init__.py
│   ├── config.py           # Configurações e constantes
│   ├── extractor.py        # Extração do Oracle (thick mode)
│   ├── loader.py           # Carga no PostgreSQL (upsert)
│   ├── oracle_queries.py   # Queries SQL Oracle
│   └── tunnel.py           # VPN + túnel SSH
├── oracle_dbeaver.bat      # Abre conexão Oracle no DBeaver
├── logs/                   # Logs diários do ETL
└── ETL.md                  # Esta documentação
```

## Solução de problemas

| Erro | Causa | Solução |
|------|-------|---------|
| `DPY-3010: thin mode not supported` | Oracle 11g requer thick mode | Verificar Instant Client em `C:\oracle\instantclient_21_20` |
| `VPN_USER/VPN_PASSWORD não encontradas` | Variáveis faltando no .env | Adicionar credenciais VPN ao `.env` |
| `Túnel SSH não ficou disponível` | VPN desconectada ou chave SSH inválida | Verificar VPN com `rasdial` e testar SSH manualmente |
| `ForeignKeyViolation assuntos` | FK auto-referencial durante insert | Já tratado: triggers desabilitados durante upsert |
| `connection refused localhost:1521` | Túnel SSH caiu | Verificar VPN e rodar novamente |
