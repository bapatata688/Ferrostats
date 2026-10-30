import datetime
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.db.connection import get_db_connection
from app.api.auth_rbac import require_role
from app.etl.bigquery_sync import stream_sale_to_bronze

router = APIRouter(prefix="/api/v1/pos", tags=["Point-of-Sale (POS)"])

CUSTOMER_TYPE_TO_DB = {
    "FINAL_CONSUMER": "CONSUMIDOR_FINAL",
    "CONSUMIDOR_FINAL": "CONSUMIDOR_FINAL",
    "CONTRACTOR": "CONTRATISTA",
    "CONTRATISTA": "CONTRATISTA",
    "INDUSTRIAL_WORKSHOP": "TALLER_INDUSTRIAL",
    "TALLER_INDUSTRIAL": "TALLER_INDUSTRIAL"
}

PAYMENT_METHOD_TO_DB = {
    "CASH": "EFECTIVO",
    "EFECTIVO": "EFECTIVO",
    "QR_TRANSFER": "TRANSFERENCIA_QR",
    "TRANSFERENCIA_QR": "TRANSFERENCIA_QR",
    "CARD": "TARJETA",
    "TARJETA": "TARJETA"
}

class CartItemRequest(BaseModel):
    product_id: int
    quantity: int = Field(..., gt=0, description="Requested quantity (must be > 0)")

class CheckoutRequest(BaseModel):
    transaction_uuid: str = Field(..., description="Unique client transaction UUID for idempotency")
    user_id: int = Field(default=3, description="Cashier or administrator user ID")
    customer_type: str = Field(
        default="FINAL_CONSUMER",
        description="FINAL_CONSUMER, CONTRACTOR, or INDUSTRIAL_WORKSHOP"
    )
    payment_method: str = Field(
        default="CASH",
        description="CASH, QR_TRANSFER, or CARD"
    )
    items: List[CartItemRequest] = Field(..., min_length=1, description="List of items to purchase")

