import os
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib import colors


from datetime import datetime

def generate_card_pdf(card_data, id_account):
    # Manejar el caso si card_data es un diccionario (del modelo) o una tupla
    if isinstance(card_data, dict):
        last4 = card_data.get('card_number_last4', '0000')
        expiration_date = card_data.get('expiration_date')
        full_name = card_data.get('full_name', 'TITULAR')
    else:
        # Por compatibilidad con versiones anteriores que usaban tuplas
        _, last4, expiration_date, full_name = card_data

    image_path = "plantilla_tarjeta.png"
    image = ImageReader(image_path)
    img_width, img_height = image.getSize()

    # ==========================================================
    # CREAR CARPETA SI NO EXISTE
    # ==========================================================
    folder_name = "tarjetas_generadas"
    os.makedirs(folder_name, exist_ok=True)

    # Limpiar nombre (quitar espacios y caracteres raros)
    safe_name = full_name.replace(" ", "_")

    # Nombre dinámico del archivo
    file_name = f"tarjeta_{safe_name}_cuenta_{id_account}.pdf"
    file_path = os.path.join(folder_name, file_name)

    # Crear PDF
    c = canvas.Canvas(file_path, pagesize=(img_width, img_height))
    c.drawImage(image_path, 0, 0, width=img_width, height=img_height)

    # ==========================================================
    # FRENTE (Nombre y Cuenta - Blanco)
    # ==========================================================
    c.setFillColor(colors.white)
    
    # Nombre del titular
    c.setFont("Helvetica-Bold", 38)
    c.drawString(img_width * 0.18, img_height * 0.67, full_name.upper())

    # Número de cuenta
    c.setFont("Helvetica-Bold", 41)
    c.drawString(img_width * 0.20, img_height * 0.72, " ".join(last4))

    # ==========================================================
    # REVERSO - FECHA
    # ==========================================================
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 32)

    pos_x_fecha = img_width * 0.60
    pos_y_fecha = img_height * 0.20

    if expiration_date:
        # Si ya es un objeto datetime
        if hasattr(expiration_date, 'strftime'):
            texto_expiracion = f"VENCE: {expiration_date.strftime('%m/%y')}"
        # Si es un string (que a veces devuelve Access)
        else:
            try:
                # Intentar parsear si viene como string
                if isinstance(expiration_date, str):
                    # Formato típico de Access o string simple
                    dt = datetime.strptime(expiration_date.split()[0], '%Y-%m-%d')
                    texto_expiracion = f"VENCE: {dt.strftime('%m/%y')}"
                else:
                    texto_expiracion = f"VENCE: {str(expiration_date)}"
            except:
                texto_expiracion = f"VENCE: {str(expiration_date)}"
        
        c.drawString(pos_x_fecha, pos_y_fecha, texto_expiracion)

    c.save()

    print(f"✅ Tarjeta guardada en: {file_path}")