from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from io import BytesIO
import datetime

def generar_pdf_auditoria(df, titulo="Reporte Ejecutivo de Auditoría", date_range=None):
    buffer = BytesIO()
    
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )
    
    elementos = []
    styles = getSampleStyleSheet()
    
    # --- Estilos ---
    estilo_titulo = ParagraphStyle(
        'Titulo',
        parent=styles['Heading1'],
        alignment=TA_CENTER,
        textColor=colors.HexColor("#1e293b"),
        fontName="Helvetica-Bold",
        fontSize=16,
        spaceAfter=8
    )

    estilo_subtitulo = ParagraphStyle(
        'Subtitulo',
        parent=styles['Normal'],
        alignment=TA_CENTER,
        textColor=colors.HexColor("#475569"),
        fontName="Helvetica",
        fontSize=10,
        spaceAfter=4
    )

    estilo_fecha = ParagraphStyle(
        'Fecha',
        parent=styles['Normal'],
        alignment=TA_CENTER,
        textColor=colors.HexColor("#94a3b8"),
        fontSize=8,
        spaceAfter=25
    )

    estilo_celda = ParagraphStyle(
        'Celda',
        parent=styles['Normal'],
        fontName="Helvetica",
        fontSize=8,
        textColor=colors.HexColor("#334155"),
        leading=10
    )

    estilo_header = ParagraphStyle(
        'Header',
        parent=styles['Normal'],
        fontName="Helvetica-Bold",
        fontSize=9,
        textColor=colors.white,
        alignment=TA_CENTER
    )

    df = df.rename(columns={
        "Tipo Nombre": "Tipo"
    })

    # --- Rango de fechas ---
    if not date_range:
        texto_rango = "Período: Todo el histórico disponible"
    elif isinstance(date_range, (list, tuple)):
        if len(date_range) == 2:
            if date_range[0] == date_range[1]:
                texto_rango = f"Fecha de registro: {date_range[0].strftime('%d/%m/%Y')}"
            else:
                texto_rango = f"Período consultado: {date_range[0].strftime('%d/%m/%Y')} - {date_range[1].strftime('%d/%m/%Y')}"
        elif len(date_range) == 1:
            texto_rango = f"Fecha de registro: {date_range[0].strftime('%d/%m/%Y')}"
        else:
            texto_rango = "Período: Todo el histórico disponible"
    else:
        texto_rango = "Período: Todo el histórico disponible"

    # --- Encabezado ---
    elementos.append(Paragraph(titulo.upper(), estilo_titulo))
    elementos.append(Paragraph(texto_rango, estilo_subtitulo))
    
    fecha_gen = datetime.datetime.now().strftime("%d/%m/%Y a las %H:%M:%S")
    elementos.append(Paragraph(f"Documento generado el {fecha_gen}", estilo_fecha))

    # --- Preparar datos ---
    df_string = df.astype(str)
    df_string = df_string.replace('nan', '-')

    datos_tabla = []

    # Header
    encabezados = [
        Paragraph(col, estilo_header)
        for col in df_string.columns.tolist()
    ]
    datos_tabla.append(encabezados)

    # Filas
    for fila in df_string.values:
        nueva_fila = []
        for celda in fila:
            nueva_fila.append(Paragraph(str(celda), estilo_celda))
        datos_tabla.append(nueva_fila)

    # --- Tabla ---
    tabla = Table(datos_tabla, repeatRows=1)

    estilo_tabla = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1e293b")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),

        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),

        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [
            colors.white,
            colors.HexColor("#f8fafc")
        ])
    ])

    tabla.setStyle(estilo_tabla)
    elementos.append(tabla)

    doc.build(elementos)
    buffer.seek(0)

    return buffer
