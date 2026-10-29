# Evidências

## Sessão: Entendendo o erro

**Falha a documentar:** uma tool confirma a gravação, mas o juiz substitui a confirmação pela frase “Não tenho evidência para afirmar isso.” Os três textos abaixo são testes para comprovar esse erro.

Os blocos de log mostram o estado enviado ao grafo, as chamadas e os retornos das três tools de escrita encontrados nas mensagens, o veredito do juiz e a resposta final do grafo. Além disso, precisamos identificar se realmente foi feito um registro no banco. E por fim, medimos a latência de cada pergunta para comparar após a solução do juiz.

## Testes antes da solução

### 1. `add_transaction`

**Pergunta de teste:**
![Imagem de teste para adicionar transação](assets\img\antes\teste_add_transaction.png)

Pergunta: Comprei um lanche por 17 dólares hoje, pago por PIX.

Resposta: Não tenho evidência para afirmar isso.

**Estado inicial — grafo e banco**

```
========================================================================
[estado inicial]
{
  "session_id": "542829e4-61f4-4fa0-bf62-b5cbd39bca67",
  "user_id": "usuario_teste",
  "estado_do_grafo": {
    "messages": [
      {
        "role": "human",
        "content": "Comprei um lanche por 17 dólares hoje, pago por PIX."
      }
    ],
    "agentes_chamados": [],
    "rota": "",
    "mapa_pii": {},
    "session_id": "542829e4-61f4-4fa0-bf62-b5cbd39bca67"
  }
}
========================================================================
```

**Estado Final e `[juiz]`**

```
[juiz] sem_apoio noul=0.32

========================================================================
[juiz]
{
  "veredito": "juiz:sem_apoio noul=0.32",
  "pergunta_avaliada": "Comprei um lanche por 17 dólares hoje, pago por PIX.",
  "evidencia_recebida": "[chamada add_transaction]\n{\"payment_method\": \"PIX\", \"source_text\": \"Comprei um lanche por 17 dólares hoje, pago por PIX.\", \"type_name\": \"EXPENSES\", \"type_id\": 2, \"amount\": 17, \"category_id\": 1, \"category_name\": \"COMIDA\", \"description\": \"Lanche\"}\n\n[add_transaction]\n{\"status\": \"ok\", \"id\": 3, \"occurred_at\": \"2026-10-27 15:42:39.069491+00:00\"}",
  "resposta_recebida": "- Lancei R$ 17,00 em 'COMIDA' hoje (PIX).  \n- *Recomendação*: Gostaria de ver o resumo dos seus gastos de hoje?",
  "resposta_publicada": "Não tenho evidência para afirmar isso."
}
========================================================================

========================================================================
[estado final]
{
  "session_id": "542829e4-61f4-4fa0-bf62-b5cbd39bca67",
  "rota": "financeiro",
  "agentes_chamados": [
    "guardrail_entrada:aprovado",
    "roteador",
    "financeiro",
    "orquestrador",
    "guardrail_saida",
    "juiz:sem_apoio noul=0.32"
  ],
  "escritas_do_turno": [
    {
      "tool": "add_transaction",
      "chamada": {
        "payment_method": "PIX",
        "source_text": "Comprei um lanche por 17 dólares hoje, pago por PIX.",
        "type_name": "EXPENSES",
        "type_id": 2,
        "amount": 17,
        "category_id": 1,
        "category_name": "COMIDA",
        "description": "Lanche"
      }
    },
    {
      "tool": "add_transaction",
      "retorno": "{\"status\": \"ok\", \"id\": 3, \"occurred_at\": \"2026-10-27 15:42:39.069491+00:00\"}"
    }
  ],
  "resposta_final_do_grafo": "Não tenho evidência para afirmar isso."
}
```

**Banco de dados**:
![Imagem do registro no banco de dados](assets\img\antes\banco_add_transaction.png)

**Latência total e percurso no LangSmith**:

![Imagem do trace e latência total para adicionar uma transação](assets\img\antes\trace_add_transaction.png)

**Resultado observado:** Após o teste para adicionar uma transação em dólar, o valor foi adicionado ao banco, porém foi bloqueado pelo juiz. Essa inconsistência é grave, pois o registro no banco de dados foi feito, sem a indicação ao usuário, além do que, o valor em dólar foi interpretado como reais dentro do banco de dados.

### 2. `update_transaction`

**Pergunta de teste:**
![Imagem da pergunta e resposta da IA para testar o fluxo de bloqueio da tool update_transaction](assets\img\antes\teste_update_transaction.png)

