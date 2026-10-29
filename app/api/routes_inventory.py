import datetime
import sqlite3
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.db.connection import get_db_connection
from app.api.auth_rbac import require_role
from app.etl.bigquery_sync import stream_movement_to_bronze, stream_product_to_bronze

router = APIRouter(prefix="/api/v1", tags=["Inventory & Catalog"])

MOVEMENT_TYPE_TO_DB = {
    "SUPPLIER_RESTOCK": "INGRESO_PROVEEDOR",
    "INGRESO_PROVEEDOR": "INGRESO_PROVEEDOR",
    "AUDIT_ADJUSTMENT": "AJUSTE_AUDITORIA",
    "AJUSTE_AUDITORIA": "AJUSTE_AUDITORIA",
    "POS_SALE": "VENTA_POS",
    "VENTA_POS": "VENTA_POS"
}

MOVEMENT_TYPE_TO_EN = {
    "INGRESO_PROVEEDOR": "SUPPLIER_RESTOCK",
    "SUPPLIER_RESTOCK": "SUPPLIER_RESTOCK",
    "AJUSTE_AUDITORIA": "AUDIT_ADJUSTMENT",
    "AUDIT_ADJUSTMENT": "AUDIT_ADJUSTMENT",
    "VENTA_POS": "POS_SALE",
    "POS_SALE": "POS_SALE"
}

class InventoryAdjustmentRequest(BaseModel):
    product_id: int
    user_id: int = Field(default=4, description="User ID performing the inventory adjustment")
    movement_type: str = Field(..., description="SUPPLIER_RESTOCK or AUDIT_ADJUSTMENT")
    quantity_delta: int = Field(..., description="Stock adjustment delta (positive or negative)")
    reference_note: str = Field(default="Aisle inventory adjustment")

class ProductCreateUpdateRequest(BaseModel):
    sku: str
    product_name: str
    category_id: int
    supplier_id: int
    unit_measure: str
    unit_cost_usd: float = Field(..., gt=0)
    unit_price_usd: float = Field(..., gt=0)
    current_stock: int = Field(..., ge=0)
    min_stock: int = Field(..., ge=0)
    aisle_location: str

