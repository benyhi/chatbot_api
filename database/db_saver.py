import os
from dotenv import load_dotenv
from langgraph.checkpoint.postgres import PostgresSaver
from psycopg_pool import ConnectionPool

load_dotenv()

# Nota: Cuando se inicia por primera vez el memory saver, se debe llamar a memory.setup()
def get_memory_saver():
    """
    Inicializa y retorna un PostgresSaver conectado a la BD.
    """
    db_url = os.getenv("DATABASE_URL")
    connection_kwargs = {
        "prepare_threshold": 0,
        "autocommit": True,
    }

    if not db_url:
        raise ValueError("DATABASE_URL no está definido.")

    pool = ConnectionPool(conninfo=db_url, kwargs=connection_kwargs)

    memory = PostgresSaver(pool)

    return memory
