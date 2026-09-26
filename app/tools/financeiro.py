import psycopg2
from typing import Optional, List
from langchain.tools import tool
from pydantic import BaseModel, Field
from rapidfuzz import process
import unicodedata
from datetime import date as date_type, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from app.tools.db import get_conn

# ==================================================================
#                        BASEMODELS
# ==================================================================
# Essa classe garante que o objeto de Python passe todos esses campos
class AddTransactionArgs(BaseModel):
    amount: float = Field(..., description="Valor da transação (use positivo).")
    source_text: str = Field(..., description="Texto original do usuário.")
    occurred_at: Optional[str] = Field(
        default=None,
        description="Timestamp ISO 8601; se ausente, usa NOW() no banco."
    )
    type_id: Optional[int] = Field(default=None, description="ID em transaction_types (1=INCOME, 2=EXPENSES, 3=TRANSFER).")
    type_name: Optional[str] = Field(default=None, description="Nome do tipo: INCOME | EXPENSES | TRANSFER.")
    category_name: Optional[str] = Field(default=None, description="Nome da categoria: COMIDA | BESTEIRA | ESTUDO | FÉRIAS | TRANSPORTE | MORADIA | SAÚDE | LAZER | CONTAS | INVESTIMENTO | PRESENTE | OUTROS")
    category_id: Optional[int] = Field(default=None, description="ID de categories (1=COMIDA,2=BESTEIRA,3=ESTUDO,4=FÉRIAS,5=TRANSPORTE,6=MORADIA,7=SAÚDE,8=LAZER,9=CONTAS,10=INVESTIMENTO,11=PRESENTE,12=OUTROS)")
    description: Optional[str] = Field(default=None, description="Descrição (opcional).")
    payment_method: Optional[str] = Field(default=None, description="Forma de pagamento (opcional).")

class SearchTransactionsArgs(BaseModel):
    relative_period: Optional[str] = Field(
        default=None,
        description=(
            "Período relativo informado pelo usuário. Use 'hoje' ou 'ontem' "
            "sem calcular datas manualmente. Quando preenchido, substitui "
            "start_date e end_date."
        ),
    )
    type_id: Optional[int] = Field(
        default=None, 
        description="ID em transaction_types (1=INCOME, 2=EXPENSES, 3=TRANSFER)."
    )
    type_name: Optional[str] = Field(
        default=None, 
        description="Nome do tipo: INCOME | EXPENSES | TRANSFER."
    )
    category_name: Optional[str] = Field(
        default=None,
        description="Nome da categoria: COMIDA | BESTEIRA | ESTUDO | FÉRIAS | TRANSPORTE | MORADIA | SAÚDE | LAZER | CONTAS | INVESTIMENTO | PRESENTE | OUTROS"
    )
    category_id: Optional[int] = Field(
        default=None,
        description="ID de categories (1=COMIDA,2=BESTEIRA,3=ESTUDO,4=FÉRIAS,5=TRANSPORTE,6=MORADIA,7=SAÚDE,8=LAZER,9=CONTAS,10=INVESTIMENTO,11=PRESENTE,12=OUTROS)"
    )
    payment_method: Optional[str] = Field(
        default=None,
        description="Forma de pagamento para filtrar (opcional). Ex: 'Cartão', 'Pix'."
    )
    start_date: Optional[str] = Field(
        default=None,
        description=(
            "Data/hora inicial ISO 8601 para filtrar transações. "
            "Ex: '2026-03-31 00:00:00'. O agente DEVE calcular essa data "
            "com base na hora atual fornecida no system prompt."
        )
    )
    end_date: Optional[str] = Field(
        default=None,
        description=(
            "Data/hora final ISO 8601 para filtrar transações. "
            "Ex: '2026-03-31 23:59:59'. O agente DEVE calcular essa data "
            "com base na hora atual fornecida no system prompt."
        )
    )
    limit: Optional[int] = Field(
        default=50,
        description="Número máximo de registros a retornar. Padrão: 50."
    )