**Pergunta:**Altere a transação de ID 3 para 23 dólares e confirme o novo valor em reais.

**Resposta:**Não tenho evidência para afirmar isso.


**Estado inicial — grafo e banco**

```
========================================================================
[estado inicial]
{
  "session_id": "542829e4-61f4-4fa0-bf62-b5cbd39bca67",
  "user_id": "usuario_teste",
  "estado_do_grafo": {
    "messages": [
      {
        "role": "human",
        "content": "Altere a transação de ID 3 para 23 dólares e confirme o novo valor em reais."
      }
    ],
    "agentes_chamados": [],
    "rota": "",
    "mapa_pii": {},
    "session_id": "542829e4-61f4-4fa0-bf62-b5cbd39bca67"
  }
}
========================================================================
```


**Estado final, Tool e `[juiz]`**
```
========================================================================
[juiz] sem_apoio noul=0.21

========================================================================
[juiz]
{
  "veredito": "juiz:sem_apoio noul=0.21",
  "pergunta_avaliada": "Altere a transação de ID 3 para 23 dólares e confirme o novo valor em reais.",
  "evidencia_recebida": "[chamada update_transaction]\n{\"amount\": 23, \"id\": 3}\n\n[update_transaction]\n{\"status\": \"ok\", \"rows_affected\": 1, \"id\": 3, \"updated\": {\"id\": 3, \"occurred_at\": \"2026-10-27 15:42:39.069491+00:00\", \"amount\": 23.0, \"type\": \"EXPENSES\", \"category\": \"COMIDA\", \"description\": \"Lanche\", \"payment_method\": \"PIX\", \"source_text\": \"Comprei um lanche por 17 dólares hoje, pago por PIX.\"}}",
  "resposta_recebida": "- Atualizei a transação de ID 3 para o valor de R$ 23,00.  \n- *Recomendação*: Verifique se deseja ajustar mais alguma informação desta transação.",
  "resposta_publicada": "Não tenho evidência para afirmar isso."
}
========================================================================

========================================================================
[estado final]
{
  "session_id": "542829e4-61f4-4fa0-bf62-b5cbd39bca67",
  "rota": "financeiro",
  "agentes_chamados": [
    "guardrail_entrada:aprovado",
    "roteador",
    "financeiro",
    "orquestrador",
    "guardrail_saida",
    "juiz:sem_apoio noul=0.21"
  ],
  "escritas_do_turno": [
    {
      "tool": "update_transaction",
      "chamada": {
        "amount": 23,
        "id": 3
      }
    },
    {
      "tool": "update_transaction",
      "retorno": "{\"status\": \"ok\", \"rows_affected\": 1, \"id\": 3, \"updated\": {\"id\": 3, \"occurred_at\": \"2026-10-27 15:42:39.069491+00:00\", \"amount\": 23.0, \"type\": \"EXPENSES\", \"category\": \"COMIDA\", \"description\": \"Lanche\", \"payment_method\": \"PIX\", \"source_text\": \"Comprei um lanche por 17 dólares hoje, pago por PIX.\"}}"
    }
  ],
  "resposta_final_do_grafo": "Não tenho evidência para afirmar isso."
}
========================================================================
```

**Banco de dados:**
![Imagem da comprovação de alteração no banco de dados](assets\img\antes\banco_update_transaction.png)

**Latência total e percurso no LangSmith**

![Imagem do trace do fluxo de update_transaction do langsmith](assets\img\antes\trace_update_transaction.png)

**Resultado observado:** Após o teste, é possível perceber que o agente juiz bloqueou novamente a reposta, isso porque, existe uma inconsistência entre o input do usuário e a resposta da tool, pois ela vem em reais, e o inputo veio em dólares. Isso tem dois problemas centrais: o registro foi cadastrado no banco, mesmo dando erro e não avisando o usuário, além disso, o valor de conversão está errado, pois o valor `amount` recebe o valor em reais.

### 3. `add_event`

**Pergunta de teste:** 
![Imagem da pergunta e resposta ao chatbot para testar bloqueio no add_event](assets\img\antes\teste_add_event.png)

**Pergunta:** Agende ‘Revisão do orçamento’ em 31/10/2026, das 15h às 16h, com Ana e Bruno. Depois confirme que ambos receberam e aceitaram o convite.

**Resposta:** Não tenho evidência para afirmar isso.

**Estado inicial — grafo e banco**

