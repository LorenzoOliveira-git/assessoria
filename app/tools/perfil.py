"""Tool somente de leitura do perfil usada pelo especialista financeiro."""

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from app.perfil import buscar_perfil_estruturado, buscar_restricoes_relevantes


@tool
def consultar_perfil_financeiro(pergunta: str, config: RunnableConfig) -> dict:
    """Consulta o perfil para aconselhamento financeiro personalizado.

    Args:
        pergunta: assunto financeiro atual, usado na busca semantica das restricoes.
    """
    configuravel = (config or {}).get("configurable", {})
    user_id = configuravel.get("user_id")

    if not user_id:
        return {
            "status": "usuario_nao_identificado",
            "orientacao": "Nao foi possivel identificar o usuario da requisicao.",
        }

    perfil = buscar_perfil_estruturado(user_id)
    if not perfil:
        return {
            "status": "perfil_nao_cadastrado",
            "orientacao": "Oriente o usuario a cadastrar os dados na tela Perfil.",
        }

    return {
        "status": "ok",
        "perfil": {
            "renda_mensal": perfil["renda_mensal"],
            "gasto_fixo_mensal": perfil["gasto_fixo_mensal"],
            "horizonte_meses": perfil["horizonte_meses"],
            "perfil_investidor": perfil["perfil_investidor"],
        },
        "restricoes_relevantes": buscar_restricoes_relevantes(
            user_id=user_id,
            pergunta=pergunta,
        ),
    }


TOOLS_PERFIL = [consultar_perfil_financeiro]
