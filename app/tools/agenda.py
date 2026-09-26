from typing import Optional, List   # agenda.py importa só Optional
from langchain.tools import tool
from pydantic import BaseModel, Field

from app.tools.db import get_conn

# FILE:app/tools/financeiro.py

def inserir_transacao(valor: float, categoria: str, forma_pagamento: str) -> None:
    # Lógica para inserir uma transação financeira no banco de dados
    pass

def selecionar_transacoes(categoria: str) -> list:
    # Lógica para selecionar transações financeiras por categoria
    pass

def atualizar_transacao(id_transacao: int, novo_valor: float) -> None:
    # Lógica para atualizar uma transação financeira existente
    pass

def obter_saldo() -> float:
    # Lógica para obter o saldo atual
    pass

def exportar_tools() -> list:
    # Exporta a lista de ferramentas financeiras
    return [inserir_transacao, selecionar_transacoes, atualizar_transacao, obter_saldo]