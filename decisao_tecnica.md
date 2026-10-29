# Decisão técnica: autorização das escritas pelo juiz

**Relação com as evidências.** O arquivo [evidencias.md](evidencias.md) registra os casos observados **antes** da correção, nos quais houve gravação apesar da reprovação da resposta. Além disso, a verificação **depois** é feita também nesse arquivo a fim de mostrar o aumento em latência com a solução.

## Glossário

| Termo | Significado neste projeto |
|---|---|
| Grafo | Sequência de etapas do chat: guardrails, roteador, especialista, orquestrador e juiz. |
| Tool | Função que o agente pode chamar para consultar dados ou executar uma ação. |
| JEV ou juiz | Serviço que avalia se a resposta candidata é sustentada pela pergunta e pelas evidências. Ele não chama as tools de escrita. |
| Guardrail | Verificação de entrada ou saída que pode bloquear ou revisar conteúdo. |
| Turno | Processamento de uma mensagem do usuário. Um `session_id` identifica a conversa; um `turno_id` identifica aquela execução. |
| SQL, PostgreSQL e SQLite | SQL é a linguagem de operações no banco; PostgreSQL é o banco da aplicação; SQLite é o banco descartável usado nos testes isolados. |
| MongoDB | Banco usado para o histórico da conversa, separado das tabelas financeiras e de agenda. |
| Intenção pendente | Descrição de uma escrita proposta, ainda sem efeito no banco ou no Calendar. |
| `operacao_id` | Marcador formado por `turno_id` e número sequencial. Identifica a intenção, não uma linha do banco. |
| Manifesto | Lista das operações pendentes e seus argumentos, entregue ao juiz junto da resposta candidata. |
| Fronteira de autorização | Ponto do fluxo a partir do qual uma escrita pode ser executada: o veredito explícito de aprovação. |
| Transação SQL | Conjunto de alterações locais confirmado como um lote. `commit` confirma; `rollback` desfaz alterações ainda não confirmadas. |
| Efeito externo | Ação no Google Calendar, que não participa da transação do PostgreSQL. |
| Idempotência | Propriedade de repetir uma solicitação sem repetir seu efeito. Aqui, a repetição é controlada apenas dentro do mesmo turno. |
| Compensação | Tentativa de desfazer uma escrita já confirmada por meio de outra operação. |
| Fallback | Tentativa de usar outro caminho de execução quando o principal falha; o transporte MCP/REST do Calendar já possuía esse mecanismo. |
| MCP e REST | Dois caminhos de comunicação que a integração existente pode usar para acessar o Calendar. |
| Redis ou Upstash | Serviço externo que poderia guardar intenções entre processos; não foi necessário nesta implementação. |
| Lock | Controle local que impede a sobreposição de execuções concorrentes neste processo. |
| `source_text` | Texto de origem guardado com a transação, usado para avaliar se há indicação reconhecível de reais. |
| Latência, p95 e SLO | Tempo de resposta; o p95 é o valor abaixo do qual ficam 95% dos turnos medidos; SLO é o limite definido para o serviço. |
| SRE | Prática de acompanhar a confiabilidade do serviço por métricas e limites operacionais. |
| Tokens e custo | Volume de texto contabilizado pelas chamadas de modelos e estimativa de seu preço no monitor. |

## 1. Decisão tomada e justificativa

### Antes e depois

| Antes da correção | Depois da correção |
|---|---|
| O agente chamava `add_transaction`, `update_transaction` ou `add_event`; cada tool podia confirmar sua própria escrita antes do juiz. | A chamada registra uma intenção no turno e retorna `status: pendente`, sem ID de registro e sem gravação. |
| O orquestrador e o guardrail produziam a resposta; o JEV a avaliava após o efeito permanente. | O JEV recebe a resposta candidata e o manifesto das intenções ainda não executadas. |
| Uma reprovação podia substituir a confirmação por uma frase segura, embora o banco já tivesse mudado. | Só a aprovação explícita autoriza o lote SQL. A recusa descarta as intenções; o resultado real do lote determina a resposta final. |

