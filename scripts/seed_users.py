"""
seed_users.py
-------------------------------------------------------------
# Pobla la tabla [user] con usuarios de prueba usando Faker.
# Genera nombres en espanol con genero correcto (M/F).
# Formatos de DUI y NIT: ########-#
# Columnas en BD: dui, nit (minusculas).
# Crea tambien UN usuario admin (role_id=1) con contrasena 123456.

Uso:
    python scripts/seed_users.py
"""

import os
import sys
import random
import string
from faker import Faker

# -- Directorio raiz del proyecto en sys.path ------------------------------
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from models.user_model import create_user, get_user_by_email, get_user_by_dui
from utils.security import hash_password

fake = Faker("es_MX")

# -------------------------------------------------------------------------
# Helpers de generacion de datos
# -------------------------------------------------------------------------

def _gen_dui() -> str:
    """Genera un DUI con formato ########-# (9 digitos separados por guion)."""
    nums = "".join(random.choices(string.digits, k=8))
    check = random.choice(string.digits)
    return f"{nums}-{check}"


def _gen_nit() -> str:
    """
    NIT usa el mismo formato que DUI: ########-#
    (segun la aclaracion del usuario).
    """
    return _gen_dui()


def _gen_phone() -> str:
    """Telefono salvadoreno tipo 7XXX-XXXX o 6XXX-XXXX."""
    prefix = random.choice(["6", "7"])
    rest = "".join(random.choices(string.digits, k=3))
    last = "".join(random.choices(string.digits, k=4))
    return f"{prefix}{rest}-{last}"


def _unique_dui(used: set) -> str:
    while True:
        v = _gen_dui()
        if v not in used and get_user_by_dui(v) is None:
            used.add(v)
            return v


def _unique_phone(used: set) -> str:
    from models.user_model import get_user_by_phone
    while True:
        v = _gen_phone()
        if v not in used and get_user_by_phone(v) is None:
            used.add(v)
            return v


# -------------------------------------------------------------------------
# Creacion de usuarios clientes
# -------------------------------------------------------------------------

def seed_clients(n: int) -> None:
    """Crea `n` usuarios cliente (role_id=2) con gender alternado M/F."""
    used_duis: set = set()
    used_phones: set = set()
    used_emails: set = set()

    created = 0
    skipped = 0

    # Dividir en mitades M/F
    half = n // 2
    genders = ["M"] * half + ["F"] * (n - half)
    random.shuffle(genders)

    for gender in genders:
        # 1. Generamos el nombre segun el genero usando metodos especificos
        if gender == "M":
            full_name = fake.name_male()
        else:
            full_name = fake.name_female()

        # Email unico, basado en nombre + numeros aleatorios
        base_email = (
            full_name.lower()
            .replace(" ", ".")
            .replace("á", "a").replace("é", "e").replace("í", "i")
            .replace("ó", "o").replace("ú", "u").replace("ñ", "n")
        )
        suffix = "".join(random.choices(string.digits, k=4))
        email = f"{base_email}{suffix}@gmail.com"
        # Garantizar unicidad en sesion
        while email in used_emails or get_user_by_email(email) is not None:
            suffix = "".join(random.choices(string.digits, k=4))
            email = f"{base_email}{suffix}@gmail.com"
        used_emails.add(email)

        dui   = _unique_dui(used_duis)
        nit   = _gen_nit()      # NIT no requiere ser unico por DUI
        phone = _unique_phone(used_phones)
        pwd   = hash_password("Password123!")   # contrasena base para todos los clientes

        try:
            uid = create_user(
                role_id=2,
                email=email,
                password_hash=pwd,
                nit=nit,
                dui=dui,
                full_name=full_name,
                gender=gender,
                phone_number=phone,
                is_active=True,
            )
            print(f"  OK [{gender}] {full_name} > ID {uid} | {email}")
            created += 1
        except Exception as e:
            print(f"  ERROR creando {full_name}: {e}")
            skipped += 1

    print(f"\n  Clientes creados: {created} | Omitidos: {skipped}")


# -------------------------------------------------------------------------
# Creacion de usuario Admin
# -------------------------------------------------------------------------

def seed_admin() -> None:
    """Crea un usuario administrador con role_id=1 y contrasena 123456."""
    admin_email = "admin@synapse.com"

    if get_user_by_email(admin_email) is not None:
        print(f"  AVISO: Admin '{admin_email}' ya existe. Se omite.")
        return

    dui   = _gen_dui()
    nit   = _gen_nit()
    phone = _gen_phone()
    pwd   = hash_password("123456")

    try:
        uid = create_user(
            role_id=1,
            email=admin_email,
            password_hash=pwd,
            nit=nit,
            dui=dui,
            full_name="Administrador Principal",
            gender="M",
            phone_number=phone,
            is_active=True,
        )
        print(f"  OK Admin creado > ID {uid} | {admin_email} | contrasena: 123456")
    except Exception as e:
        print(f"  ERROR creando admin: {e}")


# -------------------------------------------------------------------------
# Punto de entrada
# -------------------------------------------------------------------------

if __name__ == "__main__":
    print("=======================================================")
    print("  SEED - Tabla [user]")
    print("=======================================================")

    try:
        n_str = input("¿Cuantos usuarios cliente deseas crear? [default=20]: ").strip()
        n = int(n_str) if n_str else 20
        if n <= 0:
            raise ValueError("El numero debe ser positivo.")
    except ValueError as ve:
        print(f"Valor inválido ({ve}). Usando 20 por defecto.")
        n = 20

    print(f"\n> Creando {n} clientes...\n")
    seed_clients(n)

    print("\n> Creando usuario admin...\n")
    seed_admin()

    print("\n" + "=" * 55)
    print("  Seed de usuarios finalizado.")
    print("=" * 55)
