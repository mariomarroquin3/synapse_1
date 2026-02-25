"""
pages/transfer.py
Página de Streamlit para ejecutar transferencias entre cuentas
y depósitos/retiros simples. Usa transaction_service para orquestar
la lógica de ledger contable.
"""

import streamlit as st
from services.transaction_service import (
    create_transfer,
    create_simple_transaction,
    ENTRY_DEBIT,
    ENTRY_CREDIT,
)
from models.ledger_model import get_ledger_entries_by_transaction


# ─────────────────────────────────────────────
# Helpers de UI
# ─────────────────────────────────────────────

def _show_ledger_entries(transaction_id: int):
    """Muestra en pantalla las entradas de ledger de una transacción."""
    entries = get_ledger_entries_by_transaction(transaction_id)
    if not entries:
        st.warning("No se encontraron entradas de ledger para esta transacción.")
        return

    st.subheader(f"📒 Entradas de Ledger — Transacción #{transaction_id}")
    for e in entries:
        col1, col2, col3 = st.columns(3)
        col1.metric("Cuenta",  e["account_id"])
        col2.metric("Monto",   f"Q {e['amount']:,.2f}")
        col3.metric("Fecha",   str(e["created_at"]))


# ─────────────────────────────────────────────
# Página principal
# ─────────────────────────────────────────────

def show():
    st.title("💸 Movimientos y Transferencias")

    # Verificar sesión activa
    if "user" not in st.session_state:
        st.error("Debes iniciar sesión para realizar operaciones.")
        st.stop()

    user = st.session_state["user"]
    user_id = user["Id_user"]

    tab_transfer, tab_simple = st.tabs(["🔁 Transferencia", "💰 Depósito / Retiro"])

    # ── Tab 1: Transferencia entre cuentas ──────────────────────────────
    with tab_transfer:
        st.subheader("Transferencia entre cuentas")
        st.caption("Genera 2 entradas de ledger: débito en origen, crédito en destino.")

        with st.form("form_transfer"):
            from_account = st.number_input("ID cuenta origen",  min_value=1, step=1)
            to_account   = st.number_input("ID cuenta destino", min_value=1, step=1)
            amount       = st.number_input("Monto (Q)", min_value=0.01, format="%.2f")
            description  = st.text_input("Descripción", placeholder="Pago de factura #123")
            submitted    = st.form_submit_button("Ejecutar transferencia")

        if submitted:
            with st.spinner("Procesando transferencia..."):
                result = create_transfer(
                    from_account_id=int(from_account),
                    to_account_id=int(to_account),
                    amount=amount,
                    description=description,
                    created_by_user_id=user_id,
                )

            if result["success"]:
                st.success(f"✅ Transferencia exitosa — ID Transacción: {result['transaction_id']}")

                # Detalle de entradas
                entries = result["ledger_entries"]
                col1, col2 = st.columns(2)
                with col1:
                    st.info(
                        f"**DÉBITO**\n\n"
                        f"Cuenta: `{entries['debit']['account_id']}`\n\n"
                        f"Ledger ID: `{entries['debit']['id']}`"
                    )
                with col2:
                    st.info(
                        f"**CRÉDITO**\n\n"
                        f"Cuenta: `{entries['credit']['account_id']}`\n\n"
                        f"Ledger ID: `{entries['credit']['id']}`"
                    )

                _show_ledger_entries(result["transaction_id"])

            else:
                st.error(f"❌ Error: {result['error']}")

    # ── Tab 2: Transacción simple (depósito o retiro) ────────────────────
    with tab_simple:
        st.subheader("Depósito o Retiro")
        st.caption("Genera 1 entrada de ledger: crédito para depósito, débito para retiro.")

        with st.form("form_simple"):
            account_id  = st.number_input("ID de cuenta", min_value=1, step=1)
            op_type     = st.radio("Tipo de operación",
                                   options=["Depósito (crédito)", "Retiro (débito)"])
            amount_s    = st.number_input("Monto (Q) ", min_value=0.01, format="%.2f")
            description_s = st.text_input("Descripción ", placeholder="Depósito en efectivo")
            submitted_s   = st.form_submit_button("Ejecutar operación")

        if submitted_s:
            entry_type = ENTRY_CREDIT if "Depósito" in op_type else ENTRY_DEBIT

            with st.spinner("Procesando operación..."):
                result = create_simple_transaction(
                    account_id=int(account_id),
                    amount=amount_s,
                    entry_type=entry_type,
                    description=description_s,
                    created_by_user_id=user_id,
                )

            if result["success"]:
                st.success(
                    f"✅ Operación exitosa — ID Transacción: {result['transaction_id']} | "
                    f"Ledger ID: {result['ledger_entry_id']}"
                )
                _show_ledger_entries(result["transaction_id"])
            else:
                st.error(f"❌ Error: {result['error']}")


# Punto de entrada directo (streamlit run pages/transfer.py)
if __name__ == "__main__":
    show()
