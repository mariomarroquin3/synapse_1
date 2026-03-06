from models.card_model import get_card_with_user
from card_print.generate_card_pdf import generate_card_pdf

account_id = 218  # Cambia por la cuenta que quieras probar

card = get_card_with_user(account_id)

if card:
    generate_card_pdf(card, account_id) 
    print("Tarjeta generada correctamente")
else:
    print("No se encontró tarjeta para esa cuenta")