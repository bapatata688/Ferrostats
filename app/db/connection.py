import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator
from app.config import DB_PATH

SCHEMA_DIR = Path(__file__).resolve().parent

def get_db_connection() -> sqlite3.Connection:
    """
    Crea y configura una conexión SQLite de alto rendimiento:
    - Modo WAL (Write-Ahead Logging) para alta concurrencia de lectura y escritura
    - PRAGMA foreign_keys = ON para integridad referencial ACID estricta
    - PRAGMA busy_timeout = 5000 para evitar bloqueos por cerrojos transitorios
    - PRAGMA synchronous = NORMAL para máximo rendimiento en Cloud Run
    """
    # Asegurar que el directorio contenedor exista
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(
        str(DB_PATH),
        timeout=10.0,
        check_same_thread=False,
        isolation_level=None  # Permite control explícito de transacciones con BEGIN IMMEDIATE
    )
    conn.row_factory = sqlite3.Row
    
    # Activar directivas de rendimiento y consistencia
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA busy_timeout = 5000;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    
    return conn

@contextmanager
def get_db() -> Generator[sqlite3.Connection, None, None]:
    """
    Context manager para transacciones seguras con auto-rollback en caso de excepción.
    """
    conn = get_db_connection()
    try:
        yield conn
    finally:
        conn.close()

def init_db() -> None:
    """
    Inicializa los esquemas relacional (OLTP) y analítico (OLAP).
    """
    oltp_sql_path = SCHEMA_DIR / "schema_oltp.sql"
    olap_sql_path = SCHEMA_DIR / "schema_olap.sql"

    with get_db_connection() as conn:
        with open(oltp_sql_path, "r", encoding="utf-8") as f:
            conn.executescript(f.read())
        with open(olap_sql_path, "r", encoding="utf-8") as f:
            conn.executescript(f.read())
