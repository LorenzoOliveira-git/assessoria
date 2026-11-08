# Integracao continua

O workflow `workflows/ci.yml` adiciona somente integracoes e testes. Nenhum
arquivo existente da aplicacao ou `requirements.txt` precisa ser alterado.

## Escopo para validacao

1. Executar no GitHub Actions em pushes recebidos na `main` e em PRs destinados
   a `main` (abertura, novos commits, reabertura e marcacao como pronto).
2. Fazer checkout com `actions/checkout` e preparar Python 3.14 em Windows.
   O runner Windows permite instalar `pywin32`, ja exigido pelo projeto.
3. Instalar integralmente `requirements.txt`, adicionar `tzdata` para o fuso
   `America/Sao_Paulo` no Windows e verificar a consistencia com `pip check`.
4. Configurar variaveis ficticias e iniciar um MongoDB local descartavel.
   A aplicacao cria indices no MongoDB durante o import, antes de servir HTTP.
5. Iniciar a aplicacao real com Uvicorn e consultar `/health` antes dos testes.
   Exigir HTTP 200, `status: ok` e `problemas_de_configuracao: []`, com prazo
   de 60 segundos. Falha nessa etapa impede a execucao dos testes.
6. Executar exatamente cinco metodos de teste com `unittest` (biblioteca padrao).
   Ha subcasos de perfil invalido dentro de um mesmo metodo.
7. Encerrar os processos temporarios. Uma falha gera um check vermelho no PR.
   Esta etapa nao inclui deploy.

## Cinco cenarios de negocio

- Perfil valido: normalizacao do usuario e das restricoes.
- Perfil invalido: rejeicao de gastos iguais/superiores a renda e outros campos invalidos.
- Transacao aprovada: nenhuma escrita antecipada, nenhuma duplicacao e um unico commit.
- Transacao reprovada pelo juiz: nenhuma escrita ou conexao com o banco.
- Valor divergente da mensagem original: bloqueio mesmo com aprovacao posterior.

Os testes exercitam as regras existentes de `app.schemas` e `app.escritas`.
Somente a conexao SQL e o efeito da escrita sao simulados; nao ha chamadas a
LLMs, producao ou servicos pagos. Execute localmente, a partir da raiz:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v
```

## Limites da verificacao de saude

O `/health` atual verifica a presenca das variaveis e de `data/faq.pdf`.
Ele retorna HTTP 200 mesmo quando `status` e `atencao`, por isso o CI tambem
valida o JSON. Ele nao verifica autenticidade de chaves nem conectividade
com PostgreSQL, Qdrant, Gemini ou Groq. Esses servicos nao sao provisionados
nessa etapa e usam apenas configuracoes ficticias. O cliente Qdrant pode
emitir um aviso de conexao na inicializacao por estar sem servidor local.
O resultado nao comprova o funcionamento completo dos provedores/agentes.

## Executar antes de integrar na main

O evento `push` do GitHub Actions ocorre **depois** que o GitHub recebe o push;
um workflow remoto nao executa antes do comando `git push` local.
Para exigir aprovacao antes da integracao, configure nas regras da `main`:

1. Exigir pull request e impedir bypass/push direto.
2. Exigir o status check `Health e testes unitarios`.
3. Exigir a branch atualizada antes do merge, conforme o fluxo da equipe.

A configuracao dessas regras e feita no repositorio GitHub; o YAML sozinho
nao protege a branch. O workflow pode continuar verificando pushes na `main`
apos merges. Um hook `pre-push` local seria uma etapa adicional, passivel de
ser ignorada, e nao substitui a protecao remota.

Referencias: [eventos do GitHub Actions](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows),
[status checks obrigatorios](https://docs.github.com/en/pull-requests/reference/status-checks).

## Beneficios do CI em dez linhas

1. Detecta erros automaticamente a cada alteracao integrada ao fluxo.
2. Identifica regressoes antes de disponibilizar uma nova versao.
3. Verifica regras de negocio de maneira repetivel.
4. Padroniza o ambiente de instalacao e validacao.
5. Revela dependencias ausentes ou incompativeis.
6. Confirma a inicializacao da API e sua configuracao basica.
7. Fornece retorno rapido para corrigir falhas menores.
8. Registra os resultados por commit e facilita o diagnostico.
9. Com protecao de branch, impede merges com verificacoes reprovadas.
10. Reduz o risco de indisponibilidade, sem garantir disponibilidade de 100%.
