# AssessorIA

Assistente financeiro e de compromissos baseado em um sistema multiagentes, com API em FastAPI, orquestração em LangGraph e interface web em HTML, CSS e JavaScript.

O projeto é destinado, no estado atual, à execução local e individual. A pasta `dados/` reúne os scripts do PostgreSQL, a modelagem do MongoDB e as instruções de criação das collections do Qdrant.

## Funcionalidades

- Conversa com roteamento entre especialistas financeiro, de agenda e de FAQ.
- Registro, consulta e atualização de transações financeiras no PostgreSQL.
- Cadastro de perfil financeiro e consulta de restrições para personalizar respostas.
- Histórico de mensagens no MongoDB e recuperação semântica de resumos no Qdrant.
- Consulta ao FAQ a partir de um PDF previamente indexado.
- Encerramento da conversa pelo botão de nova sessão, com geração de resumo.

O especialista de agenda ainda não possui ferramentas conectadas para criar, consultar ou alterar compromissos. Essa funcionalidade está em desenvolvimento.

## Como funciona

A interface envia mensagens à API. O roteador identifica o assunto, e o grafo encaminha a solicitação aos agentes responsáveis. Os agentes utilizam ferramentas para acessar dados financeiros, perfil, memória e FAQ.

- **FastAPI:** rotas HTTP e disponibilização do frontend.
- **LangChain e LangGraph:** agentes, ferramentas e fluxo de conversa.
- **Google Gemini e Groq:** modelos de linguagem; o Gemini também gera embeddings.
- **PostgreSQL:** transações, categorias, tipos de transação e estrutura de eventos.
- **MongoDB:** mensagens, sessões e dados estruturados do perfil.
- **Qdrant:** busca vetorial de FAQ, resumos e restrições do perfil.

As chamadas aos modelos e embeddings dependem de serviços externos e podem gerar custos. Conteúdos processados pelos modelos são enviados aos respectivos provedores.

## Estrutura

```text
app/                       API, agentes, prompts, memória e ferramentas
frontend/                  Interface web e formulário de perfil
data/faq.pdf               Documento utilizado pelo FAQ
dados/
  relacional/              Scripts de estrutura e dados iniciais do PostgreSQL
  nao_relacional/          Modelagem do MongoDB extraída do código
  vetorial/                Documentação das collections do Qdrant
.env.example               Modelo das variáveis de ambiente
.gitignore                 Exclusões do versionamento
requirements.txt           Dependências Python
```

`data/` contém o PDF utilizado pela aplicação. `dados/` reúne a documentação dos bancos; uma pasta não substitui a outra.

## Pré-requisitos

- Python e pip. Versão de referência do ambiente de desenvolvimento: **3.14.2**.
- Acesso às APIs Google Gemini e Groq, com as respectivas chaves.
- PostgreSQL **18 ou superior** para os scripts fornecidos, MongoDB e Qdrant acessíveis a partir da máquina local.
- Tabelas e collections necessárias preparadas conforme a documentação dos bancos.

Executar a API localmente não elimina a necessidade de configurar esses serviços. Os bancos podem estar em outra máquina ou em serviços gerenciados.

## Instalação local

Baixe ou clone este repositório e abra um terminal na pasta que contém `requirements.txt`.

### 1. Crie um ambiente virtual e instale as dependências