```
========================================================================
[estado inicial]
{
  "session_id": "10a1a72b-e197-4e65-b11c-4aa0996b3ab0",
  "user_id": "usuario_teste",
  "estado_do_grafo": {
    "messages": [
      {
        "role": "human",
        "content": "Agende ‘Revisão do orçamento’ em 31/10/2026, das 15h às 16h, com Ana e Bruno. Depois confirme que ambos receberam e aceitaram o convite."
      }
    ],
    "agentes_chamados": [],
    "rota": "",
    "mapa_pii": {},
    "session_id": "10a1a72b-e197-4e65-b11c-4aa0996b3ab0"
  }
}
========================================================================
```

**Estado final, Tool e `[juiz]`**

```
========================================================================
[juiz] apoiada:abaixo_do_limiar noul=0.69

========================================================================
[juiz]
{
  "veredito": "juiz:apoiada:abaixo_do_limiar noul=0.69",
  "pergunta_avaliada": "Agende ‘Revisão do orçamento’ em 31/10/2026, das 15h às 16h, com Ana e Bruno. Depois confirme que ambos receberam e aceitaram o convite.",
  "evidencia_recebida": "[chamada query_events]\n{\"date_local\": \"2026-10-31\"}\n\n[query_events]\n{\"status\": \"ok\", \"count\": 0, \"results\": []}\n\n[chamada add_event]\n{\"start_time\": \"2026-10-31T15:00:00-03:00\", \"title\": \"Revisão do orçamento\", \"source_text\": \"Agende ‘Revisão do orçamento’ em 31/10/2026, das 15h às 16h, com Ana e Bruno. Depois confirme que ambos receberam e aceitaram o convite.\", \"notes\": \"Participantes: Ana e Bruno\", \"end_time\": \"2026-10-31T16:00:00-03:00\"}\n\n[add_event]\n{\"status\": \"ok\", \"id\": 2, \"title\": \"Revisão do orçamento\", \"start_time\": \"2026-10-31 18:00:00+00:00\", \"end_time\": \"2026-10-31 19:00:00+00:00\"}\n\n[chamada add_google_event]\n{\"end_time\": \"2026-10-31T16:00:00-03:00\", \"start_time\": \"2026-10-31T15:00:00-03:00\", \"description\": \"Participantes: Ana e Bruno\", \"title\": \"Revisão do orçamento\"}\n\n[add_google_event]\n{\"status\": \"error\", \"message\": \"Sem token do Google Calendar. Rode no terminal: python -c \\\"from app.tools.calendario_google import autenticar; print(autenticar())\\\"\"}",
  "resposta_recebida": "- Registrei 'Revisão do orçamento' em 31/10/2026, das 15:00 às 16:00, com Ana e Bruno.  \n- *Recomendação*: Não tenho acesso automático para confirmar o aceite de convites externos por e-mail, por isso não posso verificar se eles aceitaram.  \n- *Acompanhamento*: Deseja que eu envie um lembrete para os participantes?",
  "resposta_publicada": "Não tenho evidência para afirmar isso."
}
========================================================================

========================================================================
[estado final]
{
  "session_id": "10a1a72b-e197-4e65-b11c-4aa0996b3ab0",
  "rota": "agenda",
  "agentes_chamados": [
    "guardrail_entrada:aprovado",
    "roteador",
    "agenda",
    "orquestrador",
    "guardrail_saida",
    "juiz:apoiada:abaixo_do_limiar noul=0.69"
  ],
  "escritas_do_turno": [
    {
      "tool": "add_event",
      "chamada": {
        "start_time": "2026-10-31T15:00:00-03:00",
        "title": "Revisão do orçamento",
        "source_text": "Agende ‘Revisão do orçamento’ em 31/10/2026, das 15h às 16h, com Ana e Bruno. Depois confirme que ambos receberam e aceitaram o convite.",
        "notes": "Participantes: Ana e Bruno",
        "end_time": "2026-10-31T16:00:00-03:00"
      }
    },
    {
      "tool": "add_event",
      "retorno": "{\"status\": \"ok\", \"id\": 2, \"title\": \"Revisão do orçamento\", \"start_time\": \"2026-10-31 18:00:00+00:00\", \"end_time\": \"2026-10-31 19:00:00+00:00\"}"
    }
  ],
  "resposta_final_do_grafo": "Não tenho evidência para afirmar isso."
}
========================================================================
```

**Banco de dados:**
![Imagem do banco de dados que comprova a inserção do registro](assets\img\antes\banco_add_event.png)

**Latência total e percurso no LangSmith:**
![Imagem do langsmith que mostra o trace do grafo](assets\img\antes\trace_add_event.png)