A decisão foi **adiar as escritas até o veredito do juiz**. A fronteira de autorização está no nó `no_juiz`, em `app/graph.py`, que passa o veredito explícito para `Turno.concluir()` em `app/escritas.py`. Essa escolha cabe no grafo atual porque o juiz já é uma etapa posterior ao especialista e ao guardrail de saída. Não foi necessário acrescentar agente, rota ou chamada adicional ao JEV.

As três tools PostgreSQL, `add_transaction`, `update_transaction` e `add_event`, seguem a mesma regra: preparar, aguardar, executar somente após aprovação e confirmar em um único lote SQL. Se uma delas falhar, o lote é desfeito e não se publica uma confirmação de sucesso. A resposta final de escrita é construída a partir dos retornos das tools depois da tentativa de gravação; o juiz não precisa observar um `commit` futuro nem redigir uma nova confirmação.

O contexto das operações existe apenas na memória do turno. Chamadas idênticas com os mesmos argumentos recebem o mesmo `operacao_id` nesse turno. O manifesto fecha a preparação antes da avaliação. Um lock local impede a sobreposição de pedidos neste processo; ele não coordena servidores diferentes.

## 2. Caminhos considerados e não adotados

| Caminho | Como funcionaria neste grafo | Vantagem real | Custo real e motivo da exclusão |
|---|---|---|---|
| Julgar cada tool antes de executá-la | Cada chamada de escrita consultaria o JEV antes do `INSERT`, `UPDATE` ou evento. | A decisão ocorreria perto de cada ação; uma recusa impediria aquela ação imediatamente. | Um pedido com três escritas exigiria três avaliações adicionais. Além da latência e das possíveis falhas de rede, essas avaliações isoladas não examinariam a resposta final do orquestrador. O juiz já existente continuaria necessário. |
| Manter uma transação SQL aberta durante todo o grafo | As tools escreveriam dentro de uma transação iniciada antes do especialista; o juiz decidiria entre `commit` e `rollback`. | O banco poderia desfazer as três escritas locais após uma recusa. | A conexão e os bloqueios de linhas permaneceriam ocupados enquanto modelos, guardrail e JEV respondessem. Isso amplia contenção e tempo de espera em pedidos concorrentes. O Google Calendar continuaria fora da transação. |
| Gravar e compensar após a recusa | As tools confirmariam normalmente; uma reprovação dispararia `DELETE`, outro `UPDATE` ou cancelamento do evento. | Preservaria parte do fluxo antigo, com confirmação imediata das tools. | A primeira gravação já seria visível. A compensação pode falhar, atingir um registro alterado posteriormente ou não desfazer um convite externo. Portanto, não sustenta a garantia de recusa sem efeito. |
| Guardar intenções em Redis ou Upstash | O turno registraria operações em um serviço externo e as recuperaria após o juiz. | Facilitaria compartilhar estado entre instâncias e sobreviver a alguns reinícios, desde que houvesse controle de expiração e reprocessamento. | Exigiria operação, limpeza e correlação de um novo serviço. Redis não torna atômicos PostgreSQL e Google Calendar. Como o sistema executa o turno no mesmo processo, memória temporária atende à necessidade atual. |

Uma mudança apenas nos prompts também foi descartada como mecanismo de segurança: o modelo poderia seguir ou contrariar uma instrução textual, e a tool ainda gravaria antes do juiz. Os prompts foram ajustados para descrever corretamente o estado pendente, enquanto a autorização efetiva ficou no código.

## 3. Efeito esperado nas métricas de SRE

O monitor da Etapa 6 mede o turno entre `abrir_turno()` e `fechar_turno()` em `app/graph.py`. Nesse intervalo estão a execução do grafo, o JEV, o lote SQL aprovado, a tentativa no Calendar e o salvamento do histórico. A espera para adquirir o lock externo e a anonimização anterior à abertura do turno não entram nessa latência. O painel não separa o tempo gasto em JEV, SQL e Google.

