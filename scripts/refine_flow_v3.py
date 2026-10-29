import os
from PIL import Image, ImageDraw, ImageFont

def refine_flow():
    src_path = "C:/Users/Usuario/.gemini/antigravity-ide/brain/0f51a237-70a9-4358-9f54-d804bf205f74/ferrostats_linkedin_flow_v3_1793242527041.jpg"
    im_base = Image.open(src_path).convert("RGBA")

    target_w, target_h = 1920, 1071
    im = im_base.resize((target_w, target_h), Image.Resampling.LANCZOS)
    draw = ImageDraw.Draw(im)

    scale_x = target_w / 1376.0
    scale_y = target_h / 768.0

    # Fonts
    font_title = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 22)
    font_sub = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 14)
    font_kpi_val = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 15)
    font_kpi_lbl = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 11)
    font_micro = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 12)

    # =========================================================================
    # 1. REMOVE "DOI Replenishment / Mcdel / Models" from GOLD in Box 4
    # =========================================================================
    # Exact inner bounds of DOI box
    gx0 = int(872 * scale_x)
    gy0 = int(608 * scale_y)
    gx1 = int(1028 * scale_x)
    gy1 = int(706 * scale_y)

    # Exact background match of the Gold box
    bg_gold = (41, 49, 60, 255)
    draw.rounded_rectangle([gx0, gy0, gx1, gy1], radius=6, fill=bg_gold)

    # =========================================================================
    # 2. BOX 5: "5. BI" and EXPANDED DASHBOARD IMAGE
    # =========================================================================
    # Cover the entire Box 5 from the very top header to bottom
    b5_x0 = int(1098 * scale_x)
    b5_y0 = int(136 * scale_y)
    b5_x1 = int(1354 * scale_x)
    b5_y1 = int(728 * scale_y)
    b5_w = b5_x1 - b5_x0
    b5_h = b5_y1 - b5_y0

    bg_box5 = (14, 22, 36, 255)
    draw.rounded_rectangle([b5_x0, b5_y0, b5_x1, b5_y1], radius=12, fill=bg_box5, outline=(30, 41, 59, 255), width=2)

    # Header of Box 5: Exactly "5. BI" as requested
    hdr_y = b5_y0 + 16
    draw.text((b5_x0 + 18, hdr_y), "5. BI", fill=(56, 189, 248, 255), font=font_title)
    draw.text((b5_x0 + 75, hdr_y + 4), "Google Looker Studio", fill=(248, 250, 252, 255), font=font_sub)
    draw.text((b5_x0 + 18, hdr_y + 30), "Dashboard Ejecutivo en Tiempo Real", fill=(148, 163, 184, 255), font=font_micro)

    # Expanded Looker Studio Dashboard Image
    looker_path = "assets/capturas/04_inteligencia_negocio_looker_pag1.png"
    if os.path.exists(looker_path):
        looker_raw = Image.open(looker_path).convert("RGBA")
        
        # Make the dashboard significantly larger and expanded
        dash_pad_x = 10
        dash_x0 = b5_x0 + dash_pad_x
        dash_w = b5_w - (dash_pad_x * 2)  # around 337 px
        
        # Expanded height: 490 px to show all charts in full clarity
        dash_h = 490
        dash_y0 = hdr_y + 54

        looker_resized = looker_raw.resize((dash_w, dash_h), Image.Resampling.LANCZOS)

        # Draw glowing neon card frame around expanded dashboard
        draw.rounded_rectangle([dash_x0 - 2, dash_y0 - 2, dash_x0 + dash_w + 2, dash_y0 + dash_h + 2], 
                               radius=8, fill=(8, 12, 21, 255), outline=(56, 189, 248, 220), width=2)
        im.paste(looker_resized, (dash_x0, dash_y0), looker_resized)

        # KPI Summary Cards below the expanded dashboard
        kpi_y0 = dash_y0 + dash_h + 12
        kpi_w = (b5_w - 28) // 3
        kpi_h = 56

        kpis = [
            ("Facturación", "$123.3M", (56, 189, 248)),
            ("Margen Bruto", "$40.9M", (52, 211, 153)),
            ("Unidades", "11.0M", (245, 158, 11))
        ]

        for idx, (label, val, col) in enumerate(kpis):
            kx = b5_x0 + 10 + idx * (kpi_w + 4)
            draw.rounded_rectangle([kx, kpi_y0, kx + kpi_w, kpi_y0 + kpi_h], radius=6, 
                                   fill=(21, 32, 51, 255), outline=(37, 53, 82, 255), width=1)
            draw.text((kx + 8, kpi_y0 + 6), label, fill=(148, 163, 184, 255), font=font_kpi_lbl)
            draw.text((kx + 8, kpi_y0 + 26), val, fill=col, font=font_kpi_val)

        # Footer note
        draw.text((b5_x0 + 18, kpi_y0 + kpi_h + 10), "Direct Query / BI Engine sobre BigQuery Gold", fill=(56, 189, 248, 220), font=font_micro)

    # =========================================================================
    # 3. SAVE HIGH-RES OUTPUTS (JPG & PNG)
    # =========================================================================
    out_jpg = "assets/capturas/linkedin_architecture_flow_v2.jpg"
    out_png = "assets/capturas/linkedin_architecture_flow_v2.png"

    im_rgb = im.convert("RGB")
    im_rgb.save(out_jpg, "JPEG", quality=98)
    im.save(out_png, "PNG")

    print("Refined flow successfully saved at 1920x1071:")
    print(f"  -> {out_jpg}")
    print(f"  -> {out_png}")

if __name__ == "__main__":
    refine_flow()
