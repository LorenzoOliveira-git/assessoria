-- Carga de referencia para um banco novo, baseada em app/tools/financeiro.py.
-- Nao representa uma exportacao dos registros pessoais do autor.
-- Executar uma vez, depois de 01_estrutura.sql, com as tabelas vazias.
BEGIN;

INSERT INTO public.transaction_types (id, "type") VALUES
    (1, 'INCOME'),
    (2, 'EXPENSES'),
    (3, 'TRANSFER');

INSERT INTO public.categories (id, name) VALUES
    (1, 'COMIDA'),
    (2, 'BESTEIRA'),
    (3, 'ESTUDO'),
    (4, 'FERIAS'),
    (5, 'TRANSPORTE'),
    (6, 'MORADIA'),
    (7, 'SAUDE'),
    (8, 'LAZER'),
    (9, 'CONTAS'),
    (10, 'INVESTIMENTO'),
    (11, 'PRESENTE'),
    (12, 'OUTROS');

SELECT setval(pg_get_serial_sequence('public.transaction_types', 'id'), (SELECT MAX(id) FROM public.transaction_types));
SELECT setval(pg_get_serial_sequence('public.categories', 'id'), (SELECT MAX(id) FROM public.categories));

COMMIT;
