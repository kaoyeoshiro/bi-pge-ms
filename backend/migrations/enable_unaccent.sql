-- Habilita extensão unaccent para buscas sem acentos
-- Executar como superusuário ou com permissão CREATE EXTENSION

CREATE EXTENSION IF NOT EXISTS unaccent;

-- Teste rápido:
-- SELECT unaccent('Ação de Cobrança');
-- Resultado esperado: 'Acao de Cobranca'
