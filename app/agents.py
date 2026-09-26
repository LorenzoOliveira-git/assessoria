from app.prompts import (
    ROUTER_PROMPT_COMPLETO,
    FINANCEIRO_PROMPT_COMPLETO,
    AGENDA_PROMPT_COMPLETO,
    ORQUESTRADOR_PROMPT_COMPLETO,
    FAQ_PROMPT_COMPLETO,
)
from app.llms import llm_especialista, llm_rapido
from langchain.agents import create_agent
from app.tools.financeiro import TOOLS
# from event_tools import TOOLS_AGENDA
from app.tools.faq import faq_retriever
from app.tools.memoria import TOOLS_MEMORIA
from app.tools.perfil import TOOLS_PERFIL
from typing import Literal
from pydantic import BaseModel, Field


class RouterDecision(BaseModel):
    """Contrato estruturado do classificador de rotas."""

    route: Literal["financeiro", "agenda", "faq", "fim"] = Field(
        description="Destino da mensagem. Use 'fim' quando o roteador responder diretamente."
    )
    pergunta_original: str = Field(
        default="",
        description="Mensagem original completa quando houver encaminhamento.",
    )
    resposta: str = Field(
        default="",
        description="Resposta direta somente para saudação, ambiguidade ou fora de escopo.",
    )

# O roteador é apenas um classificador. Usar create_agent aqui habilitava o
# protocolo de tool calling e fazia o gpt-oss interpretar ROUTE como uma tool.
# JSON Schema usa a saída estruturada nativa do Groq, sem qualquer tool exposta.
router_app       = llm_rapido.with_structured_output(RouterDecision, method="json_schema")
financeiro_app   = create_agent(model=llm_especialista, tools=TOOLS+TOOLS_MEMORIA+TOOLS_PERFIL, system_prompt=FINANCEIRO_PROMPT_COMPLETO)
agenda_app       = create_agent(model=llm_especialista, system_prompt=AGENDA_PROMPT_COMPLETO, tools=TOOLS_MEMORIA)
orquestrador_app = create_agent(model=llm_rapido,       system_prompt=ORQUESTRADOR_PROMPT_COMPLETO)
faq_app          = create_agent(model=llm_rapido,       tools=[faq_retriever], system_prompt=FAQ_PROMPT_COMPLETO)
