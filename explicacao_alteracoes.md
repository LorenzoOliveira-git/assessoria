# Explicação das alterações do AssessorIA

Este documento explica a correção do fluxo de escritas do chat, em linguagem simples. Ele descreve o estado atual dos arquivos. Algumas alterações em `app/graph.py` e `app/prompts.py`, além das imagens de `assets/img/`, já existiam no trabalho local e foram preservadas.

## 1. Qual era o problema?

O juiz avalia a resposta **depois** que os agentes usam as tools. Antes da correção, as tools de finanças e agenda gravavam imediatamente. Assim, podia acontecer isto:

1. O usuário pedia um lançamento ou evento.
2. A tool gravava no banco.
3. O agente respondia que tinha gravado.
4. O juiz reprovava a resposta e mostrava “Não tenho evidência para afirmar isso.”

O usuário recebia uma negativa, mas o registro já existia. Os exemplos originais estão em `evidencias.md`. A criação no Google Calendar tinha o mesmo problema de ordem: poderia ocorrer antes do juiz.

**Objetivo da correção:** se o juiz rejeitar a resposta, nenhuma escrita pendente daquele pedido deve ser feita. Se a gravação falhar após a aprovação, o usuário não deve receber uma confirmação falsa.

## 2. Como o fluxo funciona agora?

Exemplo: “Registre um gasto de R$ 17 em lanche”.

1. O agente chama `add_transaction`, como antes.
2. A chamada recebe **`status: pendente`**. Nesse momento ainda não há novo registro nem ID do banco.
3. A resposta provisória do agente e a lista de operações pendentes vão para o juiz.
4. Se o juiz reprovar, as operações são descartadas. Se aprovar, o código executa as operações.
5. O banco confirma o lote de escritas. Só então o código monta a resposta final usando os resultados reais, como o ID devolvido pelo banco.

O juiz continua avaliando a resposta do agente. Ele **não** faz a gravação e **não** consegue enxergar um commit que ainda não aconteceu. Depois do veredito, quem executa e confirma é código comum, sem pedir a outro modelo que invente uma resposta.

## 3. Por que `app/escritas.py` é importante?

Esse é o arquivo que permite **adiar a escrita**. Sem ele, a tool continuaria fazendo `INSERT` ou `UPDATE` assim que o agente a chamasse, antes de o juiz decidir. Pense nele como uma ficha temporária do pedido: anota “o que seria gravado”, espera a decisão e só então chama a função original.

Ele **não é um cache**, um Redis local, uma tabela ou uma fila. Os dados pendentes ficam na memória apenas enquanto aquela mensagem do chat está sendo processada. Ao fim do pedido, o contexto é encerrado. Por isso, Upstash Redis não é necessário para esta solução.

### O que cada parte faz

| Parte | Explicação simples | Por que existe |
|---|---|---|
| `contexto()` e `atual()` | Criam e encontram a ficha do pedido atual. | Evitam misturar operações de pedidos diferentes. |
| `serializar()` | Faz um pedido de chat passar por vez neste processo. | Evita que execuções simultâneas disputem o histórico local do grafo. |
| `escrita()` | É colocado nas quatro tools que escrevem. Na primeira chamada, guarda a intenção e devolve “pendente”. | Impede que a gravação aconteça antes do juiz, mantendo a tool disponível para pedidos válidos. |
| `_preparar()` | Confere os argumentos e, no caso de atualização, localiza a transação antes de tentar alterá-la. | Evita levar ao juiz uma operação com valor incompatível ou alvo ambíguo. Essa consulta ao banco **não grava**. |
| `Turno.preparar()` | Guarda o nome da tool e seus argumentos; chamadas idênticas no mesmo pedido viram uma única operação. | Evita executar duas vezes a mesma intenção dentro do turno. |
| `Turno.manifesto()` | Produz a lista exata das operações pendentes para o juiz e fecha a preparação. | O juiz avalia o que foi proposto, sem tratar “pendente” como prova de gravação. |
| `Turno.concluir()` | Recebe a decisão do juiz. Só executa se houver aprovação explícita e nenhum erro de preparação. | É o ponto que transforma uma intenção em escrita real. |
| `_recibo()` | Monta a confirmação a partir dos retornos reais das tools. | O usuário não recebe um ID ou sucesso inventado pelo agente. |

