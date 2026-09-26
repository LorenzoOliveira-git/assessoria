"""Persistencia do perfil financeiro no MongoDB e no Qdrant."""

import uuid
from datetime import datetime, timezone

from pymongo import MongoClient
from qdrant_client import models

from app.config import MONGODB_URI
from app.schemas import PerfilRequest
from app.tools.vectorstore import (
    COLLECTION_PERFIL_RESTRICOES,
    garantir_collection_perfil,
    gerar_embedding,
    gerar_embeddings_batch,
    qdrant,
)


_mongo = MongoClient(MONGODB_URI, connect=False)
_db = _mongo["assessor"]
col_perfis = _db["perfis"]


def _agora() -> datetime:
    return datetime.now(timezone.utc)


def _garantir_indice_mongo() -> None:
    # Um indice unico transforma user_id na identidade do cadastro e impede
    # que dois perfis sejam criados para o mesmo usuario.
    col_perfis.create_index("user_id", unique=True)


def _filtro_usuario_qdrant(user_id: str) -> models.Filter:
    return models.Filter(
        must=[
            models.FieldCondition(
                key="user_id",
                match=models.MatchValue(value=user_id),
            )
        ]
    )


def _substituir_restricoes(
    user_id: str,
    restricoes: list[str],
    vetores: list[list[float]],
    atualizado_em: datetime,
) -> None:
    # O formulario representa o estado completo. Portanto, qualquer restricao
    # anterior deste usuario deixa de existir antes da nova lista ser gravada.
    qdrant.delete(
        collection_name=COLLECTION_PERFIL_RESTRICOES,
        points_selector=models.FilterSelector(
            filter=_filtro_usuario_qdrant(user_id)
        ),
        wait=True,
    )

    pontos = [
        models.PointStruct(
            id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"perfil:{user_id}:{indice}")),
            vector=vetor,
            payload={
                "user_id": user_id,
                "restricao": restricao,
                "posicao": indice,
                "atualizado_em": atualizado_em.isoformat(),
            },
        )
        for indice, (restricao, vetor) in enumerate(zip(restricoes, vetores))
    ]

    qdrant.upsert(
        collection_name=COLLECTION_PERFIL_RESTRICOES,
        points=pontos,
        wait=True,
    )


def salvar_perfil(perfil: PerfilRequest) -> dict:
    """Atualiza o cadastro estruturado e substitui suas restricoes semanticas."""
    _garantir_indice_mongo()
    garantir_collection_perfil()

    # Embeddings sao gerados antes das escritas para que uma falha do provedor
    # nao deixe apenas metade do novo perfil persistida.
    vetores = gerar_embeddings_batch(perfil.restricoes)
    if len(vetores) != len(perfil.restricoes):
        raise RuntimeError("O provedor nao gerou um vetor para cada restricao.")
    atualizado_em = _agora()

    dados_estruturados = {
        "user_id": perfil.user_id,
        "renda_mensal": perfil.renda_mensal,
        "gasto_fixo_mensal": perfil.gasto_fixo_mensal,
        "horizonte_meses": perfil.horizonte_meses,
        "perfil_investidor": perfil.perfil_investidor,
        "atualizado_em": atualizado_em,
    }

    col_perfis.update_one(
        {"user_id": perfil.user_id},
        {"$set": dados_estruturados},
        upsert=True,
    )
    _substituir_restricoes(
        user_id=perfil.user_id,
        restricoes=perfil.restricoes,
        vetores=vetores,
        atualizado_em=atualizado_em,
    )

    return perfil.model_dump()


def buscar_perfil_estruturado(user_id: str) -> dict | None:
    """Consulta interna usada pela futura tool do especialista financeiro."""
    return col_perfis.find_one({"user_id": user_id}, {"_id": 0})


def buscar_restricoes_relevantes(user_id: str, pergunta: str) -> list[str]:
    """Busca semanticamente as restricoes do usuario relacionadas a pergunta."""
    garantir_collection_perfil()
    resultados = qdrant.query_points(
        collection_name=COLLECTION_PERFIL_RESTRICOES,
        query=gerar_embedding(pergunta),
        query_filter=_filtro_usuario_qdrant(user_id),
        limit=2,
    )
    return [
        ponto.payload["restricao"]
        for ponto in resultados.points
        if ponto.payload and ponto.payload.get("restricao")
    ]
