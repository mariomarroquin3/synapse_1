from faker import Faker
import random
from models.user_model import create_user
from services.account_service import create_account_for_user
from utils.security import hash_password

fake = Faker("es_ES")


def generar_dui():
    """Genera DUI con formato XXXXXXXX-X"""
    numero = random.randint(10000000, 99999999)
    verificador = random.randint(0, 9)
    return f"{numero}-{verificador}"


def generar_telefono_sv():
    """Genera teléfono válido de El Salvador +503 7XXX-XXXX"""
    
    primer_digito = random.choice(["6", "7"])
    resto = str(random.randint(1000000, 9999999))  # exactamente 7 dígitos
    
    numero = primer_digito + resto  # ahora siempre serán 8 dígitos
    
    return f"+503 {numero[:4]}-{numero[4:]}"


def generar_usuario():
    """Genera datos ficticios coherentes"""

    # Primero elegimos género
    gender = random.choice(["M", "F"])

    # Luego el nombre corresponde al género
    if gender == "M":
        full_name = fake.name_male()
    else:
        full_name = fake.name_female()

    email = fake.unique.email()
    phone = generar_telefono_sv()

    return {
        "role_id": 2,
        "email": email,
        "password_hash": hash_password("123456"),
        "nit": None,
        "gender": gender,
        "dui": generar_dui(),
        "full_name": full_name,
        "phone_number": phone
    }


def crear_usuarios_masivos(cantidad):
    for i in range(cantidad):
        try:
            datos = generar_usuario()

            user_id = create_user(**datos)
            create_account_for_user(user_id, "USD")

            print(f"✅ Usuario {i+1} creado - ID: {user_id}")

        except Exception as e:
            print(f"❌ Error en usuario {i+1}: {e}")


if __name__ == "__main__":
    cantidad = int(input("¿Cuántos usuarios quieres crear? "))
    crear_usuarios_masivos(cantidad)