"""
test_transactions.py

"""

from services.transaction_service import (
    create_transfer,
    create_simple_transaction,
    ENTRY_DEBIT,
    ENTRY_CREDIT
)

def test_transfer():
    print("\n===== TEST TRANSFER =====")

    result = create_transfer(
        from_account_id=1,      # Ajusta IDs reales
        to_account_id=3,
        transaction_type_id=1,
        amount=100.00,
        description="Test transfer script",
        created_by_user_id=19  # Usuario existente en tu DB
    )
    # Debe evaluarse pertinencia de id_cuenta al usuario

    print("Resultado transferencia:")
    print(result)


def test_deposit():
    print("\n===== TEST DEPOSIT =====")

    result = create_simple_transaction(
        account_id=1,
        amount=50.00,
        transaction_type_id=3,
        entry_type=ENTRY_CREDIT,
        description="Test deposit script",
        created_by_user_id=19
    )

    print("Resultado depósito:")
    print(result)


def test_withdraw():
    print("\n===== TEST WITHDRAW =====")

    result = create_simple_transaction(
        account_id=1,
        amount=25.00,
        transaction_type_id=2,
        entry_type=ENTRY_DEBIT,
        description="Test withdraw script",
        created_by_user_id=19
    )

    print("Resultado retiro:")
    print(result)


if __name__ == "__main__":
    print("====================================")
    print("   INICIANDO PRUEBAS DE TRANSACCIONES")
    print("====================================")

    test_transfer()
    test_deposit()
    test_withdraw()

    print("\nPruebas finalizadas.")