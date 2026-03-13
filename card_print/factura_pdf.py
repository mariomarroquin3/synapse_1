from reportlab.lib.pagesizes import A6
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.graphics.barcode import code128
from io import BytesIO

def generar_recibo_pdf(datos_recibo):
    buffer = BytesIO()
    # 1. Redujimos los márgenes top y bottom a 10 para ganar más espacio vertical
    doc = SimpleDocTemplate(buffer, pagesize=A6, rightMargin=15, leftMargin=15, topMargin=10, bottomMargin=10)
    
    # --- PALETA DE COLORES FINTECH ---
    BRAND_COLOR = colors.HexColor("#0f172a")
    ACCENT_COLOR = colors.HexColor("#3b82f6")
    TEXT_MUTED = colors.HexColor("#64748b")
    BG_LIGHT = colors.HexColor("#f8fafc")
    DIVIDER_COLOR = colors.HexColor("#cbd5e1")
    
    es_deposito = "Depósito" in datos_recibo['operacion']
    amount_color = colors.HexColor("#16a34a") if es_deposito else colors.HexColor("#dc2626")
    signo = "+" if es_deposito else "-"

    # --- ESTILOS DE TEXTO (Espaciados reducidos) ---
    style_bank = ParagraphStyle('Bank', fontSize=14, fontName='Helvetica-Bold', alignment=TA_CENTER, textColor=BRAND_COLOR, spaceAfter=2)
    style_tagline = ParagraphStyle('Tag', fontSize=6.5, fontName='Helvetica', alignment=TA_CENTER, textColor=ACCENT_COLOR, spaceAfter=8, letterSpacing=1)
    style_section = ParagraphStyle('Sec', fontSize=8, fontName='Helvetica-Bold', alignment=TA_LEFT, textColor=TEXT_MUTED, spaceAfter=4)
    style_footer = ParagraphStyle('Foot', fontSize=6.5, fontName='Helvetica', alignment=TA_CENTER, textColor=TEXT_MUTED, leading=8)

    elementos = []
    
    # --- 1. ENCABEZADO ---
    elementos.append(Paragraph("SYNAPSE", style_bank))
    elementos.append(Paragraph("DIGITAL BANKING NETWORK", style_tagline))
    
    elementos.append(HRFlowable(width="100%", thickness=1, color=DIVIDER_COLOR, spaceAfter=8, spaceBefore=2))

    # --- 2. DATOS DEL CLIENTE Y CAJERO ---
    cuenta_str = str(datos_recibo['cuenta'])
    cuenta_enmascarada = f"**** {cuenta_str[-4:]}" if len(cuenta_str) > 4 else cuenta_str

    info_data = [
        ["FECHA:", datos_recibo['fecha']],
        ["CAJERO:", "ATM-001 (SUCURSAL VIRTUAL)"],
        ["CLIENTE:", str(datos_recibo['usuario']).upper()],
        ["CUENTA:", cuenta_enmascarada]
    ]
    
    t_info = Table(info_data, colWidths=[65, 160])
    # 2. Redujimos el BOTTOMPADDING a 3
    t_info.setStyle(TableStyle([
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
        ('FONTNAME', (1,0), (1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('TEXTCOLOR', (0,0), (0,-1), TEXT_MUTED),
        ('TEXTCOLOR', (1,0), (1,-1), BRAND_COLOR),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    elementos.append(t_info)
    elementos.append(Spacer(1, 8)) # Reducido de 15 a 8

    # --- 3. BLOQUE DE TRANSACCIÓN ---
    elementos.append(Paragraph("DETALLE DE OPERACIÓN", style_section))
    
    tx_data = [
        ["TIPO:", datos_recibo['operacion'].upper()],
        ["ESTADO:", datos_recibo['estado'].upper()],
        ["MONTO:", f"{signo} ${datos_recibo['monto']:,.2f}"]
    ]
    
    t_tx = Table(tx_data, colWidths=[65, 160])
    # 3. Redujimos TOPPADDING y BOTTOMPADDING a 6 para compactar la tabla
    t_tx.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), BG_LIGHT),
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
        ('FONTNAME', (1,0), (1,-1), 'Helvetica-Bold'), 
        ('FONTSIZE', (0,0), (0,-1), 8),
        ('FONTSIZE', (1,0), (1,-1), 10),
        ('TEXTCOLOR', (0,0), (0,-1), TEXT_MUTED),
        ('TEXTCOLOR', (1,0), (1,0), BRAND_COLOR),
        ('TEXTCOLOR', (1,1), (1,1), ACCENT_COLOR),
        ('TEXTCOLOR', (1,2), (1,2), amount_color),
        ('ALIGN', (0,0), (0,-1), 'LEFT'),
        ('ALIGN', (1,0), (1,-1), 'RIGHT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('BOX', (0,0), (-1,-1), 1, DIVIDER_COLOR), 
    ]))
    elementos.append(t_tx)
    elementos.append(Spacer(1, 8)) # Reducido de 15 a 8

    # --- 4. CÓDIGO DE BARRAS DE REFERENCIA ---
    ref_str = str(datos_recibo['referencia'])
    # Redujimos un poco la altura del código de barras (barHeight=20)
    barcode = code128.Code128(ref_str, barHeight=20, barWidth=1.2)
    
    t_barcode = Table([[barcode]], colWidths=[225])
    t_barcode.setStyle(TableStyle([
        ('ALIGN', (0,0), (0,0), 'CENTER'),
        ('VALIGN', (0,0), (0,0), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (0,0), 2),
    ]))
    elementos.append(t_barcode)
    
    style_ref = ParagraphStyle('Ref', fontSize=7.5, fontName='Helvetica', alignment=TA_CENTER, textColor=BRAND_COLOR, spaceAfter=8)
    elementos.append(Paragraph(f"Ref: {ref_str}", style_ref))

    # --- 5. PIE DE PÁGINA ---
    elementos.append(HRFlowable(width="100%", thickness=1, color=DIVIDER_COLOR, spaceAfter=6, spaceBefore=0))
    elementos.append(Paragraph("¡Gracias por confiar en Synapse!", style_footer))
    elementos.append(Paragraph("Conserve este comprobante para futuras gestiones.", style_footer))

    doc.build(elementos)
    buffer.seek(0)
    return buffer