from reportlab.lib.pagesizes import LETTER
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from io import BytesIO

def generate_account_statement_pdf(user_name, account_number, balance, transactions, date_range_text="Historial Completo"):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=LETTER, rightMargin=45, leftMargin=45, topMargin=45, bottomMargin=45)
    styles = getSampleStyleSheet()
    
    PRIMARY_COLOR = colors.HexColor("#1e293b")
    SECONDARY_COLOR = colors.HexColor("#64748b")
    BG_LIGHT = colors.HexColor("#f8fafc")

    style_bank_name = ParagraphStyle('bank', fontSize=16, fontName='Helvetica-Bold', textColor=PRIMARY_COLOR, leading=18)
    style_label = ParagraphStyle('label', fontSize=8, textColor=SECONDARY_COLOR, leading=10, spaceAfter=2)
    style_value = ParagraphStyle('value', fontSize=10, fontName='Helvetica-Bold', textColor=PRIMARY_COLOR, leading=12)
    style_header_table = ParagraphStyle('h_table', fontSize=9, fontName='Helvetica-Bold', textColor=colors.white, alignment=TA_LEFT)
    style_cell_left = ParagraphStyle('c_left', fontSize=9, alignment=TA_LEFT, leading=12)
    style_cell_right = ParagraphStyle('c_right', fontSize=9, alignment=TA_RIGHT, leading=12)
    
    # Estilo pequeño para la hora
    style_time = ParagraphStyle('c_time', fontSize=7, textColor=SECONDARY_COLOR, alignment=TA_LEFT, leading=9)

    elements = []

    # --- ENCABEZADO ---
    header_content_left = [
        Paragraph("BANCO SYNAPSE S.A.", style_bank_name),
        Paragraph("Av. Financiera 123, El Salvador", style_label),
        Paragraph("www.synapsebank.sv", style_label)
    ]
    
    header_content_right = [
        Paragraph("ESTADO DE CUENTA", ParagraphStyle('est', fontSize=14, alignment=TA_RIGHT, fontName='Helvetica-Bold', leading=16)),
        #  Imprimimos exactamente el texto del rango de fechas
        Paragraph(f"Periodo: {date_range_text}", 
                  ParagraphStyle('per', alignment=TA_RIGHT, fontSize=9, textColor=SECONDARY_COLOR))
    ]

    header_table = Table([[header_content_left, header_content_right]], colWidths=[260, 260])
    header_table.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP')]))
    elements.append(header_table)
    elements.append(Spacer(1, 25))

    # --- DATOS DEL CLIENTE ---
    client_data = [
        [Paragraph("TITULAR DE LA CUENTA", style_label), Paragraph("NÚMERO DE CUENTA", style_label)],
        [Paragraph(user_name.upper(), style_value), Paragraph(account_number, style_value)]
    ]
    client_table = Table(client_data, colWidths=[260, 260])
    client_table.setStyle(TableStyle([
        ('BOTTOMPADDING', (0,0), (-1,0), 0),
        ('TOPPADDING', (0,1), (-1,1), 2),
    ]))
    elements.append(client_table)
    elements.append(Spacer(1, 10))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey))
    elements.append(Spacer(1, 20))

    # --- RESUMEN ---
    CREDIT = 1
    DEBIT = 2

    total_credits = sum(tx['amount'] for tx in transactions if tx['entry_type'] == CREDIT)
    total_debits = sum(tx['amount'] for tx in transactions if tx['entry_type'] == DEBIT)
    initial_balance = balance - (total_credits - total_debits)

    summary_data = [
        ["SALDO INICIAL", "(+) DEPÓSITOS", "(-) RETIROS", "SALDO FINAL"],
        [f"${initial_balance:,.2f}", f"${total_credits:,.2f}", f"${total_debits:,.2f}", f"${balance:,.2f}"]
    ]
    summary_table = Table(summary_data, colWidths=[130, 130, 130, 130])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), BG_LIGHT),
        ('TEXTCOLOR', (0,0), (-1,-1), PRIMARY_COLOR),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 8),
        ('FONTSIZE', (0,1), (-1,1), 10),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 30))

    # --- TABLA DE MOVIMIENTOS ---
    elements.append(Paragraph("DETALLE DE MOVIMIENTOS", style_value))
    elements.append(Spacer(1, 10))

    # Agregamos la columna "HORA" al encabezado
    data = [[
        Paragraph("FECHA / HORA", style_header_table),
        Paragraph("DESCRIPCIÓN", style_header_table),
        Paragraph("TIPO", style_header_table),
        Paragraph("MONTO", ParagraphStyle('h_right', parent=style_header_table, alignment=TA_RIGHT))
    ]]

    for i, tx in enumerate(transactions):
        # Actualizado para usar el número 1 (CREDIT)
        color = colors.HexColor("#15803d") if tx['entry_type'] == CREDIT else colors.HexColor("#b91c1c")
        prefix = "+" if tx['entry_type'] == CREDIT else "-"
        amount_text = f"<b><font color='{color}'>{prefix}${tx['amount']:,.2f}</font></b>"
        
        # Formateamos fecha y hora
        date_str = tx['date'].strftime("%d/%m/%Y")
        time_str = tx['date'].strftime("%I:%M %p") # Ejemplo: 02:30 PM
        
        # Combinamos fecha y hora en una celda usando Paragraphs apilados
        date_time_cell = [
            Paragraph(date_str, style_cell_left),
            Paragraph(time_str, style_time)
        ]
        
        data.append([
            date_time_cell,
            Paragraph(tx['description'], style_cell_left),
            Paragraph(tx['type'], style_cell_left),
            Paragraph(amount_text, style_cell_right)
        ])

    # Reajuste de anchos: La primera columna necesita un poco más para la hora
    t_mov = Table(data, colWidths=[85, 235, 90, 110])
    t_mov.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), PRIMARY_COLOR),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LINEBELOW', (0,0), (-1,-1), 0.5, colors.lightgrey),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ]))
    
    for i in range(1, len(data)):
        if i % 2 == 0:
            t_mov.setStyle([('BACKGROUND', (0,i), (-1,i), BG_LIGHT)])

    elements.append(t_mov)
    
    # --- FOOTER ---
    elements.append(Spacer(1, 50))
    footer_text = "Este documento es una representación impresa de movimientos electrónicos. <br/> Banco Synapse S.A. - Vigilado por la Superintendencia del Sistema Financiero."
    elements.append(Paragraph(footer_text, ParagraphStyle('footer', fontSize=7, textColor=SECONDARY_COLOR, alignment=TA_CENTER, leading=9)))

    doc.build(elements)
    buffer.seek(0)
    return buffer