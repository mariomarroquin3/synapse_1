from services.transaction_service import create_transfer, create_simple_transaction, get_account_balance, ENTRY_CREDIT

# ==========================================
# ⚙️ SETUP: Put your real database IDs here
# ==========================================
ACCOUNT_A = 1  # Assume this is an ACTIVE account
ACCOUNT_B = 3  # Assume this is an ACTIVE account
USER_ID = 19    # The user executing the action

def run_tests():
    print("🚀 INICIANDO BATERÍA DE PRUEBAS DE TRANSFERENCIAS...\n")

    # ---------------------------------------------------------
    # PRUEBA 0: Preparar el terreno (Darle dinero a la Cuenta A)
    # ---------------------------------------------------------
    print("▶️ PRE-TEST: Fondeando Cuenta A para las pruebas...")
    create_simple_transaction(
        account_id=ACCOUNT_A, amount=500.0, entry_type=ENTRY_CREDIT,
        description="Fondeo inicial para pruebas", created_by_user_id=USER_ID, transaction_type_id=2
    )
    balance_a = get_account_balance(ACCOUNT_A)
    print(f"   Saldo actual Cuenta A: ${balance_a}\n")


    # ---------------------------------------------------------
    # PRUEBA 1: Transferencia Exitosa (Happy Path)
    # ---------------------------------------------------------
    print("▶️ TEST 1: Transferencia válida ($50 de A -> B)")
    res1 = create_transfer(ACCOUNT_A, ACCOUNT_B, 50.0, "Pago de cena", USER_ID)
    if res1["success"]:
        print("   ✅ ÉXITO: La transferencia pasó correctamente.")
    else:
        print(f"   ❌ FALLO INESPERADO: {res1['error']}")
    print("-" * 40)


    # ---------------------------------------------------------
    # PRUEBA 2: Fondos Insuficientes (Sad Path)
    # ---------------------------------------------------------
    print("▶️ TEST 2: Intentar transferir más de lo que hay ($999,999 de A -> B)")
    res2 = create_transfer(ACCOUNT_A, ACCOUNT_B, 999999.0, "Intento de fraude", USER_ID)
    if not res2["success"]:
        print(f"   ✅ ÉXITO (Bloqueado correctamente): {res2['error']}")
    else:
        print("   ❌ PELIGRO: El sistema permitió sobregirar la cuenta!")
    print("-" * 40)


    # ---------------------------------------------------------
    # PRUEBA 3: Monto negativo o cero (Sad Path)
    # ---------------------------------------------------------
    print("▶️ TEST 3: Intentar transferir $0 o negativo")
    res3 = create_transfer(ACCOUNT_A, ACCOUNT_B, -100.0, "Hack hacker", USER_ID)
    if not res3["success"]:
        print(f"   ✅ ÉXITO (Bloqueado correctamente): {res3['error']}")
    else:
        print("   ❌ PELIGRO: El sistema permitió montos negativos!")
    print("-" * 40)


    # ---------------------------------------------------------
    # PRUEBA 4: Transferencia a la misma cuenta (Sad Path)
    # ---------------------------------------------------------
    print("▶️ TEST 4: Transferir de Cuenta A hacia Cuenta A")
    res4 = create_transfer(ACCOUNT_A, ACCOUNT_A, 10.0, "Auto-pago", USER_ID)
    if not res4["success"]:
        print(f"   ✅ ÉXITO (Bloqueado correctamente): {res4['error']}")
    else:
        print("   ❌ PELIGRO: El sistema permitió transferir a la misma cuenta!")
    print("-" * 40)


    # ---------------------------------------------------------
    # PRUEBA 5: Verificar Balances Finales
    # ---------------------------------------------------------
    print("▶️ TEST 5: Verificación de Integridad Matemática")
    final_balance_a = get_account_balance(ACCOUNT_A)
    print(f"   Saldo final Cuenta A: ${final_balance_a} (Debería ser ${balance_a - 50.0})")
    
    if final_balance_a == (balance_a - 50.0):
        print("   ✅ MATEMÁTICA PERFECTA. El ledger está cuadrado.")
    else:
        print("   ❌ ALERTA: Fuga de dinero en el ledger.")
    print("-" * 40)

if __name__ == "__main__":
    run_tests()