import os
from dotenv import load_dotenv
from langgraph.checkpoint.postgres import PostgresSaver
from psycopg_pool import ConnectionPool

load_dotenv()

def get_memory_saver():
    """
    Inicializa y retorna un PostgresSaver conectado a la BD.
    """
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise ValueError("DATABASE_URL no está definido en el .env")

    pool = ConnectionPool(conninfo=db_url, kwargs={"prepare_threshold": 0, "autocommit": True})
    memory = PostgresSaver(pool)
    return memory
