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
    Application Lifespan Cycle:
    On Cold Start (in Google Cloud Run or local development):
    1. Initializes OLTP transactional tables and local OLAP analytical tables.
    2. Loads master catalogs from CSV seeds if empty.
    3. Deterministically generates 180 historical sales transactions if empty.
    4. Compiles local analytical Star Schema (Data Marts and Daily Facts) and DQ assertions.
    5. Cloud Medallion Lakehouse operates via Google Dataform & BigQuery ($0.00 USD Free Tier).
    """
    print(f"[*] Starting {APP_NAME} v{APP_VERSION} (Lead Architect: {AUTHOR})...")
    init_db()
    load_csv_seeds()
    generate_historical_sales_if_empty()
    run_local_etl_if_empty()
    print("[+] Initialization complete. Platform ready to serve production traffic.")
    yield
    print("[-] Shutting down FERROSTATS service.")

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

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Routers
app.include_router(inventory_router)
app.include_router(pos_router)
app.include_router(analytics_router)

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"

# Mount Static Assets
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
    """Serves the Managerial Portal (Warehouse Control & Business Intelligence)."""
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file), headers=NO_CACHE_HEADERS)
    return {
        "message": "Welcome to FERROSTATS API",
        "docs": "/docs"
    }

@app.get("/pos", include_in_schema=False)
def serve_pos():
    """Serves the Dedicated Point of Sale (POS) Cashier Terminal."""
    pos_file = STATIC_DIR / "pos.html"
    if pos_file.exists():
        return FileResponse(str(pos_file), headers=NO_CACHE_HEADERS)
    return FileResponse(str(STATIC_DIR / "index.html"), headers=NO_CACHE_HEADERS)

@app.get("/bodega", include_in_schema=False)
def serve_bodega():
    """Direct route alias for the warehouse control view."""
    return FileResponse(str(STATIC_DIR / "index.html"), headers=NO_CACHE_HEADERS)

@app.get("/presentacion", include_in_schema=False)
def serve_presentacion():
    """Serves the interactive Executive Presentation Deck."""
    pres_file = ASSETS_DIR / "presentacion_ejecutiva_ferrostats.html"
    if pres_file.exists():
        return FileResponse(str(pres_file), headers=NO_CACHE_HEADERS)
    return FileResponse(str(STATIC_DIR / "index.html"), headers=NO_CACHE_HEADERS)

@app.get("/health", tags=["Service Health"])
def health_check():
    """Health check endpoint for Cloud Run and container orchestration probes."""
    return {
        "status": "HEALTHY",
        "platform": APP_NAME,
        "version": APP_VERSION,
        "author": AUTHOR,
        "cloud_tier": "Google Cloud Run Serverless (Free Tier $0.00 USD)"
    }
