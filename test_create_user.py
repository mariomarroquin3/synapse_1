from models.user_model import create_user, get_user_by_id #Se importaría desde user_model en lugar de auth_service si create_user estuviera ahí, pero lo moví a auth_service para centralizar lógica relacionada con usuarios.
from services.account_service import create_account_for_user
from utils.security import hash_password

def test_create_user_and_account():

    try:
        print("🔹 Creando usuario...")

        # Llama al servicio para crear usuario (aplica reglas y encripta contraseña)
        user_id = create_user(
            role_id=2,
            email="nuevo3@gmail.com",
            password_hash=hash_password("12456"),
            nit=None,
            gender="M",
            dui="11112121-3",
            full_name="Usuario Prueba",
            phone_number="7777-8858"
        )

        # Muestra el ID retornado
        get_user_by_id(user_id)  # Opcional: para verificar que se creó correctamente
        print("✅ Usuario creado:", user_id)
          # Ajusta según el formato real de tu función create_user
        print("🔹 Creando cuenta...")

        # Crea cuenta asociada al usuario
        create_account_for_user(user_id, "USD")

        print("✅ Cuenta creada correctamente.")

    except Exception as e:
        # Captura y muestra cualquier error
        print("❌ Error:", e)

# Ejecuta la función solo si el archivo se corre directamente
if __name__ == "__main__":
    test_create_user_and_account()
    #nahum test