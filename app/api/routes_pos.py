import datetime
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.db.connection import get_db_connection
from app.api.auth_rbac import require_role
from app.etl.bigquery_sync import stream_sale_to_bronze

router = APIRouter(prefix="/api/v1/pos", tags=["Punto de Venta POS"])

class CartItemRequest(BaseModel):
    product_id: int
    quantity: int = Field(..., gt=0, description="Cantidad solicitada (debe ser > 0)")

class CheckoutRequest(BaseModel):
    transaction_uuid: str = Field(..., description="UUID único de transacción para idempotencia")
    user_id: int = Field(default=3, description="ID del cajero o administrador")
    customer_type: str = Field(
        default="CONSUMIDOR_FINAL",
        description="CONSUMIDOR_FINAL, CONTRATISTA o TALLER_INDUSTRIAL"
    )
    payment_method: str = Field(
        default="EFECTIVO",
        description="EFECTIVO, TRANSFERENCIA_QR o TARJETA"
    )
    items: List[CartItemRequest] = Field(..., min_length=1, description="Lista de artículos a cobrar")

@router.post("/checkout", status_code=status.HTTP_201_CREATED)
def pos_checkout(
    payload: CheckoutRequest,
    role: str = Depends(require_role("ADMIN", "CAJERO"))
) -> Dict[str, Any]:
    """
    Ejecuta el checkout atómico de punto de venta bajo garantías estrictas ACID:
    - BEGIN IMMEDIATE TRANSACTION para bloqueo exclusivo de escritura.
    - Verificación de idempotencia por transaction_uuid.
    - Verificación preventiva de stock con ROLLBACK inmediato (HTTP 409 Conflict) si no alcanza.
    - Descuento atómico de existencias con cláusula de guarda WHERE current_stock >= :qty.
    - Inserción de venta, detalle de ítems y bitácora de auditoría.
    - Disparo de refresco incremental del Pipeline ETL tras el COMMIT.
    """
    if payload.customer_type not in ("CONSUMIDOR_FINAL", "CONTRATISTA", "TALLER_INDUSTRIAL"):
        raise HTTPException(status_code=400, detail="customer_type no válido")
    if payload.payment_method not in ("EFECTIVO", "TRANSFERENCIA_QR", "TARJETA"):
        raise HTTPException(status_code=400, detail="payment_method no válido")

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("BEGIN IMMEDIATE TRANSACTION;")

        # 1. Verificación de Idempotencia por transaction_uuid
        cursor.execute("SELECT sale_id FROM sales WHERE transaction_uuid = ?;", (payload.transaction_uuid,))
        existing_sale = cursor.fetchone()
        if existing_sale:
            conn.execute("ROLLBACK;")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Transacción duplicada: el UUID '{payload.transaction_uuid}' ya fue procesado previamente en la venta #{existing_sale['sale_id']}."
            )

        # 2. Verificación de Stock para cada artículo del carrito
        items_processed = []
        stock_alerts = []
        sale_total_amount = 0.0
        sale_total_cost = 0.0
        now_ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        for item in payload.items:
            cursor.execute(
                """
                SELECT product_id, sku, product_name, unit_cost_usd, unit_price_usd, current_stock, min_stock
                FROM products
                WHERE product_id = ?;
                """,
                (item.product_id,)
            )
            prod = cursor.fetchone()
            if not prod:
                conn.execute("ROLLBACK;")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Producto con ID {item.product_id} no existe en el catálogo."
                )

            current_stock = prod["current_stock"]
            requested_qty = item.quantity

            if current_stock < requested_qty:
                conn.execute("ROLLBACK;")
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        f"Stock insuficiente para {prod['sku']} ({prod['product_name']}): "
                        f"disponible en pasillo: {current_stock} uds, solicitado en carrito: {requested_qty} uds."
                    )
                )

            # 3. Descuento atómico con cláusula de guarda
            cursor.execute(
                """
                UPDATE products
                SET current_stock = current_stock - ?,
                    updated_at = ?
                WHERE product_id = ?
                  AND current_stock >= ?;
                """,
                (requested_qty, now_ts, item.product_id, requested_qty)
            )

            if cursor.rowcount == 0:
                conn.execute("ROLLBACK;")
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Condición de carrera detectada para {prod['sku']}. Venta abortada por seguridad ACID."
                )

            stock_after = current_stock - requested_qty
            subtotal = round(requested_qty * prod["unit_price_usd"], 2)
            item_cost = round(requested_qty * prod["unit_cost_usd"], 2)

            sale_total_amount += subtotal
            sale_total_cost += item_cost

            items_processed.append({
                "product_id": prod["product_id"],
                "sku": prod["sku"],
                "product_name": prod["product_name"],
                "quantity": requested_qty,
                "unit_price_usd": prod["unit_price_usd"],
                "unit_cost_usd": prod["unit_cost_usd"],
                "subtotal_usd": subtotal,
                "stock_before": current_stock,
                "stock_after": stock_after
            })

            # Detectar si entró en zona de riesgo o quiebre de stock
            if stock_after <= prod["min_stock"]:
                stock_alerts.append({
                    "sku": prod["sku"],
                    "product_name": prod["product_name"],
                    "stock_left": stock_after,
                    "min_stock": prod["min_stock"],
                    "status": "AGOTADO" if stock_after == 0 else "BAJO_STOCK"
                })

        sale_total_amount = round(sale_total_amount, 2)
        sale_total_cost = round(sale_total_cost, 2)
        gross_profit = round(sale_total_amount - sale_total_cost, 2)

        # 4. Insertar encabezado de venta
        cursor.execute(
            """
            INSERT INTO sales (
                transaction_uuid, sale_timestamp, user_id, customer_type,
                payment_method, total_cost_usd, total_amount_usd, gross_profit_usd
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                payload.transaction_uuid,
                now_ts,
                payload.user_id,
                payload.customer_type,
                payload.payment_method,
                sale_total_cost,
                sale_total_amount,
                gross_profit
            )
        )
        sale_id = cursor.lastrowid

        # 5. Insertar renglones de venta y movimientos de inventario
        for item in items_processed:
            cursor.execute(
                """
                INSERT INTO sale_items (
                    sale_id, product_id, quantity, unit_cost_snapshot_usd,
                    unit_price_snapshot_usd, subtotal_usd
                )
                VALUES (?, ?, ?, ?, ?, ?);
                """,
                (
                    sale_id,
                    item["product_id"],
                    item["quantity"],
                    item["unit_cost_usd"],
                    item["unit_price_usd"],
                    item["subtotal_usd"]
                )
            )

            cursor.execute(
                """
                INSERT INTO inventory_movements (
                    movement_timestamp, product_id, user_id, movement_type,
                    quantity_delta, stock_before, stock_after, reference_note
                )
                VALUES (?, ?, ?, 'VENTA_POS', ?, ?, ?, ?);
                """,
                (
                    now_ts,
                    item["product_id"],
                    payload.user_id,
                    -item["quantity"],
                    item["stock_before"],
                    item["stock_after"],
                    f"Venta POS Ticket #{sale_id} (UUID: {payload.transaction_uuid[:18]})"
                )
            )

        conn.execute("COMMIT;")

        # 6. Ingesta continua hacia la capa Bronze de BigQuery (Dataform gestiona el ELT)
        stream_sale_to_bronze(
            sale_id=sale_id,
            transaction_uuid=payload.transaction_uuid,
            sale_timestamp=now_ts,
            user_id=payload.user_id,
            customer_type=payload.customer_type,
            payment_method=payload.payment_method,
            total_cost_usd=sale_total_cost,
            total_amount_usd=sale_total_amount,
            gross_profit_usd=gross_profit,
            items=items_processed
        )

        # 7. Obtener nombre del cajero para el ticket
        cursor.execute("SELECT full_name FROM users WHERE user_id = ?;", (payload.user_id,))
        user_row = cursor.fetchone()
        cashier_name = user_row["full_name"] if user_row else f"Cajero #{payload.user_id}"

        subtotal_neto = round(sale_total_amount / 1.13, 2)
        iva_calc = round(sale_total_amount - subtotal_neto, 2)

        return {
            "status": "SUCCESS",
            "sale_id": sale_id,
            "transaction_uuid": payload.transaction_uuid,
            "sale_timestamp": now_ts,
            "timestamp": now_ts,
            "cashier_name": cashier_name,
            "customer_type": payload.customer_type,
            "payment_method": payload.payment_method,
            "items_count": len(items_processed),
            "items": items_processed,
            "items_breakdown": items_processed,
            "subtotal_usd": subtotal_neto,
            "iva_usd": iva_calc,
            "total_cost_usd": sale_total_cost,
            "total_amount_usd": sale_total_amount,
            "gross_profit_usd": gross_profit,
            "gross_margin_pct": round((gross_profit / sale_total_amount * 100.0), 2) if sale_total_amount > 0 else 0.0,
            "stock_alerts_triggered": stock_alerts
        }

    except HTTPException:
        raise
    except Exception as exc:
        conn.execute("ROLLBACK;")
        raise HTTPException(status_code=500, detail=f"Fallo en transacción de venta: {str(exc)}")
    finally:
        conn.close()