| Métrica | Decisão adotada: adiar | Alternativa: julgar cada tool antes de executá-la |
|---|---|---|
| Latência do turno e p95 | Não há uma chamada adicional ao JEV. Há preparação e um lote SQL curto após a aprovação; na recusa, as escritas são evitadas. O efeito líquido no p95 depende da carga e ainda não foi medido com serviços reais. | Cada escrita acrescentaria uma requisição ao JEV. Com várias escritas, a soma dessas esperas tenderia a aumentar a latência e poderia levar o p95 acima do SLO de **8 s**. |
| Taxa de erro, SLO de **5%** | O monitor conta `status: erro` dividido pelos turnos concluídos. Uma recusa normal de escrita gera `bloqueado`, sem aumentar essa taxa. Falha no JEV, no lote ou no Calendar pode gerar `erro`. | Mais requisições ao JEV criariam mais oportunidades de timeout ou falha HTTP. Se essas falhas terminassem em `erro`, poderiam elevar a taxa; uma recusa deliberada continuaria sendo `bloqueado`. |
| Estados `ok`, `erro`, `bloqueado` | Escrita confirmada: `ok`; recusa do juiz com intenção pendente: `bloqueado`; falha ou resultado incerto: `erro`. Bloqueio do guardrail de entrada também é `bloqueado`, não erro. | Exigiria registrar o resultado de cada julgamento parcial e distinguir recusa de indisponibilidade antes do juiz final. Sem essa instrumentação, uma frase segura emitida sem exceção poderia aparecer como `ok` indevidamente. |
| Tokens e custo | A quantidade de chamadas de modelos permanece, em princípio, a do fluxo existente. O texto adicional dos prompts pode alterar tokens. O JEV é chamado por HTTP e seu uso não entra na contagem de tokens e custo do monitor. | As avaliações adicionais ao JEV aumentariam uso externo, mas **não apareceriam** no custo de modelos calculado pelo monitor atual. Portanto, custo exibido e custo real poderiam divergir ainda mais. |

O monitor atual armazena até 50 turnos no processo, estima custo com uma tabela fixa e calcula p95 e taxa de erro a partir desses registros. Não houve alteração em `app/observabilidade.py` nem em `app/routes/monitor.py`; o novo fluxo apenas fornece o `status_escrita` ao fechamento do turno. O monitor não contabiliza o custo do JEV, do banco ou do Google. Também não há medição antes/depois em produção que permita afirmar melhoria numérica do p95 ou cumprimento do SLO após a correção.

Uma transação aberta durante todo o grafo, caso tivesse sido escolhida, não acrescentaria tokens diretamente, mas manteria uma conexão ocupada durante a espera pelo JEV. Sob concorrência, esse mecanismo poderia ampliar a latência e o p95 de outros turnos; o monitor atual mostraria o efeito total, sem atribuí-lo à espera por conexão.

## 4. Escopo, falhas e evidências

### Outras decisões de escopo

- **Google Calendar:** `add_google_event` também é preparada antes do juiz. Após aprovação, o controlador confirma primeiro o lote SQL e só então tenta o efeito externo. Não há transação conjunta entre PostgreSQL e Calendar. Se o Google falhar, a gravação local pode permanecer e a resposta informa o resultado parcial. O fallback MCP/REST anterior foi preservado; o controlador não repete automaticamente a operação após uma resposta incerta.
- **Histórico da conversa:** `salvar_mensagem` permaneceu fora do lote de escritas financeiras e de agenda. Ele é chamado depois do grafo, inclusive quando o juiz publica uma recusa, para conservar o histórico do atendimento. Uma falha no MongoDB após um `commit` SQL pode fazer a requisição terminar em erro apesar de a escrita local ter sido confirmada; não existe transação distribuída entre esses serviços.
- **Moeda:** sem alterar o esquema do banco, novas inserções e alterações de valor exigem indicação reconhecível de reais no texto. Transações antigas de moeda não identificável podem aparecer em consultas, mas impedem apresentar um saldo completo em reais. O texto livre não substitui uma coluna estruturada de moeda; esta é uma limitação assumida.

Se o juiz não responder, devolver resultado inválido ou ficar indisponível, não há aprovação explícita: as operações pendentes são descartadas e nenhuma confirmação de escrita é publicada. Uma recusa regular fica como `bloqueado`; uma falha do juiz fica como `erro` no turno com escrita pendente.