O **ID da operação pendente** identifica uma intenção dentro do pedido. Ele não é o ID de uma transação ou evento no banco. O ID do banco só aparece depois que a tool original realmente executa.

Se houver mais de uma escrita local, `concluir()` manda todas para um único lote SQL. Se alguma falhar, o banco desfaz o lote. A chamada ao Google Calendar vem depois da confirmação local. A mesma chamada de conclusão retorna a resposta já calculada, sem repetir a escrita dentro do mesmo turno.

### A regra de moeda neste arquivo

`moeda_brl()` reconhece menções explícitas a reais no texto. `validar_valor()` compara o valor que o agente quer gravar com o valor em reais informado pelo usuário. Por exemplo, um pedido de **R$ 17** pode preparar uma escrita de **17**; um pedido sem valor em reais não deve ser transformado silenciosamente em R$ 17.

Essa verificação acontece **no código, antes do juiz**. O prompt orienta o agente, mas não é a barreira de segurança. Na atualização de um valor, o código também lê o `source_text` do registro antigo para verificar se há indicação reconhecível de reais.

## 4. O que mudou em cada arquivo?

### `app/graph.py` — liga as etapas do chat

- Abre o contexto temporário do pedido antes de rodar os agentes e o encerra ao terminar.
- No nó `no_juiz`, junta à evidência as operações pendentes e recebe a decisão do JEV.
- Em caso de aprovação, chama `Turno.concluir(True)`; em caso de rejeição ou falha do juiz, chama `Turno.concluir(False)`.
- Publica o resultado real da escrita no lugar da confirmação provisória do modelo. O status da escrita também chega ao monitor do turno.
- Inclui `add_google_event` na coleta de chamadas de escrita para as evidências.

Os registros de estado inicial e final e outras alterações locais que já estavam nesse arquivo foram mantidos. A ordem geral do grafo não foi alterada.

### `app/juiz.py` — deixa o veredito explícito

- Passou a devolver `juiz_aprovado: True` somente quando a resposta é classificada como apoiada e atinge o limiar exigido.
- Limpa a resposta anterior ao encontrar uma nova pergunta do usuário, para o juiz não avaliar uma resposta velha.
- Rejeita uma pontuação inválida, como um valor não finito.

Isso permite que o grafo use uma decisão clara. Um texto de log, o nome da tool ou uma classificação incompleta não autorizam a escrita.

### `app/prompts.py` — ensina o significado de “pendente”

- Os exemplos de finanças e agenda deixaram de dizer “registrei” ou mostrar um ID logo após a primeira chamada da tool.
- As instruções agora pedem que os agentes não confundam operação preparada com gravação confirmada e não afirmem que convites foram aceitos sem prova.
- A instrução do juiz esclarece que uma intenção pendente não prova persistência.

Essas instruções ajudam a produzir uma resposta provisória coerente. A garantia de não gravar antes do juiz está em `escritas.py` e `graph.py`, não depende apenas do prompt. Uma pequena edição local anterior no título da seção de agenda foi preservada.

### `app/tools/db.py` — confirma as escritas locais juntas

- Foi acrescentado `lote_sql()`, que abre uma conexão para todas as escritas locais aprovadas e faz um único `commit` no final.
- As tools antigas tentam fazer seus próprios `commit()` e `close()`. Durante o lote, uma conexão intermediária adia essas chamadas para que a decisão final seja conjunta.
- Se alguma escrita falhar, o lote faz `rollback`, isto é, desfaz as alterações ainda não confirmadas.

Fora desse lote, `get_conn()` continua abrindo uma conexão normalmente para as leituras.

### `app/tools/financeiro.py` — adia inserções e atualizações