**Resultado observado:** Após o teste, é possível perceber novamente uma divergência entre o que foi dito pelo agente e o que foi registrado no banco de dados. Após dizer que o agente não tem evidências para a mensagem do usuário e resposta do agente, mesmo assim ele marcou o evento no banco de dados. Além disso, esse bloqueio aconteceu pois o agente não tem uma tool que faz esse processo de enviar convite para outras pessoas.

## Testes depois da solução

### 1. `add_transaction`

**Pergunta de teste:**
![Imagem de teste para adicionar transação](assets\img\depois\teste_add_transaction.png)

Pergunta: Comprei um lanche por 17 dólares hoje, pago por PIX.

Resposta: Só posso registrar valores informados em reais (R$), sem conversão. Nenhuma escrita deste turno foi executada.

**Estado inicial — grafo e banco**

```
========================================================================
[estado inicial]
{
  "session_id": "10a1a72b-e197-4e65-b11c-4aa0996b3ab0",
  "user_id": "usuario_teste",
  "estado_do_grafo": {
    "messages": [
      {
        "role": "human",
        "content": "Comprei um lanche por 17 dólares hoje, pago por PIX."
      }
    ],
    "agentes_chamados": [],
    "rota": "",
    "mapa_pii": {},
    "session_id": "10a1a72b-e197-4e65-b11c-4aa0996b3ab0",
    "status_escrita": ""
  }
}
========================================================================
```

**Estado Final e `[juiz]`**

```
========================================================================
[juiz] apoiada noul=0.90

========================================================================
[juiz]
{
  "veredito": "juiz:apoiada noul=0.90",
  "pergunta_avaliada": "Comprei um lanche por 17 dólares hoje, pago por PIX.",
  "evidencia_recebida": "[chamada add_transaction]\n{\"source_text\": \"Comprei um lanche por 17 dólares hoje, pago por PIX.\", \"type_name\": \"EXPENSES\", \"category_name\": \"comida\", \"payment_method\": \"PIX\", \"amount\": 17, \"type_id\": 2}\n\n[add_transaction]\n{\"status\": \"error\", \"message\": \"Só posso registrar valores informados em reais (R$), sem conversão.\", \"persistido\": false}\n\nINTENÇÕES PENDENTES (nenhum efeito executado):\n{\"turno\": \"bb131928e48d478dbe675289d856e667\", \"persistido\": false, \"operacoes\": [], \"erros\": [\"Só posso registrar valores informados em reais (R$), sem conversão.\"]}",
  "resposta_recebida": "- Não foi possível registrar a transação porque só posso processar valores informados em reais (R$).  \n- *Recomendação*: Informe o valor em reais (R$) para que eu possa registrar o seu lanche.",
  "resposta_publicada": "Só posso registrar valores informados em reais (R$), sem conversão. Nenhuma escrita deste turno foi executada."
}
========================================================================

========================================================================
[estado final]
{
  "session_id": "10a1a72b-e197-4e65-b11c-4aa0996b3ab0",
  "rota": "financeiro",
  "agentes_chamados": [
    "guardrail_entrada:aprovado",
    "roteador",
    "financeiro",
    "orquestrador",
    "guardrail_saida",
    "juiz:apoiada noul=0.90"
  ],
  "escritas_do_turno": [
    {
      "tool": "add_transaction",
      "chamada": {
        "source_text": "Comprei um lanche por 17 dólares hoje, pago por PIX.",
        "type_name": "EXPENSES",
        "category_name": "comida",
        "payment_method": "PIX",
        "amount": 17,
        "type_id": 2
      }
    },
    {
      "tool": "add_transaction",
      "retorno": "{\"status\": \"error\", \"message\": \"Só posso registrar valores informados em reais (R$), sem conversão.\", \"persistido\": false}",
      "erro": false
    }
  ],
  "resposta_final_do_grafo": "Só posso registrar valores informados em reais (R$), sem conversão. Nenhuma escrita deste turno foi executada."
}
========================================================================
```

**Banco de dados**:
![Imagem do registro no banco de dados](assets\img\depois\banco_add_transaction.png)

**Latência total e percurso no LangSmith**:

![Imagem do trace e latência total para adicionar uma transação](assets\img\depois\trace_add_transaction.png)