class GetBalanceArgs(BaseModel):
    start_date: Optional[str] = Field(
        default=None,
        description="Data inicial ISO 8601 para filtrar o período (ex: '2026-03-01'). Se ausente, considera todas as transações."
    )
    end_date: Optional[str] = Field(
        default=None,
        description="Data final ISO 8601 para filtrar o período (ex: '2026-03-31'). Se ausente, considera até agora."
    )

class GetDailyBalanceArgs(BaseModel):
    date: Optional[str] = Field(
        default=None,
        description="Data ISO 8601 (ex: '2026-03-31'). Se ausente, usa o dia atual."
    )

class UpdateTransactionArgs(BaseModel):
    id: Optional[int] = Field(
        default=None,
        description="ID da transação a atualizar. Se ausente, será feita uma busca por (match_text + date_local)."
    )
    match_text: Optional[str] = Field(
        default=None,
        description="Texto para localizar transação quando id não for informado (busca em source_text/description)."
    )
    date_local: Optional[str] = Field(
        default=None,
        description="Data local (YYYY-MM-DD) em America/Sao_Paulo; usado em conjunto com match_text quando id ausente."
    )
    amount: Optional[float] = Field(default=None, description="Novo valor.")
    type_id: Optional[int] = Field(default=None, description="Novo type_id (1/2/3).")
    type_name: Optional[str] = Field(default=None, description="Novo type_name: INCOME | EXPENSES | TRANSFER.")
    category_id: Optional[int] = Field(default=None, description="Nova categoria (id).")
    category_name: Optional[str] = Field(default=None, description="Nova categoria (nome).")
    description: Optional[str] = Field(default=None, description="Nova descrição.")
    payment_method: Optional[str] = Field(default=None, description="Novo meio de pagamento.")
    occurred_at: Optional[str] = Field(default=None, description="Novo timestamp ISO 8601.")

# ===================================================================================
#                                 MÉTODOS
# ===================================================================================
TYPE_ALIASES = {
    # INCOME
    "INCOME": "INCOME",
    "ENTRADA": "INCOME",
    "ENTRADAS": "INCOME",
    "RECEITA": "INCOME",
    "RECEITAS": "INCOME",
    "SALÁRIO": "INCOME",
    "SALARIO": "INCOME",
    "SALÁRIOS": "INCOME",
    "RECEBIMENTO": "INCOME",
    "RECEBIMENTOS": "INCOME",
    "RECEBI": "INCOME",
    "RECEBER": "INCOME",
    "GANHEI": "INCOME",
    "GANHO": "INCOME",
    "GANHOS": "INCOME",
    "RENDA": "INCOME",
    "RENDIMENTO": "INCOME",
    "RENDIMENTOS": "INCOME",
    "REMUNERAÇÃO": "INCOME",
    "REMUNERACAO": "INCOME",
    "PAGAMENTO": "INCOME",      
    "FREELANCE": "INCOME",
    "FREELA": "INCOME",
    "BÔNUS": "INCOME",
    "BONUS": "INCOME",
    "COMISSÃO": "INCOME",
    "COMISSAO": "INCOME",
    "DIVIDENDO": "INCOME",
    "DIVIDENDOS": "INCOME",
    "REEMBOLSO": "INCOME",
    "RESTITUIÇÃO": "INCOME",
    "RESTITUICAO": "INCOME",
    "LUCRO": "INCOME",
    "LUCROS": "INCOME",
    "PRÊMIO": "INCOME",
    "PREMIO": "INCOME",
    "PENSÃO": "INCOME",
    "PENSAO": "INCOME",
    "APOSENTADORIA": "INCOME",
    "MESADA": "INCOME",
    "ALUGUEL RECEBIDO": "INCOME",

    # EXPENSES
    "EXPENSE": "EXPENSES",
    "EXPENSES": "EXPENSES",
    "DESPESA": "EXPENSES",
    "DESPESAS": "EXPENSES",
    "GASTO": "EXPENSES",
    "GASTOS": "EXPENSES",
    "GASTEI": "EXPENSES",
    "GASTAR": "EXPENSES",
    "SAÍDA": "EXPENSES",
    "SAIDA": "EXPENSES",
    "SAÍDAS": "EXPENSES",
    "SAIDAS": "EXPENSES",
    "PAGUEI": "EXPENSES",
    "PAGAR": "EXPENSES",
    "COMPREI": "EXPENSES",
    "COMPRA": "EXPENSES",
    "COMPRAS": "EXPENSES",
    "DÉBITO": "EXPENSES",
    "DEBITO": "EXPENSES",
    "CONTA": "EXPENSES",
    "CONTAS": "EXPENSES",
    "CUSTO": "EXPENSES",
    "CUSTOS": "EXPENSES",
    "GASTO FIXO": "EXPENSES",
    "GASTO VARIÁVEL": "EXPENSES",
    "GASTO VARIAVEL": "EXPENSES",
    "BOLETO": "EXPENSES",
    "FATURA": "EXPENSES",
    "PARCELAMENTO": "EXPENSES",
    "PARCELA": "EXPENSES",
    "MENSALIDADE": "EXPENSES",
    "ASSINATURA": "EXPENSES",
    "TORREI": "EXPENSES",      
    "TORRAR": "EXPENSES",      
    "GASTANÇA": "EXPENSES",    

    # TRANSFER
    "TRANSFER": "TRANSFER",
    "TRANSFERÊNCIA": "TRANSFER",
    "TRANSFERENCIA": "TRANSFER",
    "TRANSFERÊNCIAS": "TRANSFER",
    "TRANSFERENCIAS": "TRANSFER",
    "TRANSFERI": "TRANSFER",
    "TRANSFERIR": "TRANSFER",
    "MANDEI": "TRANSFER",
    "MANDAR": "TRANSFER",
    "ENVIEI": "TRANSFER",
    "ENVIAR": "TRANSFER",
    "ENVIO": "TRANSFER",
    "PIX": "TRANSFER",
    "PIXEI": "TRANSFER",       
    "PIXAR": "TRANSFER",       
    "TED": "TRANSFER",
    "DOC": "TRANSFER",
    "MOVIMENTAÇÃO": "TRANSFER",
    "MOVIMENTACAO": "TRANSFER",
    "MOVIMENTEI": "TRANSFER",
}