- `add_transaction` e `update_transaction` receberam `@escrita`. Suas funções originais continuam responsáveis pela gravação depois da aprovação.
- `search_transactions` mostra a moeda como `BRL` quando o texto de origem indica reais; caso contrário, mostra `desconhecida`.
- `saldo_total` e `saldo_diario` deixam de apresentar um saldo em reais se o período incluir uma transação de moeda desconhecida.

Não foi criada tabela nem coluna de moeda. Como o banco antigo guarda apenas o valor e o texto de origem, essa identificação é uma aproximação conservadora.

### `app/tools/agenda.py` — adia o evento local

`add_event` recebeu `@escrita`. Assim, a criação na tabela de eventos espera o veredito, como as operações financeiras. A consulta de eventos continua uma leitura normal.

### `app/tools/calendario_google.py` — adia o efeito externo

`add_google_event` também recebeu `@escrita`. O código que conversa com o Google, inclusive o fallback MCP/REST que já existia, foi preservado. O controlador só chama essa tool depois da aprovação e do lote SQL local.

### `tests/test_escritas.py` — verifica efeitos, não só mensagens

Arquivo novo com **9 testes**. Ele usa um banco SQLite descartável no lugar do PostgreSQL e uma chamada simulada ao Google. Os testes conferem os registros antes e depois do veredito, aprovação, rejeição, erro no meio do lote, commit incerto, moeda, falha parcial do Google e o caminho do grafo com FAQ e guardrail. O comando usado foi `.venv\Scripts\python.exe -m unittest discover -s tests -q`; os 9 testes passaram.

### Documentos e imagens

- `decisao_tecnica.md` foi preenchido para comparar alternativas e registrar por que a escrita adiada foi escolhida.
- `evidencias.md` manteve os casos e imagens anteriores e recebeu a seção de validação da correção.
- As imagens em `assets/img/` já faziam parte das evidências locais e não foram alteradas por esta correção.
- Este arquivo, `explicacao_alteracoes.md`, foi criado para a apresentação ao professor.

Durante a simplificação, `app/observabilidade.py` voltou à versão anterior. Os arquivos temporários `tests/test_fluxo.py` e `dados/relacional/03_moeda.sql`, criados numa versão intermediária, foram removidos. No estado atual, não há mudança de esquema do banco, Redis, nova rota, novo agente ou mudança no frontend.

## 5. O que a solução garante e quais são seus limites?

**Garante neste fluxo do chat:** uma escrita pendente só é executada com aprovação explícita do juiz; as escritas SQL do mesmo pedido são confirmadas juntas; uma falha não vira mensagem de sucesso. A resposta final de escrita vem do resultado real, e não da frase provisória gerada pelo agente.

**Limites importantes para explicar:**

- PostgreSQL e Google Calendar são serviços separados. Um evento pode ficar salvo na agenda local mesmo se o Google falhar; a resposta informa esse resultado parcial.
- Se a conexão cair exatamente durante o `commit`, pode ser impossível saber imediatamente se o banco confirmou. Nesse caso, a mensagem pede para conferir os registros antes de repetir.
- O texto antigo da transação nem sempre permite saber sua moeda com certeza. O sistema pode recusar um saldo até que os dados sejam esclarecidos.
- O controle de repetição vale dentro do mesmo pedido em execução. Uma nova requisição HTTP é outro pedido. O bloqueio de concorrência é local a um processo.
- Os testes automatizados usaram serviços simulados; não provaram o comportamento de PostgreSQL, Google Calendar e modelos reais em produção.

## 6. Resumo para apresentar oralmente

> “Antes, a tool gravava e só depois o juiz avaliava a resposta. Agora, a tool apenas prepara a operação. O arquivo `escritas.py` guarda essa operação durante o pedido, o juiz decide e o código só grava se houver aprovação. As gravações locais são confirmadas juntas, e a resposta final usa o resultado real. Não criei cache nem mudei o banco: usei a memória temporária do pedido e mantive o restante do projeto o mais próximo possível do original.”