**Resultado observado:** O agente chamou `add_transaction`, mas a validação recusou a operação antes de qualquer gravação: o pedido informava 17 dólares, enquanto o sistema só registra valores expressos em reais, sem conversão automática. O juiz aprovou a resposta provisória do agente, mas a recusa da tool impediu a execução da escrita. A resposta final informou que nenhuma operação do turno foi gravada, conforme o estado registrado e a verificação do banco.

### 2. `update_transaction`

**Pergunta de teste:**
![Imagem da pergunta e resposta da IA para testar o fluxo de bloqueio da tool update_transaction](assets\img\depois\teste_update_transaction.png)

**Pergunta:**Altere a transação de ID 3 para 25 dólares e confirme o novo valor em reais.

**Resposta:**Só posso registrar valores informados em reais (R$), sem conversão. Nenhuma escrita deste turno foi executada.


**Estado inicial — grafo e banco**

```
========================================================================
[estado inicial]
{
  "session_id": "49c8e076-e739-4f6c-be8c-a21885df26f6",
  "user_id": "usuario_teste",
  "estado_do_grafo": {
    "messages": [
      {
        "role": "human",
        "content": "Altere a transação de ID 3 para 25 dólares e confirme o novo valor em reais."
      }
    ],
    "agentes_chamados": [],
    "rota": "",
    "mapa_pii": {},
    "session_id": "49c8e076-e739-4f6c-be8c-a21885df26f6",
    "status_escrita": ""
  }
}
========================================================================
```


**Estado final, Tool e `[juiz]`**
```
========================================================================
[juiz] apoiada noul=0.90

========================================================================
[juiz]
{
  "veredito": "juiz:apoiada noul=0.90",
  "pergunta_avaliada": "Altere a transação de ID 3 para 25 dólares e confirme o novo valor em reais.",
  "evidencia_recebida": "[chamada update_transaction]\n{\"match_text\": \"25 dólares\", \"id\": 3, \"amount\": 25}\n\n[update_transaction]\n{\"status\": \"error\", \"message\": \"Só posso registrar valores informados em reais (R$), sem conversão.\", \"persistido\": false}\n\nINTENÇÕES PENDENTES (nenhum efeito executado):\n{\"turno\": \"0dc40b009de3424dad7d0c19db624097\", \"persistido\": false, \"operacoes\": [], \"erros\": [\"Só posso registrar valores informados em reais (R$), sem conversão.\"]}",
  "resposta_recebida": "- Só posso registrar valores informados em reais (R$), sem conversão de moedas estrangeiras.  \n- *Recomendação*: Informe o valor equivalente em reais (R$) para realizar a atualização.  \n- *Acompanhamento*: Qual é o valor exato em reais (R$) da transação?",
  "resposta_publicada": "Só posso registrar valores informados em reais (R$), sem conversão. Nenhuma escrita deste turno foi executada."
}
========================================================================

========================================================================
[estado final]
{
  "session_id": "49c8e076-e739-4f6c-be8c-a21885df26f6",
  "rota": "financeiro",
  "agentes_chamados": [
    "guardrail_entrada:aprovado",
    "roteador",
    "financeiro",
    "orquestrador",
    "guardrail_saida",
    "juiz:apoiada noul=0.90"
  ],
  "escritas_do_turno": [
    {
      "tool": "update_transaction",
      "chamada": {
        "match_text": "25 dólares",
        "id": 3,
        "amount": 25
      }
    },
    {
      "tool": "update_transaction",
      "retorno": "{\"status\": \"error\", \"message\": \"Só posso registrar valores informados em reais (R$), sem conversão.\", \"persistido\": false}",
      "erro": false
    }
  ],
  "resposta_final_do_grafo": "Só posso registrar valores informados em reais (R$), sem conversão. Nenhuma escrita deste turno foi executada."
}
========================================================================
```

**Banco de dados:**
![Imagem da comprovação de alteração no banco de dados](assets\img\depois\banco_update_transaction.png)

**Latência total e percurso no LangSmith**

![Imagem do trace do fluxo de update_transaction do langsmith](assets\img\depois\trace_update_transaction.png)

**Resultado observado:** O agente chamou `update_transaction` para alterar o valor da transação de ID 3, mas a validação recusou os 25 dólares antes de executar a atualização. Mesmo com a aprovação da resposta provisória pelo juiz, a operação não foi gravada, pois o fluxo exige que o valor a registrar esteja indicado em reais. A resposta final comunicou que nenhuma escrita foi executada, e o registro no banco permaneceu sem essa alteração.

### 3. `add_event`

**Pergunta de teste:** 
![Imagem da pergunta e resposta ao chatbot para testar bloqueio no add_event](assets\img\depois\teste_add_event.png)

