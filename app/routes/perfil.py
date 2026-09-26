"""Rota de escrita do perfil financeiro."""

import logging

from fastapi import APIRouter, HTTPException, status

from app.perfil import salvar_perfil
from app.schemas import PerfilRequest


logger = logging.getLogger(__name__)
router = APIRouter(tags=["perfil"])


@router.post("/perfil", response_model=PerfilRequest, status_code=status.HTTP_200_OK)
def enviar_perfil(perfil: PerfilRequest) -> PerfilRequest:
    """Cria ou atualiza o unico perfil associado ao user_id informado."""
    try:
        salvar_perfil(perfil)
    except Exception as exc:
        logger.exception("Falha ao salvar o perfil do usuario %s", perfil.user_id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Nao foi possivel salvar o perfil neste momento.",
        ) from exc

    return perfil