CATEGORIES_ALIASES = {
    # COMIDA (1)
    "COMIDA": "COMIDA", "ALMOÇO": "COMIDA", "ALMOCO": "COMIDA", "JANTA": "COMIDA",
    "JANTAR": "COMIDA", "LANCHE": "COMIDA", "LANCHINHO": "COMIDA",
    "RESTAURANTE": "COMIDA", "IFOOD": "COMIDA", "DELIVERY": "COMIDA",
    "PEDIDO": "COMIDA", "MERCADO": "COMIDA", "SUPERMERCADO": "COMIDA",
    "COMPRA": "COMIDA", "COMPRAS": "COMIDA", "PADARIA": "COMIDA",
    "CAFÉ": "COMIDA", "CAFE": "COMIDA", "CAFETERIA": "COMIDA",
    "PIZZA": "COMIDA", "HAMBURGUER": "COMIDA", "BURGER": "COMIDA",
    "REFEIÇÃO": "COMIDA", "REFEICAO": "COMIDA", "PRATO": "COMIDA",
    "BEBIDA": "COMIDA", "SUCO": "COMIDA", "REFRIGERANTE": "COMIDA",
    "ENERGÉTICO": "COMIDA", "ENERGETICO": "COMIDA","ALIMENTACAO":"COMIDA",

    # BESTEIRA (2)
    "BESTEIRA": "BESTEIRA", "DOCE": "BESTEIRA", "DOCES": "BESTEIRA",
    "CHOCOLATE": "BESTEIRA", "BALA": "BESTEIRA", "BALAS": "BESTEIRA",
    "SORVETE": "BESTEIRA", "SNACK": "BESTEIRA", "SALGADINHO": "BESTEIRA",
    "SALGADINHOS": "BESTEIRA", "FASTFOOD": "BESTEIRA", "FAST FOOD": "BESTEIRA",
    "PORCARIA": "BESTEIRA", "GULOSEIMA": "BESTEIRA",

    # ESTUDO (3)
    "ESTUDO": "ESTUDO", "ESTUDOS": "ESTUDO", "CURSO": "ESTUDO",
    "CURSOS": "ESTUDO", "FACULDADE": "ESTUDO", "UNIVERSIDADE": "ESTUDO",
    "ESCOLA": "ESTUDO", "LIVRO": "ESTUDO", "LIVROS": "ESTUDO",
    "APOSTILA": "ESTUDO", "MATERIAL": "ESTUDO", "MENSALIDADE": "ESTUDO",
    "PROVA": "ESTUDO", "EXAME": "ESTUDO", "AULA": "ESTUDO",
    "AULAS": "ESTUDO", "CERTIFICAÇÃO": "ESTUDO", "CERTIFICACAO": "ESTUDO",

    # FÉRIAS (4)
    "FÉRIAS": "FERIAS", "FERIAS": "FERIAS", "VIAGEM": "FERIAS",
    "VIAJAR": "FERIAS", "HOTEL": "FERIAS", "HOSTEL": "FERIAS",
    "AIRBNB": "FERIAS", "PASSEIO": "FERIAS", "TURISMO": "FERIAS",
    "TURISTICO": "FERIAS", "RESORT": "FERIAS", "VOO": "FERIAS", 
    "AEROPORTO": "FERIAS",

    # TRANSPORTE (5)
    "TRANSPORTE": "TRANSPORTE", "UBER": "TRANSPORTE", "99": "TRANSPORTE",
    "TAXI": "TRANSPORTE", "ÔNIBUS": "TRANSPORTE", "ONIBUS": "TRANSPORTE",
    "METRO": "TRANSPORTE", "TREM": "TRANSPORTE", "PASSAGEM": "TRANSPORTE",
    "GASOLINA": "TRANSPORTE", "COMBUSTÍVEL": "TRANSPORTE",
    "COMBUSTIVEL": "TRANSPORTE", "ETANOL": "TRANSPORTE",
    "DIESEL": "TRANSPORTE", "ESTACIONAMENTO": "TRANSPORTE",
    "PEDAGIO": "TRANSPORTE",

    # MORADIA (6)
    "MORADIA": "MORADIA", "CASA": "MORADIA", "APARTAMENTO": "MORADIA",
    "ALUGUEL": "MORADIA", "CONDOMINIO": "MORADIA", "CONDOMÍNIO": "MORADIA",
    "LUZ": "MORADIA", "ENERGIA": "MORADIA", "ÁGUA": "MORADIA",
    "AGUA": "MORADIA", "INTERNET": "MORADIA", "WI-FI": "MORADIA",
    "WIFI": "MORADIA", "GÁS": "MORADIA", "GAS": "MORADIA",
    "MANUTENÇÃO": "MORADIA", "MANUTENCAO": "MORADIA",

    # SAÚDE (7)
    "SAÚDE": "SAUDE", "SAUDE": "SAUDE", "REMÉDIO": "SAUDE",
    "REMEDIO": "SAUDE", "REMÉDIOS": "SAUDE", "FARMACIA": "SAUDE",
    "CONSULTA": "SAUDE", "MÉDICO": "SAUDE", "MEDICO": "SAUDE",
    "EXAME": "SAUDE", "CLINICA": "SAUDE", "HOSPITAL": "SAUDE",
    "PLANO": "SAUDE", "CONVENIO": "SAUDE", "DENTISTA": "SAUDE",

    # LAZER (8)
    "LAZER": "LAZER", "CINEMA": "LAZER", "FILME": "LAZER",
    "JOGO": "LAZER", "JOGOS": "LAZER", "STREAMING": "LAZER",
    "NETFLIX": "LAZER", "SPOTIFY": "LAZER", "SHOW": "LAZER",
    "FESTA": "LAZER", "BAR": "LAZER", "BALADA": "LAZER",
    "VIAGEM": "LAZER", "PASSEIO": "LAZER",

    # CONTAS (9)
    "CONTAS": "CONTAS", "BOLETO": "CONTAS", "FATURA": "CONTAS",
    "CARTÃO": "CONTAS", "CARTAO": "CONTAS", "DIVIDA": "CONTAS",
    "DÍVIDA": "CONTAS", "PAGAMENTO": "CONTAS", "PAGAR": "CONTAS",
    "COBRANÇA": "CONTAS", "COBRANCA": "CONTAS",

    # INVESTIMENTO (10)
    "INVESTIMENTO": "INVESTIMENTO", "INVESTIR": "INVESTIMENTO",
    "AÇÃO": "INVESTIMENTO", "ACOES": "INVESTIMENTO", "AÇÃO": "INVESTIMENTO",
    "BOLSA": "INVESTIMENTO", "CRIPTO": "INVESTIMENTO",
    "CRYPTO": "INVESTIMENTO", "BITCOIN": "INVESTIMENTO",
    "ETHEREUM": "INVESTIMENTO", "TESOURO": "INVESTIMENTO",
    "RENDA": "INVESTIMENTO", "APLICAÇÃO": "INVESTIMENTO",
    "APLICACAO": "INVESTIMENTO",

    # PRESENTE (11)
    "PRESENTE": "PRESENTE", "GIFT": "PRESENTE",
    "LEMBRANÇA": "PRESENTE", "LEMBRANCA": "PRESENTE",
    "BRINDE": "PRESENTE", "SURPRESA": "PRESENTE",

    # OUTROS (12)
    "OUTROS": "OUTROS", "DIVERSOS": "OUTROS",
    "GERAL": "OUTROS", "RUA": "OUTROS",
    "VARIOS": "OUTROS", "ALEATORIO": "OUTROS"
}

