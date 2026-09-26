"""
Cliente Qdrant e função de embedding — centralizados aqui.

Dois consumidores:
  - memory.py   → salva/busca resumos na collection "memoria_resumos"
  - tools/faq.py → busca chunks do PDF na collection "faq_chunks"

O modelo de embedding é o mesmo para ambos (gemini-embedding-2-preview, 768d),
então instanciamos uma vez só.
"""

from functools import lru_cache

from qdrant_client import QdrantClient, models
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from app.config import QDRANT_CLUSTER_ENDPOINT, QDRANT_API_KEY, GEMINI_API_KEY

qdrant = QdrantClient(url=QDRANT_CLUSTER_ENDPOINT, api_key=QDRANT_API_KEY)

COLLECTION_MEMORIA = "memoria_resumos"
COLLECTION_FAQ     = "faq_chunks"
COLLECTION_PERFIL_RESTRICOES = "perfil_restricoes"
EMBEDDING_DIM      = 768

_embeddings = GoogleGenerativeAIEmbeddings(
    model="gemini-embedding-2-preview",
    google_api_key=GEMINI_API_KEY,
)


def gerar_embedding(texto: str) -> list[float]:
    """Gera um vetor de 768 dimensões para o texto informado."""
    return _embeddings.embed_query(texto, output_dimensionality=EMBEDDING_DIM)


def gerar_embeddings_batch(textos: list[str]) -> list[list[float]]:
    """Gera embeddings para uma lista de textos de uma vez (mais eficiente)."""
    return _embeddings.embed_documents(textos, output_dimensionality=EMBEDDING_DIM)


@lru_cache(maxsize=1)
def garantir_indice_memoria() -> None:
    """Garante o indice de isolamento da memoria quando ela for utilizada."""
    qdrant.create_payload_index(
        collection_name=COLLECTION_MEMORIA,
        field_name="user_id",
        field_schema=models.PayloadSchemaType.KEYWORD,
        wait=True,
    )


@lru_cache(maxsize=1)
def garantir_collection_perfil() -> None:
    """Cria, de forma idempotente, a collection usada pelas restricoes."""
    if not qdrant.collection_exists(collection_name=COLLECTION_PERFIL_RESTRICOES):
        qdrant.create_collection(
            collection_name=COLLECTION_PERFIL_RESTRICOES,
            vectors_config=models.VectorParams(
                size=EMBEDDING_DIM,
                distance=models.Distance.COSINE,
            ),
        )

    # user_id e usado em todas as substituicoes e consultas desta collection.
    qdrant.create_payload_index(
        collection_name=COLLECTION_PERFIL_RESTRICOES,
        field_name="user_id",
        field_schema=models.PayloadSchemaType.KEYWORD,
        wait=True,
    )
