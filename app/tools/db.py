import psycopg2
from app.config import DATABASE_URL


def get_conn():
    """Abre e devolve uma conexão com o Postgres. Quem chama fecha."""
    return psycopg2.connect(DATABASE_URL)