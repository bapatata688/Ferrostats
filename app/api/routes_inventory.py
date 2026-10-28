import datetime
import sqlite3
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.db.connection import get_db_connection
from app.api.auth_rbac import require_role
from app.etl.bigquery_sync import stream_movement_to_bronze, stream_product_to_bronze

router = APIRouter(prefix="/api/v1", tags=["Inventario y Catálogo"])

class InventoryAdjustmentRequest(BaseModel):
    product_id: int
    user_id: int = Field(default=4, description="ID del usuario que realiza el ajuste")
    movement_type: str = Field(..., description="INGRESO_PROVEEDOR o AJUSTE_AUDITORIA")
    quantity_delta: int = Field(..., description="Cambio de inventario (positivo o negativo)")
    reference_note: str = Field(default="Ajuste de inventario en pasillo")

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
    q: Optional[str] = Query(None, description="Búsqueda rápida por SKU o nombre de producto"),
    category_id: Optional[int] = Query(None, description="Filtrar por ID de categoría"),
    stock_status: Optional[str] = Query(None, description="OPTIMO, BAJO_STOCK, AGOTADO"),
    abc_class: Optional[str] = Query(None, description="A, B, C"),
    role: str = Depends(require_role("ADMIN", "CAJERO", "BODEGUERO"))
) -> List[Dict[str, Any]]:
    """
    Consulta el catálogo maestro de artículos SKU enriquecido con datos dimensionales
    (estado de stock, clasificación ABC, ubicación física y recomendaciones de compra).
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
                WHEN p.current_stock = 0 THEN 'AGOTADO'
                WHEN p.current_stock <= p.min_stock THEN 'BAJO_STOCK'
                ELSE 'OPTIMO'
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
            query += " AND stock_status = ?"
            params.append(stock_status.upper().strip())

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
    role: str = Depends(require_role("ADMIN", "BODEGUERO"))
) -> Dict[str, Any]:
    """
    Registra una recepción de mercadería de proveedor o un ajuste físico de pasillo.
    Valida invariantes de no negatividad de stock y actualiza de inmediato el Mart analítico.
    """
    if payload.movement_type not in ("INGRESO_PROVEEDOR", "AJUSTE_AUDITORIA"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="movement_type debe ser INGRESO_PROVEEDOR o AJUSTE_AUDITORIA"
        )

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
                detail=f"Producto ID {payload.product_id} no encontrado"
            )

        stock_before = prod["current_stock"]
        stock_after = stock_before + payload.quantity_delta

        if stock_after < 0:
            conn.execute("ROLLBACK;")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ajuste inválido: el stock no puede ser negativo ({stock_before} + {payload.quantity_delta} = {stock_after})"
            )

        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 1. Actualizar stock en catálogo maestro
        cursor.execute(
            """
            UPDATE products
            SET current_stock = ?, updated_at = ?
            WHERE product_id = ?
            """,
            (stock_after, now_str, payload.product_id)
        )

        # 2. Registrar en bitácora inmutable de movimientos
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
                payload.movement_type,
                payload.quantity_delta,
                stock_before,
                stock_after,
                payload.reference_note
            )
        )

        conn.execute("COMMIT;")
        
        # 3. Ingesta continua a la capa Bronze de BigQuery (Dataform gestiona el ELT)
        stream_movement_to_bronze(
            product_id=payload.product_id,
            user_id=payload.user_id,
            movement_type=payload.movement_type,
            quantity_delta=payload.quantity_delta,
            stock_before=stock_before,
            stock_after=stock_after,
            reference_note=payload.reference_note,
            movement_timestamp=now_str
        )

        return {
            "status": "SUCCESS",
            "message": "Ajuste de inventario aplicado exitosamente",
            "product_id": payload.product_id,
            "sku": prod["sku"],
            "product_name": prod["product_name"],
            "movement_type": payload.movement_type,
            "quantity_delta": payload.quantity_delta,
            "stock_before": stock_before,
            "stock_after": stock_after
        }
    except HTTPException:
        raise
    except Exception as exc:
        conn.execute("ROLLBACK;")
        raise HTTPException(status_code=500, detail=f"Error en ajuste de inventario: {str(exc)}")
    finally:
        conn.close()

@router.post("/products")
def create_product(
    payload: ProductCreateUpdateRequest,
    role: str = Depends(require_role("ADMIN"))
) -> Dict[str, Any]:
    """Crea un nuevo SKU en el catálogo maestro (Exclusivo ADMIN)."""
    if payload.unit_price_usd < payload.unit_cost_usd:
        raise HTTPException(status_code=400, detail="El precio de venta debe ser >= al costo unitario")

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
        raise HTTPException(status_code=400, detail=f"Violación de integridad: {str(ie)}")
    finally:
        conn.close()
