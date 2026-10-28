import os
import logging
from typing import Dict, Any, List, Optional
from app.config import GCP_PROJECT_ID, ENABLE_BIGQUERY_SYNC

logger = logging.getLogger("ferrostats.bigquery_sync")

BRONZE_DATASET = "ferrostats_bronze"
SILVER_DATASET = "ferrostats_silver"
GOLD_DATASET = "ferrostats_gold"

def _get_bq_client():
    """Obtiene el cliente de BigQuery si las credenciales o el entorno de GCP están activos."""
    try:
        from google.cloud import bigquery
        return bigquery.Client(project=GCP_PROJECT_ID)
    except Exception as exc:
        logger.debug("BigQuery client no disponible en entorno local sin credenciales: %s", exc)
        return None

def stream_sale_to_bronze(
    sale_id: int,
    transaction_uuid: str,
    sale_timestamp: str,
    user_id: int,
    customer_type: str,
    payment_method: str,
    total_cost_usd: float,
    total_amount_usd: float,
    gross_profit_usd: float,
    items: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Ingesta en tiempo real hacia la capa Bronze de BigQuery (raw_sales y raw_sale_items).
    Las transformaciones analíticas (Pareto ABC, Hechos) son calculadas por Google Dataform.
    """
    client = _get_bq_client()
    if not client:
        return {"status": "LOCAL_FALLBACK", "message": "BigQuery client inactivo o local sin credenciales"}

    try:
        # 1. Ingesta a raw_sales
        sale_row = [{
            "sale_id": int(sale_id),
            "transaction_uuid": str(transaction_uuid),
            "sale_timestamp": str(sale_timestamp),
            "user_id": int(user_id),
            "customer_type": str(customer_type),
            "payment_method": str(payment_method),
            "total_cost_usd": float(total_cost_usd),
            "total_amount_usd": float(total_amount_usd),
            "gross_profit_usd": float(gross_profit_usd)
        }]
        err_sales = client.insert_rows_json(f"{GCP_PROJECT_ID}.{BRONZE_DATASET}.raw_sales", sale_row)
        if err_sales:
            logger.warning("Error insertando en raw_sales: %s", err_sales)

        # 2. Ingesta a raw_sale_items
        item_rows = []
        for item in items:
            item_rows.append({
                "sale_id": int(sale_id),
                "product_id": int(item["product_id"]),
                "quantity": int(item["quantity"]),
                "unit_cost_snapshot_usd": float(item["unit_cost_usd"]),
                "unit_price_snapshot_usd": float(item["unit_price_usd"]),
                "subtotal_usd": float(item["subtotal_usd"])
            })
        
        if item_rows:
            err_items = client.insert_rows_json(f"{GCP_PROJECT_ID}.{BRONZE_DATASET}.raw_sale_items", item_rows)
            if err_items:
                logger.warning("Error insertando en raw_sale_items: %s", err_items)

        return {"status": "SUCCESS", "sale_id": sale_id, "items_streamed": len(item_rows)}
    except Exception as exc:
        logger.info("Fallo seguro en streaming BigQuery (continúa sin interrumpir POS): %s", exc)
        return {"status": "FALLBACK", "error": str(exc)}

def stream_movement_to_bronze(
    product_id: int,
    user_id: int,
    movement_type: str,
    quantity_delta: int,
    stock_before: int,
    stock_after: int,
    reference_note: str,
    movement_timestamp: str
) -> Dict[str, Any]:
    """Ingesta un movimiento de inventario a la capa Bronze (raw_inventory_movements)."""
    client = _get_bq_client()
    if not client:
        return {"status": "LOCAL_FALLBACK"}

    try:
        row = [{
            "movement_timestamp": str(movement_timestamp),
            "product_id": int(product_id),
            "user_id": int(user_id),
            "movement_type": str(movement_type),
            "quantity_delta": int(quantity_delta),
            "stock_before": int(stock_before),
            "stock_after": int(stock_after),
            "reference_note": str(reference_note)
        }]
        errs = client.insert_rows_json(f"{GCP_PROJECT_ID}.{BRONZE_DATASET}.raw_inventory_movements", row)
        if errs:
            logger.warning("Error insertando en raw_inventory_movements: %s", errs)
        return {"status": "SUCCESS"}
    except Exception as exc:
        logger.info("Fallo seguro en streaming movimiento BigQuery: %s", exc)
        return {"status": "FALLBACK", "error": str(exc)}

def stream_product_to_bronze(product_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Ingesta o actualiza un producto en la capa Bronze (raw_products)."""
    client = _get_bq_client()
    if not client:
        return {"status": "LOCAL_FALLBACK"}

    try:
        row = [{
            "product_id": int(product_dict["product_id"]),
            "sku": str(product_dict["sku"]),
            "product_name": str(product_dict["product_name"]),
            "category_id": int(product_dict["category_id"]),
            "supplier_id": int(product_dict["supplier_id"]),
            "unit_measure": str(product_dict["unit_measure"]),
            "unit_cost_usd": float(product_dict["unit_cost_usd"]),
            "unit_price_usd": float(product_dict["unit_price_usd"]),
            "current_stock": int(product_dict["current_stock"]),
            "min_stock": int(product_dict["min_stock"]),
            "aisle_location": str(product_dict["aisle_location"]),
            "updated_at": str(product_dict.get("updated_at", ""))
        }]
        errs = client.insert_rows_json(f"{GCP_PROJECT_ID}.{BRONZE_DATASET}.raw_products", row)
        if errs:
            logger.warning("Error insertando en raw_products: %s", errs)
        return {"status": "SUCCESS"}
    except Exception as exc:
        logger.info("Fallo seguro en streaming producto BigQuery: %s", exc)
        return {"status": "FALLBACK", "error": str(exc)}
