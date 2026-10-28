from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import APP_NAME, AUTHOR, APP_VERSION
from app.db.connection import init_db
from app.db.seed_loader import load_csv_seeds, generate_historical_sales_if_empty
from app.etl.local_pipeline import run_local_etl_if_empty
from app.api.routes_inventory import router as inventory_router
from app.api.routes_pos import router as pos_router
from app.api.routes_analytics import router as analytics_router

STATIC_DIR = Path(__file__).resolve().parent / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Ciclo de vida de la aplicación:
    Al arrancar en frío (Cold Start) en Cloud Run o en desarrollo local:
    1. Inicializa las tablas OLTP y OLAP si no existen.
    2. Carga catálogos CSV si faltan datos maestros.
    3. Genera deterministamente 180 ventas históricas si la tabla está vacía.
    4. Compila el esquema analítico local (Data Marts y Hechos) y compuertas de calidad.
    5. La arquitectura Medallón en la nube opera vía Google Dataform & BigQuery ($0.00 USD).
    """
    print(f"[*] Starting {APP_NAME} v{APP_VERSION} (Lead Architect: {AUTHOR})...")
    init_db()
    load_csv_seeds()
    generate_historical_sales_if_empty()
    run_local_etl_if_empty()
    print("[+] Inicialización completada. Plataforma lista para servir tráfico.")
    yield
    print("[-] Apagando servicio FERROSTATS.")

app = FastAPI(
    title="FERROSTATS — Business Intelligence & POS Platform",
    description=(
        "Cloud-Native Business Intelligence, Automated ELT Data Lakehouse, "
        "and ACID Point-of-Sale Platform. Built under a $0.00 USD Serverless "
        "Always Free Tier architecture on Google Cloud Platform."
    ),
    version=APP_VERSION,
    lifespan=lifespan
)

# Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inclusión de Routers de la API
app.include_router(inventory_router)
app.include_router(pos_router)
app.include_router(analytics_router)

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"

# Montar archivos estáticos para la interfaz Web
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
if (ASSETS_DIR / "capturas").exists():
    app.mount("/capturas", StaticFiles(directory=str(ASSETS_DIR / "capturas")), name="capturas")
if ASSETS_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(ASSETS_DIR)), name="assets")

NO_CACHE_HEADERS = {
    "Cache-Control": "no-cache, no-store, must-revalidate",
    "Pragma": "no-cache",
    "Expires": "0"
}

@app.get("/", include_in_schema=False)
def serve_spa():
    """Sirve el Portal Gerencial (Bodega & Business Intelligence)."""
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file), headers=NO_CACHE_HEADERS)
    return {
        "message": "Bienvenido a FERROSTATS API",
        "docs": "/docs"
    }

@app.get("/pos", include_in_schema=False)
def serve_pos():
    """Sirve la Terminal Dedicada de Punto de Venta (POS) para Cajeros de Mostrador."""
    pos_file = STATIC_DIR / "pos.html"
    if pos_file.exists():
        return FileResponse(str(pos_file), headers=NO_CACHE_HEADERS)
    return FileResponse(str(STATIC_DIR / "index.html"), headers=NO_CACHE_HEADERS)

@app.get("/bodega", include_in_schema=False)
def serve_bodega():
    """Redirige directamente al control de bodega en la SPA."""
    return FileResponse(str(STATIC_DIR / "index.html"), headers=NO_CACHE_HEADERS)

@app.get("/presentacion", include_in_schema=False)
def serve_presentacion():
    """Sirve la Presentación Ejecutiva Oficial de FERROSTATS."""
    pres_file = ASSETS_DIR / "presentacion_ejecutiva_ferrostats.html"
    if pres_file.exists():
        return FileResponse(str(pres_file), headers=NO_CACHE_HEADERS)
    return FileResponse(str(STATIC_DIR / "index.html"), headers=NO_CACHE_HEADERS)

@app.get("/health", tags=["Salud del Servicio"])
def health_check():
    """Endpoint de comprobación de salud para Cloud Run."""
    return {
        "status": "HEALTHY",
        "platform": APP_NAME,
        "version": APP_VERSION,
        "author": AUTHOR,
        "cloud_tier": "Google Cloud Run Serverless (Free Tier $0.00 USD)"
    }

