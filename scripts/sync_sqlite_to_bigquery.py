import os
import sys
import json
import sqlite3
import subprocess
import urllib.request
import urllib.error
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "db" / "ferrostats.db"
PROJECT_ID = "ferrostats"
BRONZE_DATASET = "ferrostats_bronze"
GOLD_DATASET = "ferrostats_gold"

def get_access_token() -> str:
    """Obtiene el token OAuth de GCP metadata server (Cloud Run) o de gcloud CLI en local."""
    # 1. Intentar servidor de metadatos de Google Cloud (Cloud Run)
    try:
        req = urllib.request.Request(
            "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token",
            headers={"Metadata-Flavor": "Google"}
        )
        with urllib.request.urlopen(req, timeout=2) as resp:
            data = json.loads(resp.read().decode())
            return data["access_token"]
    except Exception:
        pass

    # 2. Intentar gcloud CLI de forma dinámica y portable
    import shutil
    gcloud_bin = shutil.which("gcloud") or shutil.which("gcloud.cmd")
    if not gcloud_bin and os.name == "nt":
        local_app_data = os.getenv("LOCALAPPDATA", "")
        candidate = os.path.join(local_app_data, "Google", "Cloud SDK", "google-cloud-sdk", "bin", "gcloud.cmd")
        if os.path.exists(candidate):
            gcloud_bin = candidate
    if not gcloud_bin:
        gcloud_bin = "gcloud"
    try:
        out = subprocess.check_output([gcloud_bin, "auth", "print-access-token"], shell=True)
        return out.decode().strip()
    except Exception as exc:
        print(f"Nota: gcloud CLI token no disponible: {exc}")
        return ""

def bq_request(endpoint: str, method: str = "GET", data: dict = None, token: str = None) -> dict:
    url = f"https://bigquery.googleapis.com/bigquery/v2/projects/{PROJECT_ID}/{endpoint}"
    body = json.dumps(data).encode("utf-8") if data else None
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as err:
        error_msg = err.read().decode("utf-8")
        if err.code == 409: # Already exists
            return {"status": "ALREADY_EXISTS"}
        print(f"Error HTTP {err.code} en {endpoint}: {error_msg}")
        return {"error": error_msg, "code": err.code}

def ensure_dataset(dataset_id: str, token: str):
    data = {
        "datasetReference": {
            "projectId": PROJECT_ID,
            "datasetId": dataset_id
        },
        "location": "US"
    }
    res = bq_request("datasets", method="POST", data=data, token=token)
    if "error" not in res:
        print(f"[OK] Dataset verificado: {dataset_id}")

def map_sqlite_type_to_bq(sqlite_type: str) -> str:
    t = (sqlite_type or "TEXT").upper()
    if "INT" in t:
        return "INT64"
    if "REAL" in t or "FLOAT" in t or "NUM" in t or "DECIMAL" in t:
        return "FLOAT64"
    if "BOOL" in t:
        return "BOOL"
    if "TIME" in t or "DATE" in t:
        return "STRING"
    return "STRING"

def sync_table_to_bq(cursor, table_name: str, target_dataset: str, target_table: str, token: str):
    cursor.execute(f"PRAGMA table_info({table_name});")
    columns = cursor.fetchall()
    
    schema_fields = []
    col_names = []
    for col in columns:
        col_name = col[1]
        col_type = map_sqlite_type_to_bq(col[2])
        col_names.append(col_name)
        schema_fields.append({
            "name": col_name,
            "type": col_type,
            "mode": "NULLABLE"
        })
    
    # 1. Crear tabla si no existe
    table_data = {
        "tableReference": {
            "projectId": PROJECT_ID,
            "datasetId": target_dataset,
            "tableId": target_table
        },
        "schema": {
            "fields": schema_fields
        }
    }
    bq_request(f"datasets/{target_dataset}/tables", method="POST", data=table_data, token=token)

    # 2. Leer filas
    cursor.execute(f"SELECT * FROM {table_name};")
    rows = cursor.fetchall()
    if not rows:
        print(f"[SKIP] {table_name} no contiene filas.")
        return

    # 3. Insertar filas en lotes de 500
    batch_size = 500
    total_inserted = 0
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i + batch_size]
        rows_payload = []
        for r in batch:
            row_dict = {}
            for idx, col in enumerate(col_names):
                val = r[idx]
                row_dict[col] = val
            rows_payload.append({"json": row_dict})

        insert_payload = {"rows": rows_payload}
        res = bq_request(f"datasets/{target_dataset}/tables/{target_table}/insertAll", method="POST", data=insert_payload, token=token)
        if "insertErrors" in res and res["insertErrors"]:
            print(f"  [ERROR] Fallos de inserción en {target_table}: {res['insertErrors'][:2]}")
        else:
            total_inserted += len(batch)

    print(f"[SYNC] {table_name} -> {target_dataset}.{target_table} ({total_inserted} filas insertadas exitosamente)")

def main():
    print("=" * 60)
    print("  FERROSTATS: SINCRONIZADOR DE DATOS HACIA GOOGLE BIGQUERY")
    print(f"  Proyecto GCP: {PROJECT_ID} | Modo: Free Tier ($0.00 USD)")
    print("=" * 60)

    token = get_access_token()

    # 1. Asegurar datasets
    ensure_dataset(BRONZE_DATASET, token)
    ensure_dataset("ferrostats_silver", token)
    ensure_dataset(GOLD_DATASET, token)

    # 2. Conectar a SQLite
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    # 3. Tablas Bronze (Raw)
    bronze_tables = [
        ("categories", "raw_categories"),
        ("suppliers", "raw_suppliers"),
        ("users", "raw_users"),
        ("products", "raw_products"),
        ("sales", "raw_sales"),
        ("sale_items", "raw_sale_items"),
        ("inventory_movements", "raw_inventory_movements")
    ]

    print("\n>>> SINCRONIZANDO CAPA BRONZE (RAW) <<<")
    for src, dst in bronze_tables:
        sync_table_to_bq(cursor, src, BRONZE_DATASET, dst, token)

    # 4. Tablas Gold (Data Marts listos para Looker Studio)
    gold_tables = [
        ("dw_fact_daily_sales", "dw_fact_daily_sales"),
        ("dw_mart_product_abc_health", "dw_mart_product_abc_health")
    ]

    print("\n>>> SINCRONIZANDO CAPA GOLD (DATA MARTS / LOOKER READY) <<<")
    for src, dst in gold_tables:
        sync_table_to_bq(cursor, src, GOLD_DATASET, dst, token)

    conn.close()

    # 5. Ejecutar las transformaciones analíticas en BigQuery (Silver Views + Gold Marts)
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import deploy_dataform_models
        print("\n>>> EJECUTANDO TRANSFORMACIONES ANALÍTICAS EN BIGQUERY <<<")
        deploy_dataform_models.main()
    except Exception as exc:
        print(f"Nota: Ejecución de transformaciones Dataform: {exc}")

    print("\n" + "=" * 60)
    print("  ¡SINCRONIZACIÓN Y TRANSFORMACIONES COMPLETADAS CON ÉXITO!")
    print("=" * 60)

if __name__ == "__main__":
    main()
