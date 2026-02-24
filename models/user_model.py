from config.database import get_cursor


def create_user(role_id: int,
                email: str,
                password_hash: str,
                nit: str | None,
                dui: str,
                full_name: str,
                phone_number: str | None,
                is_active: bool = True) -> None:
    """
    Inserta un nuevo usuario en la base de datos.
    No realiza validaciones de negocio.
    """

    print("[DEBUG] Creando usuario en base de datos...")

    query = """
        INSERT INTO user (
            role_id,
            email,
            password_hash,
            NIT,
            DUI,
            full_name,
            phone_number,
            created_at,
            updated_at,
            is_active
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, Now(), Now(), ?)
    """

    with get_cursor(commit=True) as cursor:
        cursor.execute(
            query,
            (
                role_id,
                email,
                password_hash,
                nit,
                dui,
                full_name,
                phone_number,
                is_active
            )
        )

    print("[DEBUG] Usuario creado correctamente.")


def get_user_by_email(email: str):
    """
    Retorna un usuario por email.
    Devuelve None si no existe.
    """

    print("[DEBUG] Buscando usuario por email...")

    query = "SELECT * FROM user WHERE email = ?"

    with get_cursor() as cursor:
        cursor.execute(query, (email,))
        row = cursor.fetchone()

        if row:
            print("[DEBUG] Usuario encontrado.")
        else:
            print("[DEBUG] Usuario no encontrado.")

        return row


def get_user_by_id(user_id: int):
    """
    Retorna un usuario por ID.
    """

    print("[DEBUG] Buscando usuario por ID...")

    query = "SELECT * FROM user WHERE id = ?"

    with get_cursor() as cursor:
        cursor.execute(query, (user_id,))
        return cursor.fetchone()


def update_last_login(user_id: int) -> None:
    """
    Actualiza la fecha de último login.
    """

    print("[DEBUG] Actualizando último login...")

    query = """
        UPDATE user
        SET updated_at = Now()
        WHERE id = ?
    """

    with get_cursor(commit=True) as cursor:
        cursor.execute(query, (user_id,))

    print("[DEBUG] Último login actualizado.")