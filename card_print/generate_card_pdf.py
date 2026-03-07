import io
import os
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib import colors
from datetime import datetime


def draw_text_with_outline(c, text, x, y, font, size):
    """
    Dibuja texto con relleno blanco y borde negro
    para que siempre sea visible.
    """
    text_obj = c.beginText()
    text_obj.setTextOrigin(x, y)
    text_obj.setFont(font, size)

    text_obj.setFillColor(colors.white)
    text_obj.setStrokeColor(colors.black)

    text_obj.setTextRenderMode(2)  # fill + stroke
    c.setLineWidth(1.2)

    text_obj.textLine(text)
    c.drawText(text_obj)


def generate_card_pdf(card_data, id_account):

    # ==========================================================
    # EXTRAER DATOS
    # ==========================================================
    if isinstance(card_data, dict):
        card_number = card_data.get('card_number', '0000000000000000')
        expiration_date = card_data.get('expiration_date')
        full_name = card_data.get('full_name', 'TITULAR')
    else:
        # Compatibilidad con tuplas
        _, card_number, expiration_date, full_name = card_data

    # Formatear número de tarjeta
    formatted_number = " ".join(card_number[i:i+4] for i in range(0, len(card_number), 4))

    # ==========================================================
    # CARGAR IMAGEN DE TARJETA
    # ==========================================================
    image_path = "plantilla_tarjeta.png"
    image = ImageReader(image_path)
    img_width, img_height = image.getSize()

    # ==========================================================
    # CREAR PDF EN MEMORIA
    # ==========================================================
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=(img_width, img_height))

    # Fondo de la tarjeta
    c.drawImage(image_path, 0, 0, width=img_width, height=img_height)

    # ==========================================================
    # NOMBRE DEL TITULAR
    # ==========================================================
    draw_text_with_outline(
        c,
        full_name.upper(),
        img_width * 0.18,
        img_height * 0.67,
        "Helvetica-Bold",
        38
    )

    # ==========================================================
    # NUMERO DE TARJETA
    # ==========================================================
    draw_text_with_outline(
        c,
        formatted_number,
        img_width * 0.20,
        img_height * 0.72,
        "Courier-Bold",
        41
    )

    # ==========================================================
    # FECHA DE EXPIRACIÓN
    # ==========================================================
    pos_x_fecha = img_width * 0.60
    pos_y_fecha = img_height * 0.20

    if expiration_date:

        if hasattr(expiration_date, 'strftime'):
            texto_expiracion = f"VENCE: {expiration_date.strftime('%m/%y')}"

        else:
            try:
                if isinstance(expiration_date, str):
                    dt = datetime.strptime(expiration_date.split()[0], '%Y-%m-%d')
                    texto_expiracion = f"VENCE: {dt.strftime('%m/%y')}"
                else:
                    texto_expiracion = f"VENCE: {str(expiration_date)}"
            except:
                texto_expiracion = f"VENCE: {str(expiration_date)}"

        draw_text_with_outline(
            c,
            texto_expiracion,
            pos_x_fecha,
            pos_y_fecha,
            "Helvetica-Bold",
            32
        )

    # ==========================================================
    # FINALIZAR PDF
    # ==========================================================
    c.save()

    buffer.seek(0)

    return buffer