def find_category(text, categories):
    melhor_match, score, _ = process.extractOne(
        text,
        categories.keys()
    )
    if score >= 70:
        return categories[melhor_match]
    return "OUTROS"

def find_type(text,types):
    melhor_match, score, _ = process.extractOne(
        text,
        types.keys()
    )
    if score >= 70:
        return types[melhor_match]
    return " "

def normalize(text):
    text = text.upper()
    text = unicodedata.normalize("NFD", text)
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
    return text

def _local_date_filter_sql(field: str = "occurred_at") -> str:
    """
    Retorna um trecho SQL para filtragem por dia local em America/Sao_Paulo.
    Ex.: (occurred_at AT TIME ZONE 'America/Sao_Paulo')::date = %s::date
    """
    return f"(({field} AT TIME ZONE 'America/Sao_Paulo')::date = %s::date)"


try:
    FUSO_LOCAL = ZoneInfo("America/Sao_Paulo")
except ZoneInfoNotFoundError:
    # Algumas instalações do Python no Windows não incluem a base IANA tzdata.
    # Desde 2019, São Paulo não utiliza horário de verão, portanto UTC-03:00 é
    # um fallback adequado para calcular os limites de "hoje" e "ontem".
    FUSO_LOCAL = timezone(timedelta(hours=-3), name="America/Sao_Paulo")


