import random
import sys
import os
from typing import List, Dict, Any

# 1. Configuración de rutas para evitar "ModuleNotFoundError"
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.database import get_cursor
from services.transaction_service import create_simple_transaction, ENTRY_DEBIT

# --- CONFIGURACIÓN DE LA SIMULACIÓN ---
ITERACIONES = 15
TIPO_TX_PAGO = 4  # ID para 'Pago con Tarjeta' en tu tabla de tipos

def obtener_datos_reales_bd() -> List[Dict[str, Any]]:
    """
    Trae tarjetas activas cruzándolas con su cuenta para obtener el user_id real.
    Esto evita el error de integridad referencial (FK) en la tabla 'user'.
    """
    query = """
        SELECT 
            c.account_id, 
            a.user_id, 
            c.card_number_last4, 
            c.card_token 
        FROM [card] c
        INNER JOIN [account] a ON c.account_id = a.Id_account
        WHERE c.is_active = True
    """
    try:
        with get_cursor() as cursor:
            cursor.execute(query)
            filas = cursor.fetchall()
            return [
                {
                    "account_id": row[0],
                    "user_id": int(row[1]),
                    "last4": str(row[2]),
                    "token": str(row[3])
                } for row in filas
            ]
    except Exception as e:
        print(f"❌ Error al leer la base de datos: {e}")
        return []

def ejecutar_simulacion():
    print(f"🚀 Iniciando Simulación de Pagos...")
    
    tarjetas = obtener_datos_reales_bd()
    
    if not tarjetas:
        print("❌ No hay tarjetas disponibles para procesar.")
        return

    print(f"✅ Se encontraron {len(tarjetas)} tarjetas activas.\n")

    for i in range(1, ITERACIONES + 1):
        # Selección aleatoria de datos
        t = random.choice(tarjetas)
        monto = round(random.uniform(5.50, 150.00), 2)
        comercio = random.choice(["Netflix", "Amazon", "Starbucks", "Gasolinera", "Supermercado"])
        
        print(f"👉 [{i}/{ITERACIONES}] Procesando Pago: **** {t['last4']} | {comercio} | ${monto}")

        try:
            # Ejecución de la transacción

            resultado = create_simple_transaction(
                account_id=t["account_id"],
                amount=monto,
                entry_type=ENTRY_DEBIT,
                description=f"Compra en {comercio}",
                created_by_user_id=t["user_id"], # user_id real del dueño
                transaction_type_id=TIPO_TX_PAGO,
                card_number=t["last4"],          # Usamos last4 para buscar
                pin=t["token"]            # Usamos token para validar
            )

            if resultado.get("success"):
                print(f"   ✅ APROBADO")
            else:
                print(f"   ⚠️ RECHAZADO: {resultado.get('error')}")

        except Exception as e:
            print(f"   ❌ ERROR CRÍTICO: {e}")

    print("\n--- Simulación Finalizada ---")

if __name__ == "__main__":
    ejecutar_simulacion()