@router.get("/products")
def list_products(
    q: Optional[str] = Query(None, description="Fast search by SKU, product name, or aisle location"),
    category_id: Optional[int] = Query(None, description="Filter by category ID"),
    stock_status: Optional[str] = Query(None, description="OPTIMAL / OPTIMO, LOW_STOCK / BAJO_STOCK, OUT_OF_STOCK / AGOTADO"),
    abc_class: Optional[str] = Query(None, description="A, B, C"),
    role: str = Depends(require_role("ADMIN", "CASHIER", "WAREHOUSE"))
) -> List[Dict[str, Any]]:
    """
    Retrieves the master SKU catalog enriched with dimensional analytics:
    stock status, Pareto ABC classification, physical warehouse location,
    burn rate, days of inventory (DOI), and replenishment recommendations.
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        query = """
        SELECT
            p.product_id,
            p.sku,
            p.product_name,
            p.category_id,
            c.category_code,
            c.category_name,
            p.supplier_id,
            s.supplier_name,
            s.contact_phone,
            s.lead_time_days,
            p.unit_measure,
            p.unit_cost_usd,
            p.unit_price_usd,
            p.current_stock,
            p.min_stock,
            p.aisle_location,
            p.updated_at,
            COALESCE(m.stock_status, CASE
                WHEN p.current_stock = 0 THEN 'OUT_OF_STOCK'
                WHEN p.current_stock <= p.min_stock THEN 'LOW_STOCK'
                ELSE 'OPTIMAL'
            END) AS stock_status,
            COALESCE(m.abc_class, 'C') AS abc_class,
            COALESCE(m.daily_burn_rate, 0.0) AS daily_burn_rate,
            COALESCE(m.days_of_inventory_left, 999.0) AS days_of_inventory_left,
            COALESCE(m.recommended_reorder_qty, 0) AS recommended_reorder_qty
        FROM products p
        JOIN categories c ON p.category_id = c.category_id
        JOIN suppliers s ON p.supplier_id = s.supplier_id
        LEFT JOIN dw_mart_product_abc_health m ON p.product_id = m.product_id
        WHERE 1=1
        """
        params = []

        if q:
            query += " AND (p.sku LIKE ? OR p.product_name LIKE ? OR p.aisle_location LIKE ?)"
            term = f"%{q.strip()}%"
            params.extend([term, term, term])

        if category_id:
            query += " AND p.category_id = ?"
            params.append(category_id)

        if stock_status:
            stat_upper = stock_status.upper().strip()
            # Support both English and legacy Spanish status filters
            if stat_upper in ("AGOTADO", "OUT_OF_STOCK"):
                query += " AND (stock_status IN ('AGOTADO', 'OUT_OF_STOCK'))"
            elif stat_upper in ("BAJO_STOCK", "LOW_STOCK"):
                query += " AND (stock_status IN ('BAJO_STOCK', 'LOW_STOCK'))"
            elif stat_upper in ("OPTIMO", "OPTIMAL"):
                query += " AND (stock_status IN ('OPTIMO', 'OPTIMAL'))"
            else:
                query += " AND stock_status = ?"
                params.append(stat_upper)

        if abc_class:
            query += " AND abc_class = ?"
            params.append(abc_class.upper().strip())

        query += " ORDER BY p.aisle_location ASC, p.product_id ASC"

        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

@router.post("/inventory/adjust")
def adjust_inventory(
    payload: InventoryAdjustmentRequest,
    role: str = Depends(require_role("ADMIN", "WAREHOUSE"))
) -> Dict[str, Any]:
    """
    Records a supplier restock arrival or physical warehouse aisle audit adjustment.
    Enforces non-negative inventory invariants and updates transactional & analytical records.
    """
    raw_type = payload.movement_type.upper().strip()
    db_type = MOVEMENT_TYPE_TO_DB.get(raw_type)
    if not db_type or db_type not in ("INGRESO_PROVEEDOR", "AJUSTE_AUDITORIA"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid movement_type '{payload.movement_type}'. Allowed: SUPPLIER_RESTOCK (INGRESO_PROVEEDOR), AUDIT_ADJUSTMENT (AJUSTE_AUDITORIA)"
        )
    norm_en_type = MOVEMENT_TYPE_TO_EN.get(db_type, "AUDIT_ADJUSTMENT")

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("BEGIN IMMEDIATE TRANSACTION;")

        cursor.execute("SELECT * FROM products WHERE product_id = ?;", (payload.product_id,))
        prod = cursor.fetchone()
        if not prod:
            conn.execute("ROLLBACK;")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product with ID {payload.product_id} not found."
            )

        stock_before = prod["current_stock"]
        stock_after = stock_before + payload.quantity_delta

        if stock_after < 0:
            conn.execute("ROLLBACK;")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid adjustment: inventory stock cannot be negative ({stock_before} + {payload.quantity_delta} = {stock_after})"
            )

        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 1. Update stock in master catalog
        cursor.execute(
            """
            UPDATE products
            SET current_stock = ?, updated_at = ?
            WHERE product_id = ?
            """,
            (stock_after, now_str, payload.product_id)
        )

        # 2. Record in immutable audit log
        cursor.execute(
            """
            INSERT INTO inventory_movements (
                movement_timestamp, product_id, user_id, movement_type,
                quantity_delta, stock_before, stock_after, reference_note
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                now_str,
                payload.product_id,
                payload.user_id,
                db_type,
                payload.quantity_delta,
                stock_before,
                stock_after,
                payload.reference_note
            )
        )

        conn.execute("COMMIT;")
        
        # 3. Stream event to BigQuery Bronze
        stream_movement_to_bronze(
            product_id=payload.product_id,
            user_id=payload.user_id,
            movement_type=norm_en_type,
            quantity_delta=payload.quantity_delta,
            stock_before=stock_before,
            stock_after=stock_after,
            reference_note=payload.reference_note,
            movement_timestamp=now_str
        )

        return {
            "status": "SUCCESS",
            "message": "Inventory adjustment applied successfully",
            "product_id": payload.product_id,
            "sku": prod["sku"],
            "product_name": prod["product_name"],
            "movement_type": norm_en_type,
            "quantity_delta": payload.quantity_delta,
            "stock_before": stock_before,
            "stock_after": stock_after
        }
    except HTTPException:
        raise
    except Exception as exc:
        conn.execute("ROLLBACK;")
        raise HTTPException(status_code=500, detail=f"Inventory adjustment failed: {str(exc)}")
    finally:
        conn.close()

@router.post("/products")
def create_product(
    payload: ProductCreateUpdateRequest,
    role: str = Depends(require_role("ADMIN"))
) -> Dict[str, Any]:
    """Creates a new SKU in master catalog (Exclusive to ADMIN)."""
    if payload.unit_price_usd < payload.unit_cost_usd:
        raise HTTPException(status_code=400, detail="Unit selling price must be >= unit purchase cost")

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            """
            INSERT INTO products (
                sku, product_name, category_id, supplier_id, unit_measure,
                unit_cost_usd, unit_price_usd, current_stock, min_stock, aisle_location, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload.sku.strip(), payload.product_name.strip(), payload.category_id,
                payload.supplier_id, payload.unit_measure, payload.unit_cost_usd,
                payload.unit_price_usd, payload.current_stock, payload.min_stock,
                payload.aisle_location, now_str
            )
        )
        new_id = cursor.lastrowid
        conn.commit()
        stream_product_to_bronze({
            "product_id": new_id,
            "sku": payload.sku.strip(),
            "product_name": payload.product_name.strip(),
            "category_id": payload.category_id,
            "supplier_id": payload.supplier_id,
            "unit_measure": payload.unit_measure,
            "unit_cost_usd": payload.unit_cost_usd,
            "unit_price_usd": payload.unit_price_usd,
            "current_stock": payload.current_stock,
            "min_stock": payload.min_stock,
            "aisle_location": payload.aisle_location,
            "updated_at": now_str
        })
        return {"status": "SUCCESS", "product_id": new_id, "sku": payload.sku}
    except sqlite3.IntegrityError as ie:
        raise HTTPException(status_code=400, detail=f"Database integrity violation: {str(ie)}")
    finally:
        conn.close()
