import psycopg2
from contextlib import contextmanager
from contextvars import ContextVar
from app.config import DATABASE_URL

_lote = ContextVar("lote_sql", default=None)


class _ConexaoDoLote:
    """Permite reutilizar as tools antigas com um único commit no final."""

    def __init__(self, conn):
        self.conn = conn

    def cursor(self):
        return self.conn.cursor()

    def commit(self):
        pass

    def close(self):
        pass

    def rollback(self):
        self.conn.rollback()


def get_conn():
    """Abre e devolve uma conexão com o Postgres. Quem chama fecha."""
    return _lote.get() or psycopg2.connect(DATABASE_URL)


@contextmanager
def lote_sql():
    conn = psycopg2.connect(DATABASE_URL)
    token = _lote.set(_ConexaoDoLote(conn))
    try:
        yield
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _lote.reset(token)
        try:
            conn.close()
        except Exception:
            pass  # O commit já pode ter sido confirmado.
