from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib import colors

def generate_card_pdf(card_data):
    _, last4, expiration_date, full_name = card_data

    image_path = "plantilla_tarjeta.png"
    image = ImageReader(image_path)
    img_width, img_height = image.getSize()

    c = canvas.Canvas("tarjeta_generada.pdf", pagesize=(img_width, img_height))
    c.drawImage(image_path, 0, 0, width=img_width, height=img_height)

    # ==========================================================
    # FRENTE (Nombre y Cuenta - Blanco)
    # ==========================================================
    c.setFillColor(colors.white)
    
    # Nombre del titular
    c.setFont("Helvetica-Bold", 38)
    c.drawString(img_width * 0.18, img_height * 0.67, full_name.upper())

    # Número de cuenta (con espacios)
    c.setFont("Helvetica-Bold", 41)
    c.drawString(img_width * 0.20, img_height * 0.72, " ".join(last4))

    # ==========================================================
    # REVERSO 
    # ==========================================================
    
    # --- FECHA DE EXPIRACIÓN (Blanco) ---
    c.setFillColor(colors.white) 
    c.setFont("Helvetica-Bold", 32) 
    
   
    pos_x_fecha = img_width * 0.60 
    pos_y_fecha = img_height * 0.20

    if expiration_date:
        texto_expiracion = f"VENCE: {expiration_date.strftime('%m/%y')}"
        c.drawString(pos_x_fecha, pos_y_fecha, texto_expiracion)

    c.save()