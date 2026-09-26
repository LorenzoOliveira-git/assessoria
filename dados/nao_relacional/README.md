# Banco não relacional — MongoDB

Modelagem baseada na implementação de [app/memory.py](../../app/memory.py) e [app/perfil.py](../../app/perfil.py).

## Conexão e banco

A conexão usa `MONGODB_URI` do `.env`. A aplicação seleciona explicitamente o banco **`assessor`**, independentemente do banco indicado na URI.

O acesso configurado precisa permitir leitura, escrita e criação dos índices utilizados pela aplicação. As coleções são criadas conforme as operações do código; não é necessário importar conversas ou perfis de exemplo.

## Preparação local

1. Disponibilize uma instância MongoDB e configure sua URI em `MONGODB_URI`.
2. Garanta que o usuário da conexão tenha as permissões descritas acima no banco `assessor`.
3. Prepare também o [Qdrant](../vetorial/README.md), usado no encerramento de sessões e na gravação de restrições do perfil.
4. Inicie a API conforme o [README principal](../../README.md). Os índices de sessões são criados na inicialização; o índice único de perfis é garantido ao salvar um perfil.

Não há scripts SQL ou carga inicial para o MongoDB. As mensagens e os perfis são gravados pelas operações da aplicação.

## Coleção `sessoes`

Armazena documentos de conversa com os seguintes campos:

- `_id`: UUID armazenado como string, gerado pela aplicação para o documento.
- `session_id`: string que identifica a conversa; também é usada para localizar a sessão ativa.
- `user_id`: string que identifica o usuário entre conversas. O padrão atual é `usuario_teste`.
- `iniciada_em`: data e hora de criação, gerada em UTC.
- `atualizada_em`: data e hora da última mensagem salva, gerada em UTC.
- `resumo`: string inicialmente vazia, preenchida ao encerrar uma conversa com mensagens.
- `mensagens`: lista de objetos com `role` e `content`, ambos strings.

Exemplo ilustrativo de mensagem:

```json
{
  "role": "usuario",
  "content": "Gastei 50 reais no mercado hoje."
}
```

O código cria índices individuais, não únicos, em `session_id`, `user_id` e `iniciada_em` durante a importação do módulo de memória. Por isso, o MongoDB precisa estar acessível na inicialização da API.

### Ciclo da conversa

1. A aplicação inicia uma sessão explicitamente ou ao salvar a primeira mensagem.
2. Cada mensagem é acrescentada à lista `mensagens`, atualizando `atualizada_em`.
3. Ao encerrar uma sessão com mensagens, um modelo gera o resumo, que é salvo no MongoDB.
4. O resumo também é convertido em embedding e enviado ao Qdrant, com `user_id` e `session_id`.
5. A recuperação de histórico utiliza busca vetorial quando há uma consulta; sem resultados vetoriais, consulta sessões resumidas no MongoDB, filtradas por `user_id` e ordenadas por `iniciada_em`.

`session_id` identifica a conversa; `user_id` identifica o usuário. Esses identificadores não constituem autenticação.

## Coleção `perfis`

Armazena os dados estruturados do perfil financeiro:

- `_id`: identificador gerado pelo MongoDB.
- `user_id`: string que identifica o usuário.
- `renda_mensal`: número positivo.
- `gasto_fixo_mensal`: número não negativo e menor que a renda mensal.
- `horizonte_meses`: inteiro entre 1 e 120.
- `perfil_investidor`: `conservador`, `moderado` ou `arrojado`.
- `atualizado_em`: data e hora da última gravação, gerada em UTC.

Ao salvar um perfil, o código garante um índice **único** em `user_id` e utiliza `upsert`: atualiza o perfil existente ou cria um novo.

As frases de `restricoes` recebidas pelo formulário não são armazenadas nessa coleção. Elas são persistidas no Qdrant, na collection `perfil_restricoes`.

## Limites da modelagem atual

As mensagens ficam em uma lista dentro do documento da sessão. O código não implementa expiração automática ou política de retenção dessas conversas. O estado de execução do grafo LangGraph fica em memória do processo e é distinto do histórico persistido no MongoDB.
