import os
from pathlib import Path

# Directorio raíz del proyecto
BASE_DIR = Path(__file__).resolve().parent.parent

# Entorno de ejecución
ENV = os.getenv("ENV", "development")

# Ruta de almacenamiento de SQLite (en Cloud Run apunta a /tmp/ferrostats.db o /mnt/data/ferrostats.db)
DB_PATH = Path(os.getenv("DB_PATH", str(BASE_DIR / "data" / "db" / "ferrostats.db")))

# Asegurar que el directorio de la base de datos exista
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# Directorio de semillas CSV
SEEDS_DIR = BASE_DIR / "data" / "seeds"

# Sincronización opcional hacia BigQuery Free Tier
ENABLE_BIGQUERY_SYNC = os.getenv("ENABLE_BIGQUERY_SYNC", "false").lower() in ("true", "1", "yes")
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "ferrostats")
BIGQUERY_DATASET = os.getenv("BIGQUERY_DATASET", "ferrostats_dw")

# Metadatos del proyecto y control determinista
APP_NAME = "FERROSTATS"
AUTHOR = "Diego Alejandro Escobar Barahona"
APP_VERSION = "1.0.0"
RANDOM_SEED = 2026

# Configuración del servidor
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8080"))