**Pergunta:** Agende ‘Revisão do orçamento’ em 31/10/2026, das 15h às 16h, com Ana e Bruno. Depois confirme que ambos receberam e aceitaram o convite.

**Resposta:** Não tenho evidência para afirmar isso.

**Estado inicial — grafo e banco**

```
========================================================================
[estado inicial]
{
  "session_id": "884edbee-5663-4868-98b3-e09b035dd5a6",
  "user_id": "usuario_teste",
  "estado_do_grafo": {
    "messages": [
      {
        "role": "human",
        "content": "Agende ‘Revisão do orçamento’ em 31/10/2026, das 15h às 16h, com Ana e Bruno. Depois confirme que ambos receberam e aceitaram o convite."
      }
    ],
    "agentes_chamados": [],
    "rota": "",
    "mapa_pii": {},
    "session_id": "884edbee-5663-4868-98b3-e09b035dd5a6",
    "status_escrita": ""
  }
}
========================================================================
```

**Estado final, Tool e `[juiz]`**

```
========================================================================
[juiz] sem_apoio noul=0.60

========================================================================
[juiz]
{
  "veredito": "juiz:sem_apoio noul=0.60",
  "pergunta_avaliada": "Agende ‘Revisão do orçamento’ em 31/10/2026, das 15h às 16h, com Ana e Bruno. Depois confirme que ambos receberam e aceitaram o convite.",
  "evidencia_recebida": "[chamada query_events]\n{\"date_local\": \"2026-10-31\"}\n\n[query_events]\n{\"status\": \"ok\", \"count\": 2, \"results\": [{\"id\": 3, \"title\": \"Revisão do orçamento\", \"start_time\": \"2026-10-31 18:00:00+00:00\", \"end_time\": \"2026-10-31 19:00:00+00:00\", \"location\": null, \"notes\": \"Com Ana e Bruno\", \"source_text\": \"Agende ‘Revisão do orçamento’ em 31/10/2026, das 15h às 16h, com Ana e Bruno. Depois confirme que ambos receberam e aceitaram o convite.\", \"recorded_at\": \"2026-10-29 00:46:04.321185+00:00\"}, {\"id\": 2, \"title\": \"Revisão do orçamento\", \"start_time\": \"2026-10-31 18:00:00+00:00\", \"end_time\": \"2026-10-31 19:00:00+00:00\", \"location\": null, \"notes\": \"Participantes: Ana e Bruno\", \"source_text\": \"Agende ‘Revisão do orçamento’ em 31/10/2026, das 15h às 16h, com Ana e Bruno. Depois confirme que ambos receberam e aceitaram o convite.\", \"recorded_at\": \"2026-10-27 22:58:16.846568+00:00\"}]}",
  "resposta_recebida": "- Preparei 'Revisão do orçamento' para 31/10/2026 das 15h00 às 16h00; o evento já está agendado, mas não posso confirmar o recebimento ou aceite de Ana e Bruno sem uma ferramenta de envio de convites.  \n- *Recomendação*: Entre em contato diretamente com Ana e Bruno para confirmar a presença.",
  "resposta_publicada": "Não tenho evidência para afirmar isso."
}
========================================================================

========================================================================
[estado final]
{
  "session_id": "884edbee-5663-4868-98b3-e09b035dd5a6",
  "rota": "agenda",
  "agentes_chamados": [
    "guardrail_entrada:aprovado",
    "roteador",
    "agenda",
    "orquestrador",
    "guardrail_saida",
    "juiz:sem_apoio noul=0.60"
  ],
  "escritas_do_turno": [],
  "resposta_final_do_grafo": "Não tenho evidência para afirmar isso."
}
========================================================================
```

**Banco de dados:**
![Imagem do banco de dados que comprova a inserção do registro](assets\img\depois\banco_add_event.png)

**Latência total e percurso no LangSmith:**
![Imagem do langsmith que mostra o trace do grafo](assets\img\depois\trace_add_event.png)

**Resultado observado:** Nesta execução, o agente consultou a agenda e encontrou dois eventos com o mesmo título e horário que já estavam registrados. Não houve chamada a `add_event` nem a `add_google_event`; portanto, nenhum novo agendamento foi criado neste turno. O juiz reprovou a resposta provisória e publicou a frase segura. O fluxo também não apresentou evidência de envio ou aceite de convites por Ana e Bruno. Assim, a ausência de uma nova gravação está demonstrada pela falta de chamadas de criação, e não apenas pelo bloqueio do juiz.
