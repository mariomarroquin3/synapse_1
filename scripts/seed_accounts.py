"""
seed_accounts.py
─────────────────────────────────────────────────────────────
Crea y aprueba cuentas USD para todos los clientes (role_id=2)
que aún no tengan cuenta en la BD.

• Registra cada aprobación en audit_log mediante log_action().

Uso:
    python scripts/seed_accounts.py
"""

import os
import sys

# ── Directorio raíz del proyecto en sys.path ──────────────────────────────
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from models.user_model   import get_users_by_role_category
from models.account_model import create_account, approve_account, get_account_by_user
from services.audit_service import log_action

# ID del actor que realiza las aprobaciones (admin creado por seed_users.py)
# Si aún no existe, se usa 0 y audit_log lo ignorará.
SYSTEM_ACTOR_EMAIL = "admin@synapse.com"


def _get_admin_id() -> int:
    """Obtiene el Id_user del admin para registrar auditoría."""
    from models.user_model import get_user_by_email
    user = get_user_by_email(SYSTEM_ACTOR_EMAIL)
    if user:
        return int(user["Id_user"])
    return 0


def seed_accounts() -> None:
    clients = get_users_by_role_category(is_staff=False)
    if not clients:
        print("  ⚠️  No se encontraron clientes. Ejecuta seed_users.py primero.")
        return

    admin_id = _get_admin_id()
    if admin_id == 0:
        print("  ⚠️  Admin no encontrado. Las entradas de audit_log no se registrarán.")

    created  = 0
    approved = 0
    skipped  = 0

    for client in clients:
        user_id   = int(client["Id_user"])
        full_name = client["full_name"]

        # Verificar si ya tiene cuenta
        existing = get_account_by_user(user_id)
        if existing is not None:
            print(f"  ⏭  {full_name} (ID {user_id}) ya tiene cuenta. Se omite.")
            skipped += 1
            continue

        try:
            # 1. Crear cuenta (status_id=4 PENDIENTE)
            account_id = create_account(user_id, "USD")
            created += 1
            print(f"  📂 Cuenta creada → ID {account_id} para {full_name}")

            # 2. Aprobar cuenta (status_id=1 ACTIVO)
            approve_account(account_id)
            approved += 1
            print(f"  ✅ Cuenta {account_id} aprobada.")

            # 3. Registrar en audit_log
            if admin_id:
                log_action(
                    user_id=admin_id,
                    action="1",
                    details=f"Cuenta ID {account_id} aprobada para usuario '{full_name}' (ID {user_id}) — seed automático.",
                )

        except Exception as e:
            print(f"  ❌ Error procesando {full_name} (ID {user_id}): {e}")

    print(
        f"\n  Cuentas creadas: {created} | Aprobadas: {approved} | Omitidas: {skipped}"
    )


# ─────────────────────────────────────────────────────────────────────────
# Punto de entrada
# ─────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 55)
    print("  SEED — Tabla [account]")
    print("=" * 55)
    seed_accounts()
    print("\n" + "=" * 55)
    print("  Seed de cuentas finalizado.")
    print("=" * 55)
