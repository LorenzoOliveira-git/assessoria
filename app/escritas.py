"""Escritas do chat aguardam o juiz; nada fica guardado após o turno."""
from contextlib import contextmanager
from contextvars import ContextVar
from decimal import Decimal, InvalidOperation
from functools import wraps
from inspect import signature
import json
import re
from threading import Lock

from app.tools.db import get_conn, lote_sql

_turno = ContextVar("turno_escritas", default=None)
_chat_lock = Lock()  # O checkpointer deste projeto é local e não aceita o mesmo chat em paralelo.


def atual():
    return _turno.get()


def serializar(func):
    @wraps(func)
    def chamada(*args, **kwargs):
        with _chat_lock:
            return func(*args, **kwargs)
    return chamada


@contextmanager
def contexto(turno_id, pergunta):
    turno = Turno(turno_id, pergunta)

    token = _turno.set(turno)

    try:
        yield turno
    finally:
        turno.fechado = True
        _turno.reset(token)


_VALOR = r"(?:\d{1,3}(?:\.\d{3})+|\d+)(?:,\d{1,2})?"
_BRL = re.compile(rf"(?:R\$\s*|BRL\s*)({_VALOR})\b|({_VALOR})\s*(?:reais|real|BRL)\b", re.I)


def moeda_brl(texto):
    """O texto de origem menciona reais de forma reconhecível?"""
    return bool(_BRL.search(texto or ""))


def validar_valor(valor, pergunta, remover=False):

    try:
        numero = Decimal(str(valor))
        if not numero.is_finite() or numero < 0 or numero >= Decimal("1000000000000") or numero != numero.quantize(Decimal("0.01")):
            raise ValueError("Informe um valor válido com até duas casas decimais.")
    except InvalidOperation as exc:
        raise ValueError("Informe um valor válido.") from exc
    
    if remover and numero == 0 and re.search(r"\b(remov\w*|exclu\w*|apag\w*)\b", pergunta, re.I):
        return
    
    valores = [Decimal((a or b).replace('.', '').replace(',', '.')) for a, b in _BRL.findall(pergunta)]

    if numero not in valores:
        raise ValueError("Só posso registrar valores informados em reais (R$), sem conversão.")


def _preparar(nome, args, pergunta):
    args = dict(args)
    if "source_text" in args:
        args["source_text"] = pergunta

    if nome == "add_transaction":
        validar_valor(args["amount"], pergunta)

    if nome == "update_transaction":
        if args.get("amount") is not None:
            validar_valor(args["amount"], pergunta, remover=True)
        conn = get_conn()
        try:
            with conn.cursor() as cur:
                if args.get("id") is not None:
                    cur.execute("SELECT id, source_text FROM transactions WHERE id = %s", (args["id"],))
                elif args.get("match_text") and args.get("date_local"):
                    cur.execute("""SELECT id, source_text FROM transactions
                        WHERE (source_text ILIKE %s OR description ILIKE %s)
                        AND (occurred_at AT TIME ZONE 'America/Sao_Paulo')::date = %s::date
                        ORDER BY occurred_at DESC LIMIT 2""",
                        (f"%{args['match_text']}%", f"%{args['match_text']}%", args["date_local"]))
                else:
                    raise ValueError("Informe o ID ou texto e data da transação.")
                rows = cur.fetchall()
                if len(rows) != 1:
                    raise ValueError("Transação inexistente ou busca ambígua; informe o ID.")
                if args.get("amount") is not None and not moeda_brl(rows[0][1]):
                    raise ValueError("A moeda desta transação antiga não está clara; não alterei o valor.")
                args["id"] = rows[0][0]
                args["match_text"] = args["date_local"] = None
        finally:
            conn.close()
    return args


def escrita(func):
    """Mantém a assinatura da tool antiga e substitui a execução por preparação."""
    assinatura = signature(func)

    @wraps(func)
    def preparar(*args, **kwargs):
        turno = atual()
        if turno is None:
            return {"status": "error", "message": "Escrita disponível somente no fluxo do chat com juiz."}
        ligados = assinatura.bind(*args, **kwargs)
        ligados.apply_defaults()
        return turno.preparar(func, ligados.arguments)
    return preparar


