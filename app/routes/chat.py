from fastapi import APIRouter
from app.schemas import ChatRequest, ChatResponse
from app.llms import llm_rapido
from app.graph import executar_fluxo_assessor
from fastapi import HTTPException

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)         # ← response_model
def conversar(requisicao: ChatRequest):    # ← dict vira ChatRequest
    try:
        chat_response = executar_fluxo_assessor(
            user_id=requisicao.user_id
            ,pergunta_usuario=requisicao.pergunta
            ,session_id=requisicao.session_id
        )
        return ChatResponse(
            resposta=chat_response
        )
    except HTTPException as e:
        print(e)
