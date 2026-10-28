import csv
import datetime
import random
import uuid
from typing import Dict, List, Any
from app.config import SEEDS_DIR, RANDOM_SEED, AUTHOR
from app.db.connection import get_db_connection, init_db
from app.etl.local_pipeline import run_local_etl_if_empty

def load_csv_seeds() -> None:
    """
    Carga los catálogos base desde los archivos CSV a las tablas maestras de SQLite.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 1. Categorías
        cat_file = SEEDS_DIR / "categories.csv"
        if cat_file.exists():
            with open(cat_file, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    cursor.execute(
                        """
                        INSERT OR REPLACE INTO categories (category_id, category_code, category_name, target_margin_pct)
                        VALUES (?, ?, ?, ?)
                        """,
                        (int(row["category_id"]), row["category_code"], row["category_name"], float(row["target_margin_pct"]))
                    )

        # 2. Proveedores
        sup_file = SEEDS_DIR / "suppliers.csv"
        if sup_file.exists():
            with open(sup_file, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    cursor.execute(
                        """
                        INSERT OR REPLACE INTO suppliers (supplier_id, supplier_name, contact_phone, lead_time_days, city)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (int(row["supplier_id"]), row["supplier_name"], row["contact_phone"], int(row["lead_time_days"]), row["city"])
                    )

        # 3. Usuarios
        user_file = SEEDS_DIR / "users.csv"
        if user_file.exists():
            with open(user_file, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    cursor.execute(
                        """
                        INSERT OR REPLACE INTO users (user_id, username, full_name, role, pin_hash, is_active)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (int(row["user_id"]), row["username"], row["full_name"], row["role"], row["pin_hash"], int(row["is_active"]))
                    )

        # 4. Productos SKU
        prod_file = SEEDS_DIR / "products_sku.csv"
        if prod_file.exists():
            with open(prod_file, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                now_iso = datetime.datetime(2026, 10, 21, 12, 0, 0).isoformat()
                for row in reader:
                    cursor.execute(
                        """
                        INSERT OR REPLACE INTO products (
                            product_id, sku, product_name, category_id, supplier_id,
                            unit_measure, unit_cost_usd, unit_price_usd, current_stock,
                            min_stock, aisle_location, updated_at
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            int(row["product_id"]),
                            row["sku"],
                            row["product_name"],
                            int(row["category_id"]),
                            int(row["supplier_id"]),
                            row["unit_measure"],
                            float(row["unit_cost_usd"]),
                            float(row["unit_price_usd"]),
                            int(row["current_stock"]),
                            int(row["min_stock"]),
                            row["aisle_location"],
                            now_iso
                        )
                    )
        conn.commit()
    finally:
        conn.close()

def generate_historical_sales_if_empty() -> None:
    """
    Genera de forma determinista (seed: RANDOM_SEED) 180 ventas históricas
    distribuidas en los últimos 30 días si la tabla 'sales' está vacía.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT COUNT(*) as total FROM sales;")
        count = cursor.fetchone()["total"]
        if count > 0:
            return  # Ya existen ventas históricas

        print("--> Generando 180 transacciones históricas deterministas (30 días)...")
        # Semilla determinista de números pseudo-aleatorios
        random.seed(RANDOM_SEED)

        # Leer productos cargados
        cursor.execute("SELECT * FROM products ORDER BY product_id;")
        products = [dict(row) for row in cursor.fetchall()]
        prod_by_id = {p["product_id"]: p for p in products}

        # Separar en grupos de probabilidad Pareto para las ventas
        skus_a = ["MC-001", "MC-002", "HE-003", "FP-001", "TF-001", "PQ-001", "HE-001"]
        skus_b = ["HM-001", "HM-002", "HE-002", "FP-002", "FP-003", "MC-004", "PQ-002", "PQ-003"]
        
        prods_a = [p for p in products if p["sku"] in skus_a]
        prods_b = [p for p in products if p["sku"] in skus_b]
        prods_c = [p for p in products if p["sku"] not in skus_a and p["sku"] not in skus_b]

        customer_types = ["CONSUMIDOR_FINAL", "CONTRATISTA", "TALLER_INDUSTRIAL"]
        payment_methods = ["EFECTIVO", "TRANSFERENCIA_QR", "TARJETA"]
        cashier_user_ids = [3, 1]  # cmartinez (Cajero principal) o descobar (Admin)

        base_date = datetime.date(2026, 9, 21)
        total_days = 30
        total_sales = 180

        # Distribuir 180 ventas en los 30 días (~6 ventas diarias)
        sale_counter = 1
        for day_offset in range(total_days):
            day_date = base_date + datetime.timedelta(days=day_offset)
            # Entre 4 y 8 ventas por día
            sales_today = 6 if day_offset < 29 else (total_sales - (sale_counter - 1))
            if day_offset == 29:
                sales_today = total_sales - sale_counter + 1
            else:
                sales_today = random.randint(5, 7)

            for _ in range(sales_today):
                if sale_counter > total_sales:
                    break

                # Horario comercial realista entre 07:30 y 17:30
                hour = random.randint(7, 17)
                minute = random.randint(0, 59)
                second = random.randint(0, 59)
                dt = datetime.datetime.combine(day_date, datetime.time(hour, minute, second))
                timestamp_str = dt.strftime("%Y-%m-%d %H:%M:%S")

                tx_uuid = f"TXN-{dt.strftime('%Y%m%d')}-{sale_counter:04d}-{uuid.uuid4().hex[:6]}"
                cust_type = random.choice(customer_types)
                pay_method = random.choice(payment_methods)
                user_id = random.choice(cashier_user_ids)

                # Cantidad de renglones en el ticket: 1 a 3 artículos
                num_items = random.choices([1, 2, 3], weights=[0.55, 0.35, 0.10])[0]
                
                # Seleccionar productos respetando Pareto (70% A, 20% B, 10% C)
                selected_prods = []
                for _ in range(num_items):
                    pool = random.choices(
                        [prods_a, prods_b, prods_c],
                        weights=[0.70, 0.20, 0.10]
                    )[0]
                    cand = random.choice(pool)
                    if cand not in selected_prods:
                        selected_prods.append(cand)

                items_data = []
                sale_total_amount = 0.0
                sale_total_cost = 0.0

                for prod in selected_prods:
                    # Cantidad vendida según categoría
                    sku = prod["sku"]
                    if sku in ("TF-001", "TF-002", "HE-003", "FP-005"):
                        qty = random.randint(2, 6)
                    elif sku in ("MC-001", "MC-002", "MC-003"):
                        qty = random.randint(1, 5)
                    else:
                        qty = random.randint(1, 2)

                    cost = prod["unit_cost_usd"]
                    price = prod["unit_price_usd"]
                    subtotal = round(qty * price, 2)
                    item_cost = round(qty * cost, 2)

                    sale_total_amount += subtotal
                    sale_total_cost += item_cost
                    items_data.append({
                        "product_id": prod["product_id"],
                        "quantity": qty,
                        "unit_cost": cost,
                        "unit_price": price,
                        "subtotal": subtotal
                    })

                sale_total_amount = round(sale_total_amount, 2)
                sale_total_cost = round(sale_total_cost, 2)
                gross_profit = round(sale_total_amount - sale_total_cost, 2)

                cursor.execute(
                    """
                    INSERT INTO sales (
                        transaction_uuid, sale_timestamp, user_id, customer_type,
                        payment_method, total_cost_usd, total_amount_usd, gross_profit_usd
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (tx_uuid, timestamp_str, user_id, cust_type, pay_method, sale_total_cost, sale_total_amount, gross_profit)
                )
                sale_id = cursor.lastrowid

                for item in items_data:
                    cursor.execute(
                        """
                        INSERT INTO sale_items (
                            sale_id, product_id, quantity, unit_cost_snapshot_usd,
                            unit_price_snapshot_usd, subtotal_usd
                        )
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (sale_id, item["product_id"], item["quantity"], item["unit_cost"], item["unit_price"], item["subtotal"])
                    )

                    # Registrar movimiento de salida
                    p_info = prod_by_id[item["product_id"]]
                    cursor.execute(
                        """
                        INSERT INTO inventory_movements (
                            movement_timestamp, product_id, user_id, movement_type,
                            quantity_delta, stock_before, stock_after, reference_note
                        )
                        VALUES (?, ?, ?, 'VENTA_POS', ?, ?, ?, ?)
                        """,
                        (
                            timestamp_str,
                            item["product_id"],
                            user_id,
                            -item["quantity"],
                            p_info["current_stock"] + item["quantity"],
                            p_info["current_stock"],
                            f"Venta mostrador ticket #{sale_id} ({tx_uuid[:16]})"
                        )
                    )

                sale_counter += 1

        # 15 Registros de INGRESO_PROVEEDOR por Bodeguero (rflores, user_id 4)
        print("--> Generando 15 ingresos de proveedor y 8 ajustes de auditoría en bodega...")
        ingresos_skus = ["MC-001", "MC-002", "HE-003", "FP-001", "TF-001", "PQ-001", "HM-001", "HM-003", "HE-004", "MC-004", "PQ-004", "FP-004", "HM-005", "TF-004", "FP-002"]
        for idx, sku in enumerate(ingresos_skus):
            p = next(x for x in products if x["sku"] == sku)
            day_offset = (idx * 2) % 28
            dt = datetime.datetime.combine(base_date + datetime.timedelta(days=day_offset), datetime.time(8 + (idx % 8), 15, 0))
            qty_in = random.randint(15, 50)
            cursor.execute(
                """
                INSERT INTO inventory_movements (
                    movement_timestamp, product_id, user_id, movement_type,
                    quantity_delta, stock_before, stock_after, reference_note
                )
                VALUES (?, ?, 4, 'INGRESO_PROVEEDOR', ?, ?, ?, ?)
                """,
                (
                    dt.strftime("%Y-%m-%d %H:%M:%S"),
                    p["product_id"],
                    qty_in,
                    p["current_stock"],
                    p["current_stock"] + qty_in,
                    f"Recepción lote #{1000 + idx} proveedor en pasillo {p['aisle_location']}"
                )
            )

        # 8 Registros de AJUSTE_AUDITORIA por Bodeguero (rflores, user_id 4)
        ajuste_skus = ["HM-002", "HM-004", "HE-002", "TF-003", "FP-003", "MC-003", "PQ-002", "HE-005"]
        for idx, sku in enumerate(ajuste_skus):
            p = next(x for x in products if x["sku"] == sku)
            day_offset = (idx * 3) % 29
            dt = datetime.datetime.combine(base_date + datetime.timedelta(days=day_offset), datetime.time(16, 30, 0))
            delta = random.choice([-2, -1, 1, 2])
            cursor.execute(
                """
                INSERT INTO inventory_movements (
                    movement_timestamp, product_id, user_id, movement_type,
                    quantity_delta, stock_before, stock_after, reference_note
                )
                VALUES (?, ?, 4, 'AJUSTE_AUDITORIA', ?, ?, ?, ?)
                """,
                (
                    dt.strftime("%Y-%m-%d %H:%M:%S"),
                    p["product_id"],
                    delta,
                    p["current_stock"],
                    max(0, p["current_stock"] + delta),
                    f"Ajuste físico cíclico por conteo de pasillo ({sku})"
                )
            )

        conn.commit()
        print(f"--> [OK] Base de datos poblada exitosamente con {sale_counter - 1} ventas.")
    finally:
        conn.close()

def main() -> None:
    print("==================================================")
    print("  FERROSTATS: INICIALIZADOR DE DATOS DETERMINISTA")
    print(f"  Lead Architect: {AUTHOR} | Seed: {RANDOM_SEED}")
    print("==================================================")
    init_db()
    load_csv_seeds()
    generate_historical_sales_if_empty()
    run_local_etl_if_empty()

if __name__ == "__main__":
    main()
