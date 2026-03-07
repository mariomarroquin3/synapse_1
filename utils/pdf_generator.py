from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib import colors
import io
from datetime import datetime

def generate_card_pdf(holder_name, card_number, pin, exp_date_str, card_type="Débito"):
    """
    Genera un archivo PDF en memoria con los datos de la tarjeta.
    """
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    # --- Configuración de Estilo ---
    p.setStrokeColor(colors.black)
    p.setLineWidth(1)
    
    # --- Encabezado / Logo Simulado ---
    p.setFont("Helvetica-Bold", 24)
    p.drawCentredString(width / 2.0, height - 1*inch, "SYNAPSE BANK")
    
    p.setFont("Helvetica", 12)
    p.drawCentredString(width / 2.0, height - 1.2*inch, "Comprobante de Emisión de Tarjeta")
    p.line(1*inch, height - 1.4*inch, width - 1*inch, height - 1.4*inch)

    # --- Información de la Tarjeta ---
    y_position = height - 2*inch
    
    p.setFont("Helvetica-Bold", 14)
    p.drawString(1.5*inch, y_position, "Detalles de la Tarjeta:")
    
    y_position -= 0.4*inch
    p.setFont("Helvetica", 12)
    
    details = [
        ("Titular:", holder_name),
        ("Número de Tarjeta:", card_number),
        ("PIN de Seguridad:", pin),
        ("Fecha de Vencimiento:", exp_date_str),
        ("Tipo de Tarjeta:", card_type),
        ("Fecha de Emisión:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    ]
    
    for label, value in details:
        p.setFont("Helvetica-Bold", 12)
        p.drawString(1.5*inch, y_position, label)
        p.setFont("Helvetica", 12)
        p.drawString(3.5*inch, y_position, str(value))
        y_position -= 0.3*inch

    # --- Cuadro de Aviso Importante ---
    y_position -= 0.5*inch
    p.setFillColor(colors.whitesmoke)
    p.rect(1.2*inch, y_position - 1*inch, width - 2.4*inch, 1.2*inch, fill=1)
    
    p.setFillColor(colors.black)
    p.setFont("Helvetica-Bold", 10)
    p.drawString(1.4*inch, y_position - 0.2*inch, "AVISO DE SEGURIDAD:")
    p.setFont("Helvetica", 10)
    p.drawString(1.4*inch, y_position - 0.4*inch, "- No compartas tu PIN con nadie.")
    p.drawString(1.4*inch, y_position - 0.6*inch, "- El banco nunca te pedirá tu PIN por correo o teléfono.")
    p.drawString(1.4*inch, y_position - 0.8*inch, "- Memoriza tu PIN y destruye este documento después.")

    # --- Pie de página ---
    p.setFont("Helvetica-Oblique", 8)
    p.drawCentredString(width / 2.0, 1*inch, "Este es un documento generado automáticamente por el sistema Synapse.")

    p.showPage()
    p.save()

    buffer.seek(0)
    return buffer
