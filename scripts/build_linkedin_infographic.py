import os
from PIL import Image, ImageDraw, ImageFont

def build_infographic():
    W, H = 1920, 1080
    im = Image.new("RGBA", (W, H), (8, 12, 21, 255))
    draw = ImageDraw.Draw(im)

    # Fonts
    font_bold_title = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 26)
    font_header_sub = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 14)
    font_badge = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 12)
    font_col_title = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 16)
    font_col_sub = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 12)
    font_card_title = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 13)
    font_card_body = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 11)
    font_micro = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 10)

    # 1. Header
    header_x, header_y, header_w, header_h = 40, 22, 1840, 108
    draw.rounded_rectangle([header_x, header_y, header_x + header_w, header_y + header_h], radius=14, fill=(13, 20, 36, 255), outline=(30, 41, 59, 255), width=2)

    # Badge GCP
    draw.rounded_rectangle([header_x + 20, header_y + 18, header_x + 155, header_y + 46], radius=6, fill=(21, 32, 51, 255), outline=(56, 189, 248, 255), width=1)
    draw.text((header_x + 32, header_y + 24), "GCP CLOUD", fill=(56, 189, 248, 255), font=font_badge)

    draw.text((header_x + 175, header_y + 16), "FERROSTATS — ARQUITECTURA DE DATOS END-TO-END", fill=(248, 250, 252, 255), font=font_bold_title)
    draw.text((header_x + 175, header_y + 52), "Proyecto Personal de Portafolio: Spec-Driven Development (SDD), Modelado Dimensional y Lakehouse en GCP", fill=(148, 163, 184, 255), font=font_header_sub)
    draw.text((header_x + 175, header_y + 75), "Diego Alejandro Escobar Barahona  |  Google Cloud Certified — Associate Data Practitioner", fill=(56, 189, 248, 255), font=font_card_title)

    # FinOps badge right
    finops_x = header_x + header_w - 230
    draw.rounded_rectangle([finops_x, header_y + 18, finops_x + 210, header_y + 88], radius=8, fill=(16, 37, 30, 255), outline=(16, 185, 129, 255), width=2)
    draw.text((finops_x + 32, header_y + 30), "FINOPS AUDITADO", fill=(52, 211, 153, 255), font=font_badge)
    draw.text((finops_x + 40, header_y + 54), "$0.00 USD / MES", fill=(240, 253, 244, 255), font=font_card_title)

    # 2. Columns Layout
    cols = [
        {"x": 40,   "w": 270, "num": "1", "title": "BORDE TRANSACCIONAL", "sub": "Terminal POS Mostrador", "badge": "Latencia <50 ms ACID", "color": (56, 189, 248)},
        {"x": 330,  "w": 280, "num": "2", "title": "COMPUTE SERVERLESS",  "sub": "Backend (SDD) & SQLite",  "badge": "Cloud Run scale-to-zero", "color": (96, 165, 250)},
        {"x": 630,  "w": 280, "num": "3", "title": "INGESTA STREAMING",   "sub": "BigQuery Streaming API", "badge": "REST insertAll • Sin llaves", "color": (52, 211, 153)},
        {"x": 930,  "w": 360, "num": "4", "title": "LAKEHOUSE MEDALLON",  "sub": "BigQuery & Dataform SQLX", "badge": "Star Schema • Data Quality", "color": (245, 158, 11)},
        {"x": 1310, "w": 570, "num": "5", "title": "BUSINESS INTELLIGENCE", "sub": "Google Looker Studio", "badge": "Suite Analitica Real (3 Pags)", "color": (168, 85, 247)}
    ]

    col_y = 145
    col_h = 910

    # Draw columns backgrounds
    for c in cols:
        cx, cw = c["x"], c["w"]
        draw.rounded_rectangle([cx, col_y, cx + cw, col_y + col_h], radius=12, fill=(13, 20, 36, 235), outline=(30, 41, 59, 255), width=2)

        # Header of column
        draw.rounded_rectangle([cx + 12, col_y + 12, cx + 46, col_y + 46], radius=6, fill=(21, 32, 51, 255), outline=c["color"], width=2)
        draw.text((cx + 23, col_y + 18), c["num"], fill=c["color"], font=font_col_title)

        draw.text((cx + 56, col_y + 14), c["title"], fill=(248, 250, 252, 255), font=font_col_title)
        draw.text((cx + 56, col_y + 36), c["sub"], fill=(148, 163, 184, 255), font=font_col_sub)

        # Badge under title
        draw.rounded_rectangle([cx + 12, col_y + 56, cx + cw - 12, col_y + 80], radius=5, fill=(18, 27, 47, 255), outline=(37, 53, 82, 255), width=1)
        draw.text((cx + 20, col_y + 61), c["badge"], fill=c["color"], font=font_micro)

        # Divider line
        draw.line([cx + 12, col_y + 90, cx + cw - 12, col_y + 90], fill=(30, 41, 59, 255), width=1)

    # Connecting arrows between columns
    arrow_y = col_y + 45
    for i in range(len(cols) - 1):
        x1 = cols[i]["x"] + cols[i]["w"]
        x2 = cols[i + 1]["x"]
        mid_x = (x1 + x2) // 2
        draw.line([x1 + 4, arrow_y, x2 - 4, arrow_y], fill=(56, 189, 248, 200), width=2)
        draw.polygon([(x2 - 4, arrow_y), (x2 - 10, arrow_y - 4), (x2 - 10, arrow_y + 4)], fill=(56, 189, 248, 255))

    # 3. Populate Column 1: POS Mostrador
    c1_cards = [
        ("Garantias ACID Estrictas", "Aislamiento transaccional en mostrador sin lecturas sucias."),
        ("Bloqueo BEGIN IMMEDIATE", "Eleva el cerrojo de escritura previo a consultar el stock."),
        ("Deduplicacion por UUID", "Idempotencia estricta por ticket. 0% riesgo de doble cobro."),
        ("Descuento Atomico Protegido", "UPDATE con clausula de guarda WHERE current_stock >= :qty."),
        ("Calculo Fiscal Integrado", "Desglose automatico de IVA 13%, ticket digital y atajos de efectivo.")
    ]
    cy = col_y + 102
    for title, desc in c1_cards:
        draw.rounded_rectangle([40 + 10, cy, 40 + 270 - 10, cy + 135], radius=8, fill=(18, 27, 47, 255), outline=(37, 53, 82, 255), width=1)
        draw.text((40 + 20, cy + 12), title, fill=(56, 189, 248, 255), font=font_card_title)
        words = desc.split()
        l1, l2 = " ".join(words[:5]), " ".join(words[5:])
        draw.text((40 + 20, cy + 42), l1, fill=(203, 213, 225, 255), font=font_card_body)
        draw.text((40 + 20, cy + 64), l2, fill=(203, 213, 225, 255), font=font_card_body)
        cy += 150

    # 4. Populate Column 2: Backend (SDD) & SQLite WAL
    c2_cards = [
        ("Backend Guiado por SDD", "Disenado bajo especificaciones tecnicas formales previas al codigo."),
        ("FastAPI en Python 3.11", "Enrutador REST asincrono con serializacion de esquemas Pydantic v2."),
        ("SQLite en Modo WAL", "Write-Ahead Logging en disco local (/tmp). Micro-latencia < 5 ms."),
        ("Control de Acceso RBAC", "Roles jerarquizados para Administrador, Cajero y Bodeguero."),
        ("Cloud Run Scale-to-Zero", "Contenedor minimo (~130 MB). 0 instancias inactivas = $0.00 USD.")
    ]
    cy = col_y + 102
    for title, desc in c2_cards:
        draw.rounded_rectangle([330 + 10, cy, 330 + 280 - 10, cy + 135], radius=8, fill=(18, 27, 47, 255), outline=(37, 53, 82, 255), width=1)
        draw.text((330 + 20, cy + 12), title, fill=(96, 165, 250, 255), font=font_card_title)
        words = desc.split()
        l1, l2 = " ".join(words[:5]), " ".join(words[5:])
        draw.text((330 + 20, cy + 42), l1, fill=(203, 213, 225, 255), font=font_card_body)
        draw.text((330 + 20, cy + 64), l2, fill=(203, 213, 225, 255), font=font_card_body)
        cy += 150

    # 5. Populate Column 3: Ingesta Streaming BigQuery API
    c3_cards = [
        ("BigQuery Streaming API", "Llamada REST directa tabledata.insertAll hacia dataset Bronze."),
        ("Tokens IAM por Metadatos", "Resolucion automatica via servidor interno /computeMetadata/v1."),
        ("Cero SDKs Pesados", "Cliente HTTP nativo (urllib). Arranque en frio sub-3s sin bloatware."),
        ("Buffer No Bloqueante", "La terminal de caja cobra al instante sin esperar latencia cloud."),
        ("Trazabilidad y Linaje", "Auditoria inmutable con sale_id, timestamps y comprobante fiscal.")
    ]
    cy = col_y + 102
    for title, desc in c3_cards:
        draw.rounded_rectangle([630 + 10, cy, 630 + 280 - 10, cy + 135], radius=8, fill=(18, 27, 47, 255), outline=(37, 53, 82, 255), width=1)
        draw.text((630 + 20, cy + 12), title, fill=(52, 211, 153, 255), font=font_card_title)
        words = desc.split()
        l1, l2 = " ".join(words[:5]), " ".join(words[5:])
        draw.text((630 + 20, cy + 42), l1, fill=(203, 213, 225, 255), font=font_card_body)
        draw.text((630 + 20, cy + 64), l2, fill=(203, 213, 225, 255), font=font_card_body)
        cy += 150

    # 6. Populate Column 4: Lakehouse Medallon BigQuery & Dataform
    c4_cards = [
        ("Capa Bronze (Crudo Inmutable)", "raw_sales y raw_sale_items preservando el historial original completo."),
        ("Capa Silver (Staging Curado)", "Modelos SQLX con casteo estricto (INT64, FLOAT64, TIMESTAMP) y COGS."),
        ("Aserciones Data Quality (DQ)", "Validacion de uniqueKey (sale_id), nonNull y reglas antes de publicar."),
        ("Capa Gold (Star Schema)", "Data Marts dimensionales: fct_ventas_diarias y mart_inventario_pareto_abc."),
        ("SQL Ventana: Pareto 80/20", "SUM() OVER() en 30 dias para clasificar SKUs A, B, C y calcular DOI/ROP.")
    ]
    cy = col_y + 102
    for title, desc in c4_cards:
        draw.rounded_rectangle([930 + 10, cy, 930 + 360 - 10, cy + 135], radius=8, fill=(18, 27, 47, 255), outline=(37, 53, 82, 255), width=1)
        draw.text((930 + 20, cy + 12), title, fill=(245, 158, 11, 255), font=font_card_title)
        words = desc.split()
        l1, l2 = " ".join(words[:6]), " ".join(words[6:])
        draw.text((930 + 20, cy + 42), l1, fill=(203, 213, 225, 255), font=font_card_body)
        draw.text((930 + 20, cy + 64), l2, fill=(203, 213, 225, 255), font=font_card_body)
        cy += 150

    # 7. Populate Column 5: REAL LOOKER STUDIO CAPTURES!
    c5_x = 1310
    c5_w = 570
    target_img_w = 546
    img_x = c5_x + 12

    # Load real Looker images
    p1 = Image.open("assets/capturas/looker_real_p1.png")
    p2 = Image.open("assets/capturas/looker_real_p2.png")
    p3 = Image.open("assets/capturas/looker_real_p3.png")

    # Render image 1 (Page 1: Sales & Margins)
    target_h1 = 230
    p1_resized = p1.resize((target_img_w, target_h1), Image.Resampling.LANCZOS)
    draw.rounded_rectangle([img_x, col_y + 102, img_x + target_img_w, col_y + 102 + target_h1 + 24], radius=8, fill=(18, 27, 47, 255), outline=(168, 85, 247, 255), width=1)
    draw.text((img_x + 10, col_y + 107), "PAG 1: VENTAS, MARGENES Y FACTURACION POR CATEGORIA (LOOKER REAL)", fill=(216, 180, 254, 255), font=font_micro)
    im.paste(p1_resized, (img_x, col_y + 126))

    # Render image 2 (Page 2: Pareto Matrix & DOI Table)
    target_h2 = 245
    p2_resized = p2.resize((target_img_w, target_h2), Image.Resampling.LANCZOS)
    draw.rounded_rectangle([img_x, col_y + 372, img_x + target_img_w, col_y + 372 + target_h2 + 24], radius=8, fill=(18, 27, 47, 255), outline=(168, 85, 247, 255), width=1)
    draw.text((img_x + 10, col_y + 377), "PAG 2: MATRIZ PARETO 80/20, BURN RATE Y DIAS DE INVENTARIO DOI (LOOKER REAL)", fill=(216, 180, 254, 255), font=font_micro)
    im.paste(p2_resized, (img_x, col_y + 396))

    # Render image 3 (Page 3: Inventory Valuation Pie Chart)
    target_h3 = 230
    p3_resized = p3.resize((target_img_w, target_h3), Image.Resampling.LANCZOS)
    draw.rounded_rectangle([img_x, col_y + 655, img_x + target_img_w, col_y + 655 + target_h3 + 24], radius=8, fill=(18, 27, 47, 255), outline=(168, 85, 247, 255), width=1)
    draw.text((img_x + 10, col_y + 660), "PAG 3: VALORACION DE CAPITAL DE TRABAJO ($1.39M) Y SEGMENTACION ABC", fill=(216, 180, 254, 255), font=font_micro)
    im.paste(p3_resized, (img_x, col_y + 679))

    # Footer note in Column 5
    draw.text((img_x + 35, col_y + 925), "Google Looker Studio conectado directamente a los Data Marts Gold de BigQuery", fill=(148, 163, 184, 255), font=font_micro)

    # 8. Save
    output_path = "assets/capturas/linkedin_architecture_infographic.png"
    im.save(output_path, "PNG")
    print(f"Generated clean infographic successfully: {output_path}")

if __name__ == "__main__":
    build_infographic()