@router.post("/checkout", status_code=status.HTTP_201_CREATED)
def pos_checkout(
    payload: CheckoutRequest,
    role: str = Depends(require_role("ADMIN", "CASHIER"))
) -> Dict[str, Any]:
    """
    Executes an atomic point-of-sale checkout under strict ACID guarantees:
    - BEGIN IMMEDIATE TRANSACTION for exclusive database write locking.
    - Idempotency verification by transaction_uuid to prevent duplicate charges.
    - Preventive inventory check with instant ROLLBACK (HTTP 409 Conflict) on depletion.
    - Atomic stock decrement with SQL guard: WHERE current_stock >= :qty.
    - Sales receipt, item breakdown, and immutable audit log persistence.
    - Continuous streaming ingestion into Google BigQuery Bronze layer.
    """
    normalized_cust = CUSTOMER_TYPE_TO_DB.get(payload.customer_type.upper().strip())
    if not normalized_cust:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid customer_type '{payload.customer_type}'. Allowed: FINAL_CONSUMER, CONTRACTOR, INDUSTRIAL_WORKSHOP"
        )

    normalized_pay = PAYMENT_METHOD_TO_DB.get(payload.payment_method.upper().strip())
    if not normalized_pay:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid payment_method '{payload.payment_method}'. Allowed: CASH, QR_TRANSFER, CARD"
        )

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("BEGIN IMMEDIATE TRANSACTION;")

        # 1. Idempotency Check by transaction_uuid
        cursor.execute(
            """
            SELECT s.sale_id, s.transaction_uuid, s.sale_timestamp, s.user_id,
                   s.customer_type, s.payment_method, s.total_cost_usd,
                   s.total_amount_usd, s.gross_profit_usd, u.full_name AS cashier_name
            FROM sales s
            LEFT JOIN users u ON s.user_id = u.user_id
            WHERE s.transaction_uuid = ?;
            """,
            (payload.transaction_uuid,)
        )
        existing_sale = cursor.fetchone()
        if existing_sale:
            sale_id = existing_sale["sale_id"]
            cursor.execute(
                """
                SELECT si.sale_item_id, si.product_id, p.sku, p.product_name, si.quantity,
                       si.unit_price_snapshot_usd AS unit_price_usd,
                       si.unit_cost_snapshot_usd AS unit_cost_usd,
                       si.subtotal_usd
                FROM sale_items si
                JOIN products p ON si.product_id = p.product_id
                WHERE si.sale_id = ?;
                """,
                (sale_id,)
            )
            items_replayed = []
            for r in cursor.fetchall():
                items_replayed.append({
                    "sale_item_id": r["sale_item_id"],
                    "product_id": r["product_id"],
                    "sku": r["sku"],
                    "product_name": r["product_name"],
                    "quantity": r["quantity"],
                    "unit_price_usd": r["unit_price_usd"],
                    "unit_cost_usd": r["unit_cost_usd"],
                    "subtotal_usd": r["subtotal_usd"]
                })
            conn.execute("ROLLBACK;")

            sale_total_amount = float(existing_sale["total_amount_usd"])
            sale_total_cost = float(existing_sale["total_cost_usd"])
            gross_profit = float(existing_sale["gross_profit_usd"])
            subtotal_neto = round(sale_total_amount / 1.13, 2)
            iva_calc = round(sale_total_amount - subtotal_neto, 2)
            cashier_name = existing_sale["cashier_name"] or f"Cashier #{existing_sale['user_id']}"

            receipt_data = {
                "status": "SUCCESS",
                "sale_id": sale_id,
                "transaction_uuid": existing_sale["transaction_uuid"],
                "sale_timestamp": existing_sale["sale_timestamp"],
                "timestamp": existing_sale["sale_timestamp"],
                "cashier_name": cashier_name,
                "customer_type": existing_sale["customer_type"],
                "payment_method": existing_sale["payment_method"],
                "items_count": len(items_replayed),
                "items": items_replayed,
                "items_breakdown": items_replayed,
                "subtotal_usd": subtotal_neto,
                "iva_usd": iva_calc,
                "total_cost_usd": sale_total_cost,
                "total_amount_usd": sale_total_amount,
                "gross_profit_usd": gross_profit,
                "gross_margin_pct": round((gross_profit / sale_total_amount * 100.0), 2) if sale_total_amount > 0 else 0.0,
                "stock_alerts_triggered": []
            }
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content=receipt_data,
                headers={"Idempotent-Replay": "true"}
            )

        # 2. Stock Verification & Pre-flight Validation
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
                    detail=f"Product with ID {item.product_id} does not exist in catalog."
                )

            current_stock = prod["current_stock"]
            requested_qty = item.quantity

            if current_stock < requested_qty:
                conn.execute("ROLLBACK;")
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        f"Insufficient stock for {prod['sku']} ({prod['product_name']}): "
                        f"available in aisle: {current_stock} units, requested in cart: {requested_qty} units."
                    )
                )

            # 3. Guarded Atomic Stock Decrement
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
                    detail=f"Race condition detected for {prod['sku']}. Transaction rolled back by ACID guard."
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

            # Check stock risk / out-of-stock threshold
            if stock_after <= prod["min_stock"]:
                stock_alerts.append({
                    "sku": prod["sku"],
                    "product_name": prod["product_name"],
                    "stock_left": stock_after,
                    "min_stock": prod["min_stock"],
                    "status": "OUT_OF_STOCK" if stock_after == 0 else "LOW_STOCK"
                })

        sale_total_amount = round(sale_total_amount, 2)
        sale_total_cost = round(sale_total_cost, 2)
        gross_profit = round(sale_total_amount - sale_total_cost, 2)

        # 4. Insert Sale Header
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
                normalized_cust,
                normalized_pay,
                sale_total_cost,
                sale_total_amount,
                gross_profit
            )
        )
        sale_id = cursor.lastrowid

        # 5. Insert Sale Line Items & Inventory Movements Audit
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
            item["sale_item_id"] = cursor.lastrowid

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
                    f"POS Checkout Receipt #{sale_id} (UUID: {payload.transaction_uuid[:18]})"
                )
            )

        conn.execute("COMMIT;")

        # 6. Stream event to BigQuery Bronze (non-blocking)
        stream_sale_to_bronze(
            sale_id=sale_id,
            transaction_uuid=payload.transaction_uuid,
            sale_timestamp=now_ts,
            user_id=payload.user_id,
            customer_type=normalized_cust,
            payment_method=normalized_pay,
            total_cost_usd=sale_total_cost,
            total_amount_usd=sale_total_amount,
            gross_profit_usd=gross_profit,
            items=items_processed
        )

        # 7. Get Cashier Name
        cursor.execute("SELECT full_name FROM users WHERE user_id = ?;", (payload.user_id,))
        user_row = cursor.fetchone()
        cashier_name = user_row["full_name"] if user_row else f"Cashier #{payload.user_id}"

        subtotal_neto = round(sale_total_amount / 1.13, 2)
        iva_calc = round(sale_total_amount - subtotal_neto, 2)

        return {
            "status": "SUCCESS",
            "sale_id": sale_id,
            "transaction_uuid": payload.transaction_uuid,
            "sale_timestamp": now_ts,
            "timestamp": now_ts,
            "cashier_name": cashier_name,
            "customer_type": normalized_cust,
            "payment_method": normalized_pay,
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
        raise HTTPException(status_code=500, detail=f"Checkout transaction failed: {str(exc)}")
    finally:
        conn.close()