Uma queda do processo **antes do commit** perde as intenções em memória; o banco desfaz uma transação ainda aberta quando a conexão é encerrada. Uma queda **após o commit e antes do Calendar ou da resposta** pode deixar apenas a escrita local confirmada, sem recibo entregue. Uma queda **após uma chamada ao Google sem retorno conclusivo** deixa o estado externo incerto. Nesses casos, a orientação é consultar os registros antes de repetir.

Repetir a mesma tool com os mesmos argumentos **no mesmo turno** reutiliza a intenção. Repetir `concluir()` devolve a resposta já calculada e não executa outra vez. Uma nova requisição HTTP cria outro turno; sem uma chave de idempotência na API, não é possível distinguir reenvio de novo pedido. A serialização local não cobre várias instâncias do servidor.

### Evidência com marcadores de turno e operação

Os três cenários anteriores à correção estão em [evidencias.md](evidencias.md). Para verificar o comportamento posterior sem alterar dados reais, foi executada uma verificação isolada com a base SQLite descartável de [tests/test_escritas.py](tests/test_escritas.py). Cada cenário recebeu um `turno_id` próprio. As três tools foram chamadas duas vezes com os mesmos argumentos; em cada caso, ambas as preparações devolveram o mesmo `operacao_id`. As funções originais foram observadas quanto ao número de execuções, e `concluir()` também foi chamado duas vezes. A decisão do juiz foi **simulada** como recusa ou aprovação; não houve chamada ao JEV real.

| Marcador do cenário | Operações identificadas | Antes → depois | Execuções reais e confirmação |
|---|---|---|---|
| Recusa: `SRE-19adc20056fa4bbea5ec739635defea4` | `:1` = `add_transaction`; `:2` = `update_transaction`; `:3` = `add_event` | Transações **1 → 1**; eventos **0 → 0**; valor do registro atualizado permaneceu **10**. | Cada tool: **0** execução; **0** `commit`. |
| Aprovação: `SRE-fa07c0d58e594396a6f3ab9db5b4d0cd` | `:1` = `add_transaction`; `:2` = `update_transaction`; `:3` = `add_event` | Transações **1 → 2**; eventos **0 → 1**; valor do registro atualizado **10 → 23**. | Cada tool: **1** execução; **1** `commit` para o lote. |

Em cada linha, o identificador completo de uma operação é o marcador do cenário seguido do sufixo indicado, por exemplo `SRE-fa07c0d58e594396a6f3ab9db5b4d0cd:2`. Os IDs de operação não são IDs de linhas do banco. O teste do grafo também verifica, com o JEV simulado, que uma recusa ou timeout não cria a transação e que a aprovação permite a inserção. A suíte existente registrou **9 testes aprovados**. Esses resultados sustentam o comportamento do código em ambiente controlado; não comprovam integração com PostgreSQL, Calendar e JEV reais.

## 5. Arquivos criados e arquivos modificados

### Criados

- `app/escritas.py` — contexto temporário, preparação das intenções, aplicação do veredito e recibos determinísticos.
- `decisao_tecnica.md` — documenta a decisão, alternativas, métricas, limites e evidências.
- `evidencias.md` — manteve os casos anteriores e recebeu o inventário e a referência à correção.
- `assets/img/` - módulo de imagens para o documento de evidências.

### Modificados

- `app/graph.py` — passou a abrir o contexto do turno, apresentar o manifesto ao juiz, aplicar o veredito e comunicar o estado da escrita ao monitor; alterações locais anteriores de registro de evidências foram preservadas.
- `app/juiz.py` — passou a devolver aprovação explícita, limpar a resposta antiga a cada nova pergunta e recusar pontuação inválida.
- `app/prompts.py` — exemplos e instruções passaram a distinguir intenção pendente de gravação confirmada; uma edição local anterior foi preservada.
- `app/tools/db.py` — passou a oferecer um lote SQL com um único `commit` ou `rollback` para as escritas aprovadas.
- `app/tools/financeiro.py` — adiou inserção e atualização e passou a identificar moeda desconhecida em consultas e saldos.
- `app/tools/agenda.py` — adiou `add_event` até a aprovação.
- `app/tools/calendario_google.py` — adiou `add_google_event`, preservando o transporte e o fallback existentes.