def _intervalo_relativo(periodo: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    """Converte períodos relativos em limites ISO com fuso horário explícito."""
    if not periodo:
        return None, None

    periodo_normalizado = normalize(periodo).strip()
    hoje = datetime.now(FUSO_LOCAL).date()

    if periodo_normalizado == "HOJE":
        dia = hoje
    elif periodo_normalizado == "ONTEM":
        dia = hoje - timedelta(days=1)
    else:
        return None, None

    inicio = datetime.combine(dia, time.min, tzinfo=FUSO_LOCAL)
    proximo_dia = inicio + timedelta(days=1)
    return inicio.isoformat(), proximo_dia.isoformat()

def _sum_by_type(cur, type_id: int, start_date: Optional[str], end_date: Optional[str]) -> float:
    query = "SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE type = %s"
    params = [type_id]

    if start_date:
        query += " AND occurred_at >= %s"
        params.append(start_date)
    if end_date:
        query += " AND occurred_at <= %s"
        params.append(end_date)

    cur.execute(query, params)
    return float(cur.fetchone()[0])

def _resolve_type_id(cur, type_id: Optional[int], type_name: Optional[str]) -> Optional[int]:
    if type_name:
        t = normalize(type_name)
        t = find_type(t,TYPE_ALIASES)
        
        if t == ' ':
            return 2
        cur.execute("SELECT id FROM transaction_types WHERE UPPER(type)=%s LIMIT 1;", (t,))
        row = cur.fetchone()
        return row[0] if row else None
    if type_id:
        return int(type_id)
    return None

def _resolve_category_id(cur, category_id: Optional[int], category_name: Optional[str]) -> Optional[int]:
    if category_name:
        c = normalize(category_name)
        
        c = find_category(c,CATEGORIES_ALIASES)
        
        cur.execute("SELECT id FROM categories WHERE UPPER(name)=%s LIMIT 1;",(c,))
        row = cur.fetchone()
        return row[0] if row else None
    if category_id:
        return int(category_id)
    return None

# ====================================================================
#                           TOOLS
# ====================================================================

# Tool: add_transaction
@tool("add_transaction", args_schema=AddTransactionArgs)
def add_transaction(
    amount: float,
    source_text: str,
    occurred_at: Optional[str] = None,
    type_id: Optional[int] = None,
    type_name: Optional[str] = None,
    category_name: Optional[str] = None,
    category_id: Optional[int] = None,
    description: Optional[str] = None,
    payment_method: Optional[str] = None,
) -> dict:
    """Insere uma transação financeira no banco de dados Postgres.""" # docstring obrigatório da @tools do langchain (estranho, mas legal né?)
    conn = get_conn()
    cur = conn.cursor()
    try:
        resolved_type_id = _resolve_type_id(cur, type_id, type_name)
        resolved_category_id = _resolve_category_id(cur,category_id,category_name)
        if not resolved_type_id:
            return {"status": "error", "message": "Tipo inválido (use type_id ou type_name: INCOME/EXPENSES/TRANSFER)."}
        if not resolved_category_id:
            return {"status": "error", "message": "Categoria inválida (use category_id ou category_name: COMIDA/BESTEIRA/ESTUDO/FÉRIAS/TRANSPORTE/MORADIA/SAÚDE/LAZER/CONTAS/INVESTIMENTO/PRESENTE/OUTROS)."}

        if occurred_at:
            cur.execute(
                """
                INSERT INTO transactions
                    (amount, type, category_id, description, payment_method, occurred_at, source_text)
                VALUES
                    (%s, %s, %s, %s, %s, %s::timestamptz, %s)
                RETURNING id, occurred_at;
                """,
                (amount, resolved_type_id, resolved_category_id, description, payment_method, occurred_at, source_text),
            )
        else:
            cur.execute(
                """
                INSERT INTO transactions
                    (amount, type, category_id, description, payment_method, occurred_at, source_text)
                VALUES
                    (%s, %s, %s, %s, %s, NOW(), %s)
                RETURNING id, occurred_at;
                """,
                (amount, resolved_type_id, resolved_category_id, description, payment_method, source_text),
            )
        new_id, occurred = cur.fetchone()
        conn.commit()
        return {"status": "ok", "id": new_id, "occurred_at": str(occurred)}

    except Exception as e:
        conn.rollback()
        return {"status": "error", "message": str(e)}
    finally:
        try:
            cur.close()
            conn.close()
        except Exception:
            pass

@tool("search_transactions", args_schema=SearchTransactionsArgs)
def search_transactions(
    relative_period: Optional[str] = None,
    type_name: Optional[str] = None,
    type_id: Optional[int] = None,
    category_name: Optional[str] = None,
    category_id: Optional[int] = None,
    payment_method: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: Optional[int] = 50,
) -> dict:
    """Busca as transações feitas pelo usuário."""
    conn = get_conn()
    cur = conn.cursor()

    try:
        relative_start, relative_end = _intervalo_relativo(relative_period)
        if relative_start:
            start_date = relative_start
            end_date = relative_end

        resolve_category_id = _resolve_category_id(cur,category_id,category_name)
        resolve_type_id = _resolve_type_id(cur,type_id,type_name)
        query = """
            SELECT 
                t.amount AS "Valor da transação"
                ,tt.type AS "Tipo da transação"
                ,c.name AS "Categoria"
                ,t.description AS "descrição"
                ,t.payment_method AS "Método de pagamento"
                ,(t.occurred_at AT TIME ZONE 'America/Sao_Paulo')::date AS "Data da Transação"
                ,(t.occurred_at AT TIME ZONE 'America/Sao_Paulo')::time AS "Hora da transação" 
            FROM transactions t 
            JOIN transaction_types tt ON t.type = tt.id 
            JOIN categories c ON c.id = t.category_id"""
        filtros = []
        params = []

        if resolve_type_id:
            filtros.append("t.type = %s")
            params.append(resolve_type_id)
        if resolve_category_id:
            filtros.append("t.category_id = %s")
            params.append(resolve_category_id)
        if payment_method:
            filtros.append("t.payment_method = %s")
            params.append(payment_method)
        if start_date:
            filtros.append("t.occurred_at >= %s")
            params.append(start_date)
        if end_date:
            filtros.append("t.occurred_at < %s" if relative_end else "t.occurred_at <= %s")
            params.append(end_date)

        if filtros:
            query += " WHERE "+" AND ".join(filtros)
            query += " ORDER BY t.occurred_at DESC LIMIT "+str(limit)
            cur.execute(query, params)
        else:
            query += " ORDER BY t.occurred_at DESC LIMIT "+str(limit)
            cur.execute(query)
        rows = cur.fetchall()
        cols = [desc[0] for desc in cur.description]
        table = [dict(zip(cols, row)) for row in rows]
        return {
            "status": "ok",
            "table":table,
            "period": {
                "start_date": start_date or "início",
                "end_date": end_date or "agora"
            }
        }
    except Exception as e:
        conn.rollback()
        return {"status": "error", "message": str(e)}
    finally:
        try:
            cur.close()
            conn.close()
        except Exception:
            pass 

@tool("saldo_total", args_schema=GetBalanceArgs)
def saldo_total(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> dict:
    """Calcula o saldo atual do usuário: soma de INCOME (type=1) menos soma de EXPENSES (type=2)."""
    conn = get_conn()
    cur = conn.cursor()
    try:
        
        total_income = _sum_by_type(cur,1,start_date,end_date)
        total_expense = _sum_by_type(cur,2,start_date,end_date)

        balance = total_income - total_expense

        return {
            "status": "ok",
            "total_income": total_income,
            "total_expense": total_expense,
            "balance": balance,
            "period": {
                "start_date": start_date or "início",
                "end_date": end_date or "agora"
            }
        }
    except Exception as e:
        conn.rollback()
        return {"status": "error", "message": str(e)}
    finally:
        try:
            cur.close()
            conn.close()
        except Exception:
            pass 

@tool("saldo_diario", args_schema=GetDailyBalanceArgs)
def saldo_diario(
    date: Optional[str] = None
) -> dict:
    """Calcula o saldo do dia: soma de INCOME (type=1) menos soma de EXPENSES (type=2) do dia atual."""
    conn = get_conn()
    cur = conn.cursor()
    try:
        target_date = date or str(date_type.today())
        start = f"{target_date} 00:00:00"
        end   = f"{target_date} 23:59:59"

        total_income  = _sum_by_type(cur, 1, start, end)
        total_expense = _sum_by_type(cur, 2, start, end)
        balance = total_income - total_expense

        return {
            "status": "ok",
            "date": target_date,
            "total_income": total_income,
            "total_expense": total_expense,
            "balance": balance,
        }
    except Exception as e:
        conn.rollback()
        return {"status": "error", "message": str(e)}
    finally:
        try:
            cur.close()
            conn.close()
        except Exception:
            pass

@tool("update_transaction", args_schema=UpdateTransactionArgs)
def update_transaction(
    id: Optional[int] = None,
    match_text: Optional[str] = None,
    date_local: Optional[str] = None,
    amount: Optional[float] = None,
    type_id: Optional[int] = None,
    type_name: Optional[str] = None,
    category_id: Optional[int] = None,
    category_name: Optional[str] = None,
    description: Optional[str] = None,
    payment_method: Optional[str] = None,
    occurred_at: Optional[str] = None,
) -> dict:
    """
    Atualiza uma transação existente.
    Estratégias:
      - Se 'id' for informado: atualiza diretamente por ID.
      - Caso contrário: localiza a transação mais recente que combine (match_text em source_text/description)
        E (date_local em America/Sao_Paulo), então atualiza.
    Retorna: status, rows_affected, id, e o registro atualizado.
    """
    if not any([amount, type_id, type_name, category_id, category_name, description, payment_method, occurred_at]):
        return {"status": "error", "message": "Nada para atualizar: forneça pelo menos um campo (amount, type, category, description, payment_method, occurred_at)."}

    conn = get_conn()
    cur = conn.cursor()
    try:
        # Resolve target_id
        target_id = id
        if target_id is None:
            if not match_text or not date_local:
                return {"status": "error", "message": "Sem 'id': informe match_text E date_local para localizar o registro."}

            # Buscar o mais recente no dia local informado que combine o texto
            cur.execute(
                f"""
                SELECT t.id
                FROM transactions t
                WHERE (t.source_text ILIKE %s OR t.description ILIKE %s)
                  AND {_local_date_filter_sql("t.occurred_at")}
                ORDER BY t.occurred_at DESC
                LIMIT 1;
                """,
                (f"%{match_text}%", f"%{match_text}%", date_local)
            )
            row = cur.fetchone()
            if not row:
                return {"status": "error", "message": "Nenhuma transação encontrada para os filtros fornecidos."}
            target_id = row[0]

        # Resolver type_id / category_id a partir de nomes, se fornecidos
        resolved_type_id = _resolve_type_id(cur, type_id, type_name) if (type_id or type_name) else None
        resolved_category_id = category_id
        if category_name and not category_id:
            resolved_category_id = _resolve_category_id(cur,category_id, category_name)

        # Montar SET dinâmico
        sets = []
        params: List[object] = []
        if amount is not None:
            sets.append("amount = %s")
            params.append(amount)
        if resolved_type_id is not None:
            sets.append("type = %s")
            params.append(resolved_type_id)
        if resolved_category_id is not None:
            sets.append("category_id = %s")
            params.append(resolved_category_id)
        if description is not None:
            sets.append("description = %s")
            params.append(description)
        if payment_method is not None:
            sets.append("payment_method = %s")
            params.append(payment_method)
        if occurred_at is not None:
            sets.append("occurred_at = %s::timestamptz")
            params.append(occurred_at)

        if not sets:
            return {"status": "error", "message": "Nenhum campo válido para atualizar."}

        params.append(target_id)

        cur.execute(
            f"UPDATE transactions SET {', '.join(sets)} WHERE id = %s;",
            params
        )
        rows_affected = cur.rowcount
        conn.commit()

        # Retornar o registro atualizado
        cur.execute(
            """
            SELECT
              t.id, t.occurred_at, t.amount, tt.type AS type_name,
              c.name AS category_name, t.description, t.payment_method, t.source_text
            FROM transactions t
            JOIN transaction_types tt ON tt.id = t.type
            LEFT JOIN categories c ON c.id = t.category_id
            WHERE t.id = %s;
            """,
            (target_id,)
        )
        r = cur.fetchone()
        updated = None
        if r:
            updated = {
                "id": r[0],
                "occurred_at": str(r[1]),
                "amount": float(r[2]),
                "type": r[3],
                "category": r[4],
                "description": r[5],
                "payment_method": r[6],
                "source_text": r[7],
            }

        return {
            "status": "ok",
            "rows_affected": rows_affected,
            "id": target_id,
            "updated": updated
        }

    except Exception as e:
        conn.rollback()
        return {"status": "error", "message": str(e)}
    finally:
        try:
            cur.close()
            conn.close()
        except Exception:
            pass

    
# Exporta a lista de tools
TOOLS = [add_transaction,search_transactions,saldo_total,saldo_diario]
