# Muestra el ID retornado
from models.user_model import get_user_by_id
from services.account_service import create_account_for_user


get_user_by_id(21) 
create_account_for_user(21, "USD")

print("✅ Cuenta creada correctamente.")