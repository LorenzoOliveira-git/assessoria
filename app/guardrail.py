"""
Verificações de segurança e compliance do assessor financeiro.

ENTRADA  → anonimizar → checar injeção → checar dados internos → classificar (LLM)
SAÍDA    → redigir PII → desanonimizar → revisar compliance (LLM)
"""
import re
import uuid
from app.llms import llm_rapido

# ==============================================================================
# PII — padrões usados tanto na entrada quanto na saída
# ==============================================================================
PII = [
    ("CPF",      r"\d{3}\.?\d{3}\.?\d{3}-?\d{2}"),
    ("CNPJ",     r"\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}"),
    ("TELEFONE", r"\(?\d{2}\)?\s?\d{4,5}-?\d{4}"),
    ("EMAIL",    r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"),
    ("CONTA",    r"\d{4,6}-\d{1}"),
    ("CARTAO",   r"\d{4}\s?\d{4}\s?\d{4}\s?\d{4}"),
]

# ==============================================================================
# HELPERS
# ==============================================================================
def _bloquear(motivo, mensagem):
    return {"bloqueado": True, "motivo": motivo, "mensagem": mensagem}

def _aprovado():
    return {"bloqueado": False, "motivo": "aprovado", "mensagem": ""}

def _saida_ok(conteudo):
    return {"bloqueado": False, "motivo": "saida_revisada", "conteudo": conteudo}

# ==============================================================================
# ANONIMIZAÇÃO
# ==============================================================================
def anonimizar_entrada(texto):
    mapa = {}

# Tem por objetivo varrer uma tupla que contêm o tipo do PII e uma regex para capturar esses valores na pergunta.
# Então, o método varre todos os padrões setados lá na variável PII e procura no texto se há a ocorrência de cada um desses padrões no texto, caso encontre ou não, o método vai percorrer a lista com os valores no matches (lista com os valores que chegaram da regex) e anonimizar todos eles. Além disso, é necessário colocar a chave - PII anonimizado e o valor sendo o texto original para recuperar a informação posteriormente.
    for tipo, padrao in PII:
        matches = re.findall(padrao, texto)
        for valor in matches:
            token = f"[PII_{tipo}_{uuid.uuid4().hex[:6]}]"
            mapa[token] = valor
            texto = texto.replace(valor, token, 1)

    return texto, mapa

def desanonimizar_saida(texto, mapa, restaurar=False):
    """Resolve tokens de PII na saída. Por padrão omite — não repete dado pessoal."""

    # Esse método faz a desanonimização dos dados do texto, passando o que está codificado em PII para o valor padrão. Isso acontece caso o parâmetro restaurar venha como True, como padrão ele vem como False, essa parte eu não entendi direito.
    for token, valor in mapa.items():
        if token in texto:
            substituto = valor if restaurar else f"[{token.split('_')[1]} OMITIDO]"
            texto = texto.replace(token, substituto)
    return texto

# ==============================================================================
# GUARDRAIL DE ENTRADA
# ==============================================================================
_PADROES_INJECAO = [
    r"ignore\s+(as\s+)?instru[çc][oõ]es",
    r"ignore\s+previous\s+instructions",
    r"forget\s+your\s+instructions",
    r"you\s+are\s+now\s+",
    r"act\s+as\s+(if\s+)?",
    r"pretend\s+(you\s+are|to\s+be)",
    r"jailbreak",
    r"dan\s+mode",
    r"modo\s+irrestrito",
    r"system\s*prompt",
    r"<\s*system\s*>",
    r"\[INST\]",
    r"###\s*instruction",
    r"override\s+(your\s+)?instructions",
    r"desconsider[ea]\s+(suas\s+)?instru[çc][oõ]es",
]

_KEYWORDS_DADOS_INTERNOS = [
    "prompt do sistema", "system prompt", "suas instruções", "your instructions",
    "variável de ambiente", "chave de api", "api key", "senha do sistema",
    "token de acesso", "banco de dados interno", "tabela interna",
    "dados de outros clientes", "lista de clientes", "credenciais",
]

# Uma chamada LLM para as 5 categorias semânticas
_PROMPT_CLASSIFICADOR = """\
Você é um classificador de segurança de um sistema de assessoria financeira e agenda.
Classifique a mensagem em UMA categoria. Responda SOMENTE:

CATEGORIA: [categoria]
JUSTIFICATIVA: [uma linha]

Categorias:
APROVADO        - mensagem legítima sobre finanças (informativa), agenda ou operações
PERIGOSO        - instruções que causam dano físico, psicológico ou coletivo
ILICITO         - pedido de auxílio para atividades ilegais ou fraudulentas
POLITICO        - opiniões ou debates políticos, partidos, eleições
INDICACAO_INVEST - recomendação direta de ativo específico para comprar/vender/manter

Mensagem: {mensagem}
"""

_PALAVROES = [
    "puta",
    "puta que pariu",
    "pqp",
    "caralho",
    "cacete",
    "porra",
    "merda",
    "bosta",
    "foda",
    "foder",
    "fudido",
    "fdp",
    "filho da puta",
    "desgraçado",
    "desgraça",
    "arrombado",
    "otário",
    "babaca",
    "idiota",
    "imbecil",
    "retardado",
    "corno",
    "vagabundo",
    "canalha",
    "escroto",
    "pau no cu",
    "cu",
    "buceta",
    "xota",
    "piroca",
    "rola",
    "pau",
    "viado",
    "veado",
    "cuzão",
    "pau no seu cu",
    "vai se foder",
    "vai tomar no cu",
    "vsf",
    "vtnc",
    "tomar no cu",
    "fodase",
    "foda-se",
]

_RESPOSTAS_BLOQUEIO = {
    # "OFENSIVO":         ("conteudo_ofensivo",      "Por favor, mantenha um tom respeitoso para que eu possa te ajudar."),
    "PERIGOSO":         ("pedido_perigoso",         "Não posso ajudar com esse tipo de solicitação."),
    "ILICITO":          ("pedido_ilicito",           "Não posso auxiliar com atividades ilegais ou irregulares."),
    "POLITICO":         ("pergunta_politica",        "Não me envolvo em temas políticos. Posso ajudar com finanças ou sua agenda."),
    "INDICACAO_INVEST": ("indicacao_investimento",   "Por regulação, não forneço indicações diretas de ativos. Posso explicar classes de investimento ou agendar uma reunião com seu assessor."),
}

def guardrail_entrada(mensagem_anonimizada):
    """
    Executa as verificações de entrada em ordem de custo crescente:
    determinístico primeiro, LLM só se necessário.
    Retorna dict com bloqueado, motivo e mensagem.
    """
    # 1. Prompt injection
    for padrao in _PADROES_INJECAO:
        if re.search(padrao, mensagem_anonimizada, re.IGNORECASE):
            return _bloquear("prompt_injection", "Não consigo processar essa solicitação.")

    # 2. Tentativa de acesso a dados internos
    texto_lower = mensagem_anonimizada.lower()
    for kw in _KEYWORDS_DADOS_INTERNOS:
        if kw in texto_lower:
            return _bloquear("acesso_dados_internos", "Não tenho como compartilhar informações internas do sistema.")

    # 3. Classificação semântica via LLM (ofensivo, perigoso, ilícito, político, indicação)
    resposta = llm_rapido.invoke(_PROMPT_CLASSIFICADOR.format(mensagem=mensagem_anonimizada)).content

    categoria = "APROVADO"
    for linha in resposta.splitlines():
        if linha.strip().upper().startswith("CATEGORIA:"):
            categoria = linha.split(":", 1)[1].strip().upper()
            break

    if categoria in _RESPOSTAS_BLOQUEIO:
        motivo, mensagem = _RESPOSTAS_BLOQUEIO[categoria]
        return _bloquear(motivo, mensagem)

    for palavrao in _PALAVROES:
        if palavrao in texto_lower:
            return _bloquear("linguagem_ofensiva","Por favor, mantenha um tom respeitoso para que eu possa te ajudar.")
    return _aprovado()

# ==============================================================================
# GUARDRAIL DE SAÍDA
# ==============================================================================
_PROMPT_COMPLIANCE = """\
Você é um revisor de compliance para assessoria financeira regulada pela CVM e ANBIMA.
Corrija a resposta SOMENTE se ela garantir rentabilidade futura, recomendar ativo específico
sem disclaimer de risco, ou afirmar certeza sobre comportamento futuro do mercado.
Se estiver adequada, repita-a sem alterações.

Responda SOMENTE:
STATUS: APROVADO ou CORRIGIDO
RESPOSTA:
[texto final]

Resposta para revisar:
{resposta}
"""

def guardrail_saida(resposta, mapa_pii, restaurar_pii=False):
    """
    Limpa e revisa a resposta do especialista antes de entregar ao usuário.
    Nunca bloqueia — sempre retorna o texto revisado em 'conteudo'.
    """
    # 1. Remove PII que o modelo tenha gerado
    for tipo, padrao in PII:
        resposta = re.sub(padrao, f"[{tipo} OMITIDO]", resposta)

    # 2. Resolve tokens de PII da entrada
    resposta = desanonimizar_saida(resposta, mapa_pii, restaurar=restaurar_pii)

    # 3. Revisão de compliance financeiro
    # Quais que são os perigos e benefícios de colocar a resposta para ser revisada direto no prompt?
    saida = llm_rapido.invoke(_PROMPT_COMPLIANCE.format(resposta=resposta)).content.strip()
    if "RESPOSTA:" in saida:
        resposta = saida.split("RESPOSTA:", 1)[1].strip() or resposta

    return _saida_ok(resposta)
