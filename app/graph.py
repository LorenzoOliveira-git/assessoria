import operator
from typing import Annotated
from langgraph.graph import StateGraph, MessagesState, END
import signal
from app.agents import router_app, financeiro_app, agenda_app, orquestrador_app, faq_app
from langgraph.checkpoint.memory import MemorySaver
# from event_tools import TOOLS_AGENDA
from app.memory import salvar_mensagem

from app.guardrail import guardrail_entrada,guardrail_saida,anonimizar_entrada

from langchain_core.messages import RemoveMessage

from langchain_core.runnables import RunnableConfig
from app.prompts import ROUTER_PROMPT_COMPLETO

# Tratativa de erros para Kill no terminal
def handler_sinais(signum, frame):
    raise SystemExit(0)

signal.signal(signal.SIGTERM, handler_sinais)
signal.signal(signal.SIGINT, handler_sinais)
# ==============================================================================
# ESTADO
# MessagesState já traz: messages: Annotated[list[AnyMessage], add_messages]
# O checkpointer propaga automaticamente para os subgrafos adicionados via add_node
# ==============================================================================
class Estado(MessagesState):
    agentes_chamados: Annotated[list[str], operator.add]
    rota:             str   # decisão do roteador — não polui o histórico
    mapa_pii: dict


# ==============================================================================
# NÓ ROTEADOR — necessário apenas para extrair a rota sem poluir messages
# ==============================================================================
def no_roteador(estado: Estado, config: RunnableConfig) -> dict:
    mensagens = list(estado["messages"])
    decisao = router_app.invoke(
        [{"role": "system", "content": ROUTER_PROMPT_COMPLETO}, *mensagens],
        config=config,
    )

    if decisao.route == "fim":
        return {
            "agentes_chamados": ["roteador"],
            "rota":             "fim",
            "messages":         [{
                "role": "assistant",
                "content": decisao.resposta or "Posso ajudar com finanças ou agenda. O que você precisa?",
            }],
        }

    return {
        "agentes_chamados": ["roteador", decisao.route],
        "rota":             decisao.route,
        # Histórico limpo: o especialista vai ler só a conversa real
    }
    

# ==============================================================================
# NÓ ORQUESTRADOR — wrapper para capturar agentes_chamados via rota
# ==============================================================================

def no_orquestrador(estado: Estado) -> dict:
    # Pega a última resposta do especialista (última AIMessage com conteúdo)
    ultima_especialista = ""
    for mensagem in reversed(estado["messages"]):
        if mensagem.type == "ai" and mensagem.content:
            ultima_especialista = mensagem.content
            break
    
    saida = orquestrador_app.invoke({
        "messages": {"role": "human", "content": ultima_especialista}
    })

    return {
        "agentes_chamados": ["orquestrador"],
        "messages":        [{"role": "assistant", "content": saida["messages"][-1].text}]
    }

def no_guardrail_entrada(estado: Estado) ->dict:

    human_message = list(estado["messages"])[-1]

    texto_anonimizado, mapa = anonimizar_entrada(human_message.content)

    resultado = guardrail_entrada(texto_anonimizado)

    if resultado["bloqueado"]:
        return {
            "messages":[{"role":"assistant","content":resultado["mensagem"]}],
            "rota":"fim",
            "mapa_pii":{},
            "agentes_chamados":[f"guardrail_entrada:{resultado['motivo']}"]
        }
    else:
        return {
            "messages":[RemoveMessage(id=human_message.id), {"role":"human","content":texto_anonimizado}],
            "rota":"roteador",
            "mapa_pii":mapa,
            "agentes_chamados":["guardrail_entrada:aprovado"]
        }
    
def no_guardrail_saida(estado: Estado) -> dict:
    ultima = ""
    for msg in reversed(estado["messages"]):
        if msg.type == "ai" and msg.content:
            ultima = msg.content
            break

    resultado = guardrail_saida(ultima,estado.get("mapa_pii",{}))

    return {
        "messages":          [{"role":"assistant","content":resultado["conteudo"]}],
        "agentes_chamados":  ["guardrail_saida"]
    }

# ==============================================================================
# FUNÇÃO DE DECISÃO
# ==============================================================================
def decidir_especialista(estado: Estado) -> str:
    return estado["rota"] if estado["rota"] in ("financeiro","agenda", "faq") else "fim"

def decidir_pos_guardrail_entrada(estado:Estado) -> str:
    return estado["rota"] if estado["rota"] == "roteador" else "fim"
# ==============================================================================
# GRAFO
# ==============================================================================
grafo = StateGraph(Estado)


grafo.add_node("guardrail_entrada",no_guardrail_entrada)
grafo.add_node("roteador",     no_roteador)
grafo.add_node("financeiro",   financeiro_app)   # subgrafo direto — checkpointer propaga
grafo.add_node("agenda",       agenda_app)        # subgrafo direto
grafo.add_node("faq",          faq_app)           # subgrafo direto
grafo.add_node("orquestrador", no_orquestrador)
grafo.add_node("guardrail_saida",no_guardrail_saida)

grafo.set_entry_point("guardrail_entrada")

grafo.add_conditional_edges(
    "roteador",
    decidir_especialista,
    {
        "financeiro": "financeiro",
        "agenda":     "agenda",
        "faq":        "faq",
        "fim":        END,
    },
)

grafo.add_conditional_edges(
    "guardrail_entrada",
    decidir_pos_guardrail_entrada,
    {
        "roteador":"roteador",
        "fim":END
    }
)

grafo.add_edge("financeiro",   "orquestrador")
grafo.add_edge("agenda",       "orquestrador")
grafo.add_edge("orquestrador", "guardrail_saida")
grafo.add_edge("guardrail_saida",END)
grafo.add_edge("faq",          END)

memory = MemorySaver()
fluxo_agentes = grafo.compile(checkpointer=memory)

# ==============================================================================
# FLUXO PRINCIPAL
# ==============================================================================
def executar_fluxo_assessor(user_id: str, pergunta_usuario: str, session_id: str) -> str:
    texto_anonimizado, mapa = anonimizar_entrada(pergunta_usuario)

    estado_inicial = {
            "messages":         [{"role": "human", "content": pergunta_usuario}],
            "agentes_chamados": [],
            "rota":             "",
        } 

    estado_final = fluxo_agentes.invoke(
            estado_inicial,
            config={"configurable": {"thread_id": session_id, "user_id":user_id}},
        )       
    
    resposta = estado_final["messages"][-1].text

    salvar_mensagem(user_id=user_id,session_id=session_id,role="human",content=texto_anonimizado)
    salvar_mensagem(user_id=user_id,session_id=session_id,role="assistant",content=resposta)
    
    return resposta

# ==============================================================================
# LOOP
# ============================================================

# try:
#     while True:
#         try:
#             user_input = input("> ")
#             if user_input.lower() in ("sair", "end", "fim", "tchau", "bye"):
#                 # O Usuário pode encerrar a sessão fechando a janela ou algo do tipo, então você deve tratar
#                 # essas ocorrências para quando isso acontencer.
#                 break

#             resposta = executar_fluxo_assessor(
#                 pergunta_usuario=user_input,
#                 session_id=session_id,
#             )
#             print(resposta)

#         except Exception as e:
#             print("Erro ao consumir a API:", e)
#             continue
# except KeyboardInterrupt:
#     print("\nInterrupção do usuário")
# except SystemExit:
#     print("\nSaindo do programa.")
# finally:
#     resumo = encerrar_sessao(session_id)
#     if resumo:
#         print(f"Resumo da sessão: ",resumo)
#     print("Até logo!")
