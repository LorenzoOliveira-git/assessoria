import sys
from pathlib import Path
from typing import Annotated, Any, Optional

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations
from pydantic import Field

from app.tools.financeiro import (
    add_transaction as _add_transaction,
    saldo_diario as _daily_balance,
    search_transactions as _query_transactions,
    saldo_total as _total_balance,
    update_transaction as _update_transaction,
)

mcp = MCPServer(
    name="assessor-financeiro",
    version="1.0.0",
    instructions="Ferramentas financeiras do Assessor.AI.",
)

LEITURA = ToolAnnotations(readOnlyHint=True)
ESCRITA = ToolAnnotations(readOnlyHint=False, destructiveHint=False)


@mcp.tool(
    name="total_balance",
    title="Saldo total",
    description="Calcula o saldo (receitas menos despesas), opcionalmente em um período.",
    annotations=LEITURA,
)
def total_balance(
    start_date: Annotated[Optional[str], Field(description="Data/hora ISO 8601 inicial (opcional).")] = None,
    end_date: Annotated[Optional[str], Field(description="Data/hora ISO 8601 final (opcional).")]= None,
) -> dict[str, Any]:
    return _total_balance.invoke({"start_date": start_date, "end_date": end_date})


@mcp.tool(
    name="add_transaction",
    title="Registrar transação",
    description="Registra uma transação financeira.",
    annotations=ESCRITA,
)
def add_transaction(
    amount: Annotated[float, Field(description="Valor da transação (positivo).")],
    source_text: Annotated[str, Field(description="Texto original do usuário.")],
    occurred_at: Annotated[Optional[str], Field(description="Timestamp ISO 8601; se ausente, usa o horário atual.")] = None,
    type_id: Annotated[Optional[int], Field(description="ID do tipo: 1=INCOME, 2=EXPENSES, 3=TRANSFER.")] = None,
    type_name: Annotated[Optional[str], Field(description="Tipo: INCOME | EXPENSES | TRANSFER.")] = None,
    category_name: Annotated[Optional[str], Field(description="Nome da categoria financeira.")] = None,
    category_id: Annotated[Optional[int], Field(description="ID da categoria (1 a 12).")]= None,
    description: Annotated[Optional[str], Field(description="Descrição opcional.")] = None,
    payment_method: Annotated[Optional[str], Field(description="Forma de pagamento opcional.")] = None,
) -> dict[str, Any]:
    return _add_transaction.invoke({
        "amount": amount,
        "source_text": source_text,
        "occurred_at": occurred_at,
        "type_id": type_id,
        "type_name": type_name,
        "category_name": category_name,
        "category_id": category_id,
        "description": description,
        "payment_method": payment_method,
    })


@mcp.tool(
    name="search_transactions",
    title="Buscar transações",
    description="Busca transações com filtros por período, tipo, categoria e forma de pagamento.",
    annotations=LEITURA,
)
def search_transactions(
    relative_period: Annotated[Optional[str], Field(description="Período relativo, como 'hoje' ou 'ontem'; substitui start_date/end_date.")]= None,
    type_name: Annotated[Optional[str], Field(description="Tipo: INCOME | EXPENSES | TRANSFER.")]= None,
    type_id: Annotated[Optional[int], Field(description="ID do tipo: 1=INCOME, 2=EXPENSES, 3=TRANSFER.")]= None,
    category_name: Annotated[Optional[str], Field(description="Nome da categoria financeira.")]= None,
    category_id: Annotated[Optional[int], Field(description="ID da categoria (1 a 12).")]= None,
    payment_method: Annotated[Optional[str], Field(description="Forma de pagamento para filtrar.")]= None,
    start_date: Annotated[Optional[str], Field(description="Data/hora ISO 8601 inicial.")]= None,
    end_date: Annotated[Optional[str], Field(description="Data/hora ISO 8601 final.")]= None,
    limit: Annotated[Optional[int], Field(description="Máximo de registros retornados (padrão 50).")]= 50,
) -> dict[str, Any]:
    return _query_transactions.invoke({
        "relative_period": relative_period,
        "type_name": type_name,
        "type_id": type_id,
        "category_name": category_name,
        "category_id": category_id,
        "payment_method": payment_method,
        "start_date": start_date,
        "end_date": end_date,
        "limit": limit,
    })


@mcp.tool(
    name="daily_balance",
    title="Saldo diário",
    description="Calcula o saldo de receitas menos despesas em uma data.",
    annotations=LEITURA,
)
def daily_balance(
    date: Annotated[Optional[str], Field(description="Data ISO 8601 (YYYY-MM-DD); se ausente, usa hoje.")]= None,
) -> dict[str, Any]:
    return _daily_balance.invoke({"date": date})


@mcp.tool(
    name="update_transaction",
    title="Atualizar transação",
    description="Atualiza uma transação pelo ID ou localiza pela combinação de texto e data local.",
    annotations=ESCRITA,
)
def update_transaction(
    id: Annotated[Optional[int], Field(description="ID da transação a atualizar.")]= None,
    match_text: Annotated[Optional[str], Field(description="Texto para localizar em source_text/description quando não houver ID.")]= None,
    date_local: Annotated[Optional[str], Field(description="Data local YYYY-MM-DD, obrigatória com match_text quando não houver ID.")]= None,
    amount: Annotated[Optional[float], Field(description="Novo valor.")]= None,
    type_id: Annotated[Optional[int], Field(description="Novo ID de tipo: 1=INCOME, 2=EXPENSES, 3=TRANSFER.")]= None,
    type_name: Annotated[Optional[str], Field(description="Novo tipo: INCOME | EXPENSES | TRANSFER.")]= None,
    category_id: Annotated[Optional[int], Field(description="Novo ID de categoria (1 a 12).")]= None,
    category_name: Annotated[Optional[str], Field(description="Novo nome de categoria.")]= None,
    description: Annotated[Optional[str], Field(description="Nova descrição.")]= None,
    payment_method: Annotated[Optional[str], Field(description="Nova forma de pagamento.")]= None,
    occurred_at: Annotated[Optional[str], Field(description="Novo timestamp ISO 8601.")]= None,
) -> dict[str, Any]:
    return _update_transaction.invoke({
        "id": id,
        "match_text": match_text,
        "date_local": date_local,
        "amount": amount,
        "type_id": type_id,
        "type_name": type_name,
        "category_id": category_id,
        "category_name": category_name,
        "description": description,
        "payment_method": payment_method,
        "occurred_at": occurred_at,
    })


if __name__ == "__main__":
    from app.config import DATABASE_URL

    if not DATABASE_URL:
        print("[assessor-financeiro] DATABASE_URL ausente no .env", file=sys.stderr)

    mcp.run(transport="stdio")