No Windows (PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

No Linux ou macOS:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

Os comandos utilizam diretamente o Python do ambiente virtual, sem exigir ativação no terminal.

### 2. Configure o ambiente

No Windows:

```powershell
Copy-Item .env.example .env
```

No Linux ou macOS:

```bash
cp .env.example .env
```

Se já tiver um `.env`, preserve suas configurações em vez de sobrescrevê-lo. Preencha as credenciais e conexões próprias no arquivo copiado. As variáveis efetivamente utilizadas são:

- `GEMINI_API_KEY`: acesso ao Gemini e aos embeddings.
- `GROQ_API_KEY`: acesso aos modelos Groq.
- `DATABASE_URL`: conexão PostgreSQL.
- `MONGODB_URI`: conexão MongoDB.
- `QDRANT_API_KEY`: chave de acesso ao Qdrant.
- `QDRANT_CLUSTER_ENDPOINT`: endereço do cluster Qdrant.

O `.env.example` também documenta `DEBUG`, `API_PREFIX` e `ALLOW_ORIGINS`, presentes na configuração original, mas **não utilizadas pelo código atual**. Alterá-las não modifica a depuração, o prefixo das rotas ou o CORS.

### 3. Prepare os bancos

Consulte a documentação correspondente:

- [PostgreSQL](dados/relacional/README.md): execute `01_estrutura.sql` e depois `02_dados_iniciais.sql` em um banco novo.
- [MongoDB](dados/nao_relacional/README.md): configure a conexão e as permissões no banco `assessor`; as coleções e índices são gerenciados pelo código.
- [Qdrant](dados/vetorial/README.md): crie `faq_chunks`, `memoria_resumos` e `perfil_restricoes` com vetores padrão de 768 dimensões e distância Cosine, além dos índices de usuário descritos no guia.

Conclua essa preparação antes de iniciar a API. O MongoDB precisa estar acessível desde a inicialização, quando o código cria índices das sessões. Os scripts SQL incluem dados de referência compatíveis com o código, sem transações ou eventos pessoais.

### 4. Indexe o FAQ

Depois de preparar `faq_chunks` no Qdrant e conferir o arquivo `data/faq.pdf`, execute:

```powershell
# Windows
.\.venv\Scripts\python.exe -m app.ingest_faq
```

```bash
# Linux / macOS
.venv/bin/python -m app.ingest_faq
```

Execute na primeira preparação do FAQ ou quando o PDF mudar. **O comando apaga os pontos existentes em `faq_chunks` antes de inserir os novos**, utiliza a conexão do `.env` e faz chamadas à API de embeddings.

### 5. Inicie a aplicação

No Windows:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

No Linux ou macOS:

```bash
.venv/bin/python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Acesse:

- Interface: <http://localhost:8000/>
- Perfil: <http://localhost:8000/perfil_front/perfil.html>
- Documentação interativa: <http://localhost:8000/docs>
- Verificação de configuração: <http://localhost:8000/health>

O frontend é servido pela própria API e não exige uma etapa de build. O chat utiliza `http://localhost:8000` fixo no JavaScript; mantenha essa porta para seguir estas instruções sem alterar o código.

## Exemplos de uso

Com os bancos configurados, experimente mensagens com dados fictícios:

- “Gastei 50 reais no mercado hoje.”
- “Quanto gastei este mês?”
- “Quais foram as últimas transações?”

Na tela de perfil, cadastre renda, gastos fixos, horizonte, perfil de investidor e restrições. O formulário atual utiliza o identificador `usuario_teste`, também adotado como padrão pelo chat.

Para testar `POST /chat` pela documentação interativa:

```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "usuario_teste",
  "pergunta": "Quanto gastei este mês?"
}
```

Use um identificador de sessão diferente para uma nova conversa. O botão de nova sessão da interface solicita o encerramento da conversa anterior para gerar seu resumo.

## Limitações atuais

- Não há autenticação nas rotas. Os identificadores enviados pelo cliente não comprovam a identidade do usuário.
- As operações financeiras atuais não isolam transações por usuário; o projeto deve ser usado como protótipo local e individual.
- O estado de execução do grafo fica na memória do processo e é perdido ao reiniciar a API; isso é separado do histórico salvo no MongoDB.
- A agenda ainda não gerencia compromissos por ferramentas.
- `/health` verifica variáveis e a existência do PDF; não testa a conectividade com todos os serviços.
- Não há suíte automatizada de testes incluída no projeto.

## Problemas comuns

- **Variável ausente:** confira se o `.env` está na raiz e se as seis variáveis utilizadas foram preenchidas.
- **Falha ao iniciar a API:** verifique as credenciais dos provedores e o acesso ao MongoDB; há inicializações de clientes e índices durante os imports.
- **Tabela ou collection inexistente:** confira a preparação do PostgreSQL e do Qdrant. Instalar as dependências não cria toda a estrutura.
- **PDF não encontrado:** confirme a presença de `data/faq.pdf`.
- **Frontend sem conexão:** confirme que a API está acessível em `http://localhost:8000`.
- **Falha em modelos ou embeddings:** confira acesso ao modelo, credenciais e limites da conta do provedor.

## Arquivos locais e versionamento

O `.gitignore` exclui credenciais locais, ambientes virtuais, caches, logs e formatos comuns de backup. Mantenha o `.env.example` versionado com valores fictícios e não inclua dados pessoais em exemplos, PDFs ou dumps.

As regras do `.gitignore` não removem arquivos que já tenham sido rastreados pelo Git. Antes de publicar, confira os arquivos incluídos no commit e o histórico existente.
