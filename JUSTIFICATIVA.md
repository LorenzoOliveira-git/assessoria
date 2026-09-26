# JUSTIFICATIVA

1. **Quais arquivos voce criou ou modificou?** Modificados: `app/schemas.py`, `app/main.py`, `app/memory.py`, `app/agents.py`, `app/prompts.py`, `app/routes/perfil.py`, `app/tools/vectorstore.py` e `requirements.txt` (não estava importando o qdrant-client, pois no código anterior eu apenas importei a lib sem adicionar ela no requirements.txt). Criados: `app/perfil.py`, `app/tools/perfil.py` e `JUSTIFICATIVA.md`.

2. **Por onde o perfil entra, e onde cada parte dele e gravada?** Ele entra exclusivamente pelo `POST /perfil`. Os campos estruturados ficam na collection `perfis` do MongoDB e cada frase de `restricoes` vira um ponto separado na collection `perfil_restricoes` do Qdrant.

3. **Como o texto livre e indexado e consultado, e por que nao e busca por palavra?** Cada restricao recebe seu proprio embedding e ponto no Qdrant, com isso a consulta consegue comparar vetores para recuperar frases semanticamente proximas mesmo quando pergunta e cadastro nao usam as mesmas palavras.

4. **Voce criou uma tool ou duas? Por que?** Foi criada uma tool de leitura chamada `consultar_perfil_financeiro`, pois uma unica ação de aconselhamento precisa receber em conjunto os campos estruturados e as restricoes semanticamente relevantes do mesmo usuario.

5. **O que garante que o perfil de um usuario nao apareceria para outro?** O MongoDB usa consulta e indice unico por `user_id`; no Qdrant, substituicao e futura busca usam filtro obrigatorio no payload `user_id`, que tambem possui indice do tipo `keyword`.

6. **Sua tool consulta o banco diretamente ou faz uma chamada HTTP na propria API? Por que?** A tool consulta MongoDB e Qdrant diretamente pelas funções internas. Fazer a aplicacao chamar sua propria API adicionaria latencia, dependencia de rede e outro ponto de falha sem oferecer beneficio.

7. **Por que optamos por nao criar um agente \"perfil\"?** Perfil não é um novo domínio de conversa, e sim um contexto de apoio para o especialista financeiro. Um agente adicional aumentaria roteamento e complexidade sem acrescentar uma responsabilidade independente.

8. **Qual a vantagem do chat nao alterar o cadastro?** Separar aconselhamento de cadastro reduz alteracoes acidentais ou induzidas pelo modelo e mantem a tela Perfil como fonte explicita e auditavel das preferencias do usuario.
