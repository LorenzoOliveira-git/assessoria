# Banco relacional — PostgreSQL

Esta pasta contém a estrutura do banco operacional fornecida pelo autor e uma carga de referência para instalação local.

## Preparação

Crie um banco vazio em PostgreSQL **18 ou superior** e execute, nesta ordem, pelo editor SQL do seu cliente ou pelo `psql`:

1. [01_estrutura.sql](01_estrutura.sql): tabelas, constraints, relacionamentos e índices.
2. [02_dados_iniciais.sql](02_dados_iniciais.sql): tipos de transação e categorias reconhecidos pelo código.

Exemplo com `psql`, a partir da raiz do repositório, substituindo host, usuário e banco pelos seus valores:

```bash
psql -h localhost -U seu_usuario -d seu_banco -W -v ON_ERROR_STOP=1 -f dados/relacional/01_estrutura.sql
psql -h localhost -U seu_usuario -d seu_banco -W -v ON_ERROR_STOP=1 -f dados/relacional/02_dados_iniciais.sql
```

A senha é solicitada interativamente. Os scripts devem ser executados uma vez em um banco novo; não são migrações para sobrescrever uma estrutura existente. Não contêm transações ou eventos pessoais.

O SQL preserva os tipos, defaults, nomes das constraints e índices fornecidos. As constraints `NOT NULL` nomeadas foram posicionadas nas colunas, sem duplicar a restrição na tabela. Essa forma de modelar constraints nomeadas é documentada no [PostgreSQL 18](https://www.postgresql.org/docs/18/ddl-constraints.html).

## Tabelas e relacionamentos

- `categories`: identificador, nome, descrição opcional e data de criação das categorias.
- `transaction_types`: identificador e nome do tipo de transação.
- `transactions`: valor, tipo, categoria opcional, descrição, forma de pagamento, data do movimento e texto de origem.
- `events`: título, início, término opcional, local, notas, data de registro e texto de origem dos compromissos. A tabela faz parte do banco, embora o agente de agenda ainda não tenha ferramentas conectadas para utilizá-la.

`transactions.type` referencia `transaction_types.id` e tem valor padrão `2`. `transactions.category_id` referencia `categories.id`; a exclusão de uma categoria define essa referência como `NULL` nas transações.

Os índices atendem consultas por início dos eventos, data das transações, categoria com data e dia local no fuso `America/Sao_Paulo`.

## Dados de referência

A carga inicial foi derivada dos contratos e aliases de [app/tools/financeiro.py](../../app/tools/financeiro.py), não de um dump do banco do autor:

- Tipos: `1 = INCOME`, `2 = EXPENSES`, `3 = TRANSFER`. Os cálculos de saldo usam os IDs 1 e 2 diretamente.
- Categorias: `COMIDA`, `BESTEIRA`, `ESTUDO`, `FERIAS`, `TRANSPORTE`, `MORADIA`, `SAUDE`, `LAZER`, `CONTAS`, `INVESTIMENTO`, `PRESENTE` e `OUTROS`.

As sequências dos IDs são ajustadas após a carga para permitir novos cadastros sem colisões.

## Conexão

A conexão é configurada pela variável `DATABASE_URL` no `.env`. As operações estão em [app/tools/financeiro.py](../../app/tools/financeiro.py), e a conexão em [app/tools/db.py](../../app/tools/db.py).

Configure o usuário de conexão com acesso ao schema `public`, às tabelas e às sequências utilizadas nas inserções.
