from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from typing import Literal


class ChatRequest(BaseModel):
    """O que o navegador envia no POST /chat."""

    session_id: str = Field(
        ...,
        description="Identifica a conversa (UUID gerado pelo front a cada sessão).",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )
    user_id: str = Field(
        default="usuario_teste",
        description="Identifica o usuário de forma estável entre sessões. "
                    "É o que permite a memória de longo prazo funcionar.",
        examples=["usuario_teste"],
    )
    pergunta: str = Field(
        ...,
        min_length=1,
        description="A mensagem do usuário — o que antes vinha do input().",
        examples=["gastei 50 reais no mercado hoje"],
    )


class ChatResponse(BaseModel):
    """O que a API devolve no POST /chat."""
    resposta:         str = Field(...,examples=["resposta"])
    # agentes_chamados: list[str] = Field(default_factory=list)


class SessionResponse(BaseModel):
    """Ainda não é usado — é do Passo 6 da Etapa 3."""
    session_id: str
    resumo:     str | None = None

class PerfilRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: str = Field(..., min_length=1)
    renda_mensal: float = Field(..., gt=0, allow_inf_nan=False)
    gasto_fixo_mensal: float = Field(..., ge=0, allow_inf_nan=False)
    horizonte_meses: int = Field(..., strict=True, ge=1, le=120)
    perfil_investidor: Literal["conservador", "moderado", "arrojado"]
    restricoes: list[str] = Field(..., min_length=1, max_length=5)

    @field_validator("user_id")
    @classmethod
    def validar_user_id(cls, valor: str) -> str:
        valor = valor.strip()

        if not valor:
            raise ValueError("user_id não pode estar vazio")

        return valor

    @field_validator("restricoes")
    @classmethod
    def validar_restricoes(cls, restricoes: list[str]) -> list[str]:
        restricoes_normalizadas = [restricao.strip() for restricao in restricoes]

        if any(not restricao for restricao in restricoes_normalizadas):
            raise ValueError("cada restrição deve ser uma frase não vazia")

        return restricoes_normalizadas

    @model_validator(mode="after")
    def validar_gasto_fixo(self) -> "PerfilRequest":
        if self.gasto_fixo_mensal >= self.renda_mensal:
            raise ValueError(
                "gasto_fixo_mensal deve ser menor que renda_mensal"
            )

        return self
