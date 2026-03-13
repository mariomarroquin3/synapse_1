from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from io import BytesIO
import datetime

def generar_pdf_auditoria(df, titulo="Reporte Ejecutivo de Auditoría", date_range=None):
    buffer = BytesIO()
    # Márgenes un poco más amplios para respirar mejor
    doc = SimpleDocTemplate(buffer, pagesize=landscape(letter), rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    
    elementos = []
    styles = getSampleStyleSheet()
    
    # --- Estilos de Texto Profesionales ---
    estilo_titulo = ParagraphStyle(
        'Titulo', parent=styles['Heading1'], alignment=TA_CENTER, 
        textColor=colors.HexColor("#1e293b"), fontName="Helvetica-Bold", fontSize=16, spaceAfter=8
    )
    estilo_subtitulo = ParagraphStyle(
        'Subtitulo', parent=styles['Normal'], alignment=TA_CENTER, 
        textColor=colors.HexColor("#475569"), fontName="Helvetica", fontSize=10, spaceAfter=4
    )
    estilo_fecha = ParagraphStyle(
        'Fecha', parent=styles['Normal'], alignment=TA_CENTER, 
        textColor=colors.HexColor("#94a3b8"), fontSize=8, spaceAfter=25
    )
    
    # --- Lógica del texto del Rango de Fechas (Lenguaje Ejecutivo) ---
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

    # --- Construcción del Encabezado ---
    elementos.append(Paragraph(titulo.upper(), estilo_titulo))
    elementos.append(Paragraph(texto_rango, estilo_subtitulo))
    
    fecha_gen = datetime.datetime.now().strftime("%d/%m/%Y a las %H:%M:%S")
    elementos.append(Paragraph(f"Documento generado el {fecha_gen}", estilo_fecha))
    
    # --- Preparar Datos de la Tabla ---
    df_string = df.astype(str)
    # Reemplazamos los "nan" o vacíos visuales
    df_string = df_string.replace('nan', '-')
    datos_tabla = [df_string.columns.tolist()] + df_string.values.tolist()
    
    # --- Crear y Estilizar la Tabla ---
    # Calculamos anchos automáticos si es necesario, pero ReportLab lo hace bien por defecto
    tabla = Table(datos_tabla, repeatRows=1) # repeatRows hace que el encabezado se repita si hay varias páginas
    
    estilo_tabla = TableStyle([
        # Encabezado Corporativo (Gris Pizarra Oscuro)
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1e293b")), 
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('TOPPADDING', (0, 0), (-1, 0), 10),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        
        # Cuerpo de la tabla
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor("#334155")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")), # Bordes muy sutiles
        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
        ('TOPPADDING', (0, 1), (-1, -1), 8),
        
        # Filas alternas (Blanco y un gris levísimo)
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]) 
    ])
    
    tabla.setStyle(estilo_tabla)
    elementos.append(tabla)
    
    doc.build(elementos)
    buffer.seek(0)
    return buffer