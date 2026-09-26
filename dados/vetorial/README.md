# Banco vetorial — Qdrant

As três collections utilizam um vetor denso padrão, sem nome, com **768 dimensões** e distância **Cosine**, conforme a configuração do projeto. No painel, esse vetor aparece como `Default`; não crie um vetor nomeado literalmente `Default`.

## Collections e payloads

- `memoria_resumos`: embeddings dos resumos de conversas. Payload: `user_id`, `session_id`, `resumo` e `iniciada_em`. O ID do ponto corresponde ao UUID do documento da sessão no MongoDB.
- `faq_chunks`: trechos do PDF utilizado para responder ao FAQ. Payload: `page_content`, `page_number` e `source`. IDs gerados na ingestão.
- `perfil_restricoes`: restrições do perfil financeiro. Payload: `user_id`, `restricao`, `posicao` e `atualizado_em`. IDs UUID derivados do usuário e da posição da restrição.

As definições usadas pela aplicação estão em [app/tools/vectorstore.py](../../app/tools/vectorstore.py). A conexão utiliza `QDRANT_CLUSTER_ENDPOINT` e `QDRANT_API_KEY` do `.env`.

## Preparação pelo console do Qdrant

Abra o console REST do painel do seu cluster e execute cada requisição abaixo separadamente, apenas para collections que ainda não existam. Em um cliente HTTP externo, use a URL do cluster e o cabeçalho `api-key` com sua chave. Não inclua credenciais nos arquivos versionados.

```http
PUT /collections/faq_chunks
{
  "vectors": { "size": 768, "distance": "Cosine" }
}
```

```http
PUT /collections/memoria_resumos
{
  "vectors": { "size": 768, "distance": "Cosine" }
}
```

```http
PUT /collections/perfil_restricoes
{
  "vectors": { "size": 768, "distance": "Cosine" }
}
```

Mantenha os demais parâmetros nos valores padrão do cluster. As quantidades de pontos exibidas no painel dependem do uso; collections novas começam vazias.

Crie também os índices de payload utilizados para filtrar por usuário:

```http
PUT /collections/memoria_resumos/index?wait=true
{
  "field_name": "user_id",
  "field_schema": "keyword"
}
```

```http
PUT /collections/perfil_restricoes/index?wait=true
{
  "field_name": "user_id",
  "field_schema": "keyword"
}
```

O código também garante esses índices ao utilizar a memória e o perfil, e cria `perfil_restricoes` caso ela não exista. A preparação explícita acima deixa as três collections disponíveis antes de iniciar a aplicação.

Para conferir uma collection, execute `GET /collections/faq_chunks` e repita com os outros nomes. Verifique `size: 768` e `distance: Cosine` em `config.params.vectors`. Em collections existentes, confira a configuração sem apagá-las.

Referências: [collections](https://qdrant.tech/documentation/manage-data/collections/) e [índices de payload](https://qdrant.tech/documentation/concepts/indexing/).

## Preenchimento dos dados

O modelo de embeddings configurado em `app/tools/vectorstore.py` é `gemini-embedding-2-preview`, com saída de 768 dimensões. Os vetores usados na indexação e na consulta precisam ser compatíveis.

O comando `python -m app.ingest_faq` lê `data/faq.pdf` e substitui os pontos existentes em `faq_chunks`. Ele gera embeddings por API e pode gerar custos.

`memoria_resumos` recebe pontos quando conversas com mensagens são encerradas. `perfil_restricoes` recebe pontos quando o perfil é salvo; as restrições anteriores daquele usuário são substituídas. Não é necessário importar dados pessoais para inicializar essas collections.