class Turno:
    def __init__(self, turno_id, pergunta):
        self.id, self.pergunta = turno_id, pergunta
        self.operacoes = []
        self.erros = []
        self.fechado = False
        self.resposta = None
        self.status = "ok"
        self.lock = Lock()

    @property
    def tem_escritas(self):
        return bool(self.operacoes or self.erros)

    def preparar(self, func, argumentos):
        with self.lock:
            if self.fechado:
                return {"status": "error", "message": "Turno encerrado."}
            try:
                # Guarda uma cópia dos argumentos, que não muda após a preparação.
                args = json.loads(json.dumps(
                    _preparar(func.__name__, argumentos, self.pergunta),
                    ensure_ascii=False, allow_nan=False,
                ))
            except ValueError as exc:
                self.erros.append(str(exc))
                return {"status": "error", "message": str(exc), "persistido": False}
            except Exception:
                self.erros.append("Não foi possível preparar a escrita.")
                return {"status": "error", "message": self.erros[-1], "persistido": False}
            for op in self.operacoes:
                if op["nome"] == func.__name__ and op["args"] == args:
                    return {"status": "pendente", "persistido": False, "operacao_id": op["id"]}
            op = {"id": f"{self.id}:{len(self.operacoes) + 1}", "nome": func.__name__,
                  "args": args, "func": func}
            self.operacoes.append(op)
            return {"status": "pendente", "persistido": False, "operacao_id": op["id"]}

    def manifesto(self):
        self.fechado = True
        return json.dumps({"turno": self.id, "persistido": False,
            "operacoes": [{"id": op["id"], "tool": op["nome"], "args": op["args"]} for op in self.operacoes],
            "erros": self.erros}, ensure_ascii=False)

    def concluir(self, aprovado):
        with self.lock:
            if self.resposta is not None:
                return self.resposta
            if aprovado is not True or self.erros:
                self.status = "bloqueado"
                self.resposta = (self.erros[0] if self.erros else "O juiz não aprovou a solicitação.") + " Nenhuma escrita deste turno foi executada."
                return self.resposta
            locais = [op for op in self.operacoes if op["nome"] != "add_google_event"]
            externos = [op for op in self.operacoes if op["nome"] == "add_google_event"]
            try:
                if locais:
                    with lote_sql():
                        for op in locais:
                            op["resultado"] = op["func"](**op["args"])
                            resultado = op["resultado"]
                            if resultado.get("status") != "ok" or not resultado.get("id") or resultado.get("rows_affected") == 0:
                                raise ValueError("A escrita não foi concluída.")
                        partes = [_recibo(op) for op in locais]
                else:
                    partes = []
            except Exception:
                self.status = "erro"
                self.resposta = "Não foi possível confirmar a gravação. Confira os registros antes de repetir; o Google Calendar não foi acionado."
                return self.resposta
            for op in externos:
                try:
                    resultado = op["func"](**op["args"])
                    confirmado = resultado.get("status") == "ok" and resultado.get("id")
                except Exception:
                    confirmado = False
                if confirmado:
                    partes.append("Evento criado no Google Calendar; isso não confirma convites.")
                else:
                    self.status = "erro"
                    partes.append("Não consegui confirmar o evento no Google Calendar. Confira a agenda antes de repetir.")
            self.resposta = "\n".join(partes)
            return self.resposta


def _recibo(op):
    nome, dados = op["nome"], op["resultado"]
    if nome == "add_event":
        return f"Evento registrado na agenda local (ID {int(dados['id'])}), início {dados['start_time']}."
    if nome == "add_transaction":
        valor = op["args"]["amount"]
        return f"Transação registrada (ID {int(dados['id'])}): R$ {Decimal(str(valor)):.2f}.".replace('.', ',')
    atualizado = dados.get("updated") or {}
    if not atualizado:
        raise ValueError("A atualização não devolveu o registro.")
    moeda = "R$" if moeda_brl(atualizado.get("source_text")) else "moeda não confirmada"
    return f"Transação atualizada (ID {int(dados['id'])}): {moeda} {Decimal(str(atualizado['amount'])):.2f}.".replace('.', ',')
