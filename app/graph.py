import json
import operator
from typing import Annotated
from langgraph.graph import StateGraph, MessagesState, END
import signal
from app.agents import router_app, financeiro_app, agenda_app, orquestrador_app, faq_app
from langgraph.checkpoint.memory import MemorySaver
# from event_tools import TOOLS_AGENDA
from app.memory import salvar_mensagem
from app.observabilidade import abrir_turno, fechar_turno, status_do_estado
from app.juiz import coleta, julgar_jev, _publicar, FRASE_SEGURA
from app.escritas import atual, contexto, serializar

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
    status_escrita: str


_TOOLS_ESCRITA_EVIDENCIA = {"add_transaction", "update_transaction", "add_event", "add_google_event"}


def _log_evidencia(etapa: str, dados: dict) -> None:
    """Mostra um recorte legível do turno sem alterar o estado do grafo."""
    try:
        print(f"\n{'=' * 72}\n{etapa}\n{json.dumps(dados, ensure_ascii=False, indent=2, default=str)}\n{'=' * 72}", flush=True)
    except (OSError, UnicodeError):
        pass  # Uma falha no terminal não deve interromper o atendimento.


def _escritas_do_turno(mensagens: list) -> list[dict]:
    """Reúne chamadas e retornos das quatro tools após a última fala do usuário."""
    inicio = max((i for i, msg in enumerate(mensagens) if getattr(msg, "type", "") == "human"), default=-1)
    escritas = []
    nomes_por_id = {}
    for msg in mensagens[inicio + 1:]:
        if getattr(msg, "type", "") == "ai":
            for chamada in getattr(msg, "tool_calls", None) or []:
                if chamada.get("name") in _TOOLS_ESCRITA_EVIDENCIA:
                    nomes_por_id[chamada.get("id")] = chamada["name"]
                    escritas.append({"tool": chamada["name"], "chamada": chamada.get("args", {})})
        elif getattr(msg, "type", "") == "tool":
            nome = getattr(msg, "name", "") or nomes_por_id.get(getattr(msg, "tool_call_id", None))
            if nome in _TOOLS_ESCRITA_EVIDENCIA:
                escritas.append({"tool": nome, "retorno": msg.content, "erro": getattr(msg, "status", "") == "error"})
    return escritas


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

def no_juiz(estado: dict) -> dict:
    pergunta, resposta, evidencia = coleta(estado)
    turno = atual()
    tentativas = _escritas_do_turno(estado["messages"])
    if turno and (any(t.get("erro") for t in tentativas) or (tentativas and not turno.tem_escritas)):
        turno.erros.append("Não foi possível preparar a escrita solicitada.")
    if turno and turno.tem_escritas:
        evidencia += "\n\nINTENÇÕES PENDENTES (nenhum efeito executado):\n" + turno.manifesto()
    if not resposta:
        _log_evidencia("[juiz]", {"veredito": "sem_resposta", "resposta_recebida": resposta})
        if turno and turno.tem_escritas:
            texto = turno.concluir(False)
            turno.status = "erro"
            return {"messages": [{"role": "assistant", "content": texto}], "agentes_chamados": ["juiz:sem_resposta"], "status_escrita": turno.status}
        return {"agentes_chamados": ["juiz:sem_resposta"]}
    try:
        resultado = julgar_jev(pergunta, resposta, evidencia)
        if not isinstance(resultado, dict) or not isinstance(resultado.get("agentes_chamados"), list) or not resultado["agentes_chamados"]:
            raise ValueError("Veredito inválido")
    except Exception as exc:
        print(f"[juiz] erro {exc}")
        resultado = _publicar(FRASE_SEGURA, "erro", resposta)
    if turno and turno.tem_escritas:
        rotulo = resultado["agentes_chamados"][0]
        texto = turno.concluir(resultado.get("juiz_aprovado") is True)
        if rotulo.startswith(("juiz:erro", "juiz:sem_chave")):
            turno.status = "erro"
        resultado["messages"] = [{"role": "assistant", "content": texto}]
        resultado["status_escrita"] = turno.status
    _log_evidencia("[juiz]", {
        "veredito": resultado["agentes_chamados"][0],
        "pergunta_avaliada": pergunta,
        "evidencia_recebida": evidencia,
        "resposta_recebida": resposta,
        "resposta_publicada": resultado.get("messages", [{}])[-1].get("content", resposta),
    })
    return resultado

# ==============================================================================
# NÓ ORQUESTRADOR — wrapper para capturar agentes_chamados via rota
# ==============================================================================

def no_orquestrador(estado: Estado, config: RunnableConfig) -> dict:
    # Pega a última resposta do especialista (última AIMessage com conteúdo)
    ultima_especialista = ""
    for mensagem in reversed(estado["messages"]):
        if mensagem.type == "ai" and mensagem.content:
            ultima_especialista = mensagem.content
            break
    # config segue o mesmo motivo do roteador: sem ele, o modelo deste nó
    # não herda o metadata do grafo (e o registro de observabilidade perde o nó).
    saida = orquestrador_app.invoke({
        "messages": [{"role": "human", "content": ultima_especialista}]
    }, config=config)

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
grafo.add_node("juiz", no_juiz)
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
grafo.add_edge("guardrail_saida","juiz")
grafo.add_edge("faq",          END)

memory = MemorySaver()
fluxo_agentes = grafo.compile(checkpointer=memory)

# ==============================================================================
# FLUXO PRINCIPAL
# ==============================================================================
@serializar
def executar_fluxo_assessor(
    pergunta_usuario: str, session_id: str, user_id: str = "usuario_teste"
) -> str:
    pergunta_usuario_anonimizado, _ = anonimizar_entrada(pergunta_usuario)
    estado_inicial = {
        "messages":         [{"role": "human", "content": pergunta_usuario}],
        "agentes_chamados": [],
        "rota":             "",
        "mapa_pii":         {},
        "session_id":       session_id,
        "status_escrita":   "",

    }

    _log_evidencia("[estado inicial]", {
        "session_id": session_id,
        "user_id": user_id,
        "estado_do_grafo": estado_inicial,
    })



    # O registro abre antes do invoke e fecha no finally, inclusive quando
    # o grafo levanta. A rota /monitor só lê o que ficou anotado.
    turno_id = abrir_turno()
    status = "erro"
    rota = ""
    try:
        with contexto(turno_id, pergunta_usuario_anonimizado) as turno:
            try:
                estado_final = fluxo_agentes.invoke(
                    estado_inicial,
                    config={"configurable": {"thread_id": session_id, "user_id": user_id}},
                )
            except Exception:
                if not turno.tem_escritas:
                    raise
                turno.status = "erro"
                # Se já houve commit, concluir devolve o recibo cacheado.
                return turno.concluir(False)

        resposta = estado_final["messages"][-1].text

        _log_evidencia("[estado final]", {
            "session_id": session_id,
            "rota": estado_final.get("rota"),
            "agentes_chamados": estado_final.get("agentes_chamados"),
            "escritas_do_turno": _escritas_do_turno(estado_final["messages"]),
            "resposta_final_do_grafo": resposta,
        })

        # Salva no MongoDB após cada interação
        salvar_mensagem(session_id, "human",     pergunta_usuario_anonimizado, user_id=user_id)
        salvar_mensagem(session_id, "assistant", resposta, user_id=user_id)

        status = estado_final.get("status_escrita") or status_do_estado(estado_final)
        rota = estado_final.get("rota") or ""
        return resposta
    finally:
        fechar_turno(turno_id, session_id=session_id, rota=rota, status=status)

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
