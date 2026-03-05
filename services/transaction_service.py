"""
transaction_service.py
Servicio de negocio que orquesta transacciones y sus entradas contables.
"""

from config.database import get_connection
from models.ledger_model import create_ledger_entry, DEBIT, CREDIT
from datetime import datetime
from typing import Any

# Tipos de entrada para claridad externa
ENTRY_DEBIT  = DEBIT
ENTRY_CREDIT = CREDIT

# Límite de monto para aprobación automática en transferencias
LIMIT_AUTO_APPROVE = 10000.0

# ─────────────────────────────────────────────
# Helpers internos
# ─────────────────────────────────────────────

def _insert_transaction(cursor: Any, transaction_type_id: int, status_id: int,
                        description: str, created_by_user_id: int) -> int:
    """Inserta el registro principal en la tabla transaction y retorna su ID."""
    sql = """
        INSERT INTO [transaction]
            (transaction_type_id, status_id, description, created_by_user_id, transaction_date, processed_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """
    now = datetime.now()
    cursor.execute(sql, (transaction_type_id, status_id, description, created_by_user_id, now, now))
    
    cursor.execute("SELECT @@IDENTITY")
    result = cursor.fetchone()
    if result is None or result[0] is None:
        raise Exception("No se pudo obtener el ID de la transacción creada.")
    
    tx_id = int(result[0])
    print(f"[TX_SERVICE] Transacción insertada → Id_transaction={tx_id}")
    return tx_id

def _check_account_active(account_id: int, is_debit: bool = True) -> dict:
    """
    Verifica el estado de la cuenta con reglas granulares:
    - Débito (Salida): Solo permitido si status_id = 1 (Activo).
    - Crédito (Entrada): Permitido si es 1 (Activo) o 2 (Bloqueado).
    - Suspendido (3): Siempre denegado.
    """
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT status_id FROM account WHERE Id_account = ?", (account_id,))
        row = cursor.fetchone()
        
        if not row:
            return {"success": False, "error": f"La cuenta {account_id} no existe."}
        
        status_id = row[0]
        
        # REGLA 1: Suspendida siempre bloquea todo
        if status_id == 3:
            return {"success": False, "error": "Cuenta SUSPENDIDA. Operación no permitida."}
        
        # REGLA 2: Bloqueada solo permite ENTRADAS (Créditos), no SALIDAS (Débitos)
        if is_debit and status_id == 2:
            return {"success": False, "error": "Cuenta BLOQUEADA. No se permiten retiros ni envíos de dinero."}
        
        # REGLA 3: Si no es 1, 2 o 3, por defecto bloqueamos por seguridad
        if status_id not in (1, 2):
            return {"success": False, "error": "Estado de cuenta inválido para operar."}
            
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": f"Error verificando cuenta: {str(e)}"}
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

# ─────────────────────────────────────────────
# Consulta de Balance
# ─────────────────────────────────────────────

def get_account_balance(account_id: int) -> float:
    sql = '''
        SELECT entry_type, SUM(amount)
        FROM ledger_entry
        WHERE account_id = ?
        GROUP BY entry_type
    '''
    balance = 0.0
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(sql, (account_id,))
        rows = cursor.fetchall()
        
        for row in rows:
            entry_type = row[0]
            amount = float(row[1] or 0.0)
            if entry_type == CREDIT:
                balance += amount
            elif entry_type == DEBIT:
                balance -= amount
                
        return balance
    except Exception as e:
        print(f'[TX_SERVICE] ❌ Error calculando balance: {e}')
        return 0.0
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

# ─────────────────────────────────────────────
# Servicio principal - Transferencias
# ─────────────────────────────────────────────

def create_transfer(from_account_id: int, to_account_id: int,
                    amount: float, description: str,
                    created_by_user_id: int,
                    transaction_type_id: int = 1) -> dict[str, Any]:
    """
    Crea una transferencia bancaria con lógica de límite de aprobación.
    
    - Montos <= LIMIT_AUTO_APPROVE: Se procesan inmediatamente (status_id = 3)
    - Montos > LIMIT_AUTO_APPROVE: Requieren aprobación (status_id = 2, sin ledger)
    
    Args:
        from_account_id: Cuenta origen
        to_account_id: Cuenta destino
        amount: Monto a transferir
        description: Descripción de la transferencia
        created_by_user_id: Usuario que crea la transferencia
        transaction_type_id: Tipo de transacción (default=1)
        
    Returns:
        dict: {'success': bool, 'transaction_id': int, 'requires_approval': bool, 'error': str}
    """
    
    print(f"\n[TX_SERVICE] ── Iniciando transferencia (LIMIT: ${LIMIT_AUTO_APPROVE}) ───────────────")

    if amount <= 0:
        return {"success": False, "error": "El monto debe ser mayor a cero."}
    if from_account_id == to_account_id:
        return {"success": False, "error": "Cuentas origen y destino iguales."}

    # ORIGEN: Debe permitir DÉBITO (Solo Activa)
    sender_status = _check_account_active(from_account_id, is_debit=True)
    if not sender_status["success"]:
        return sender_status
        
    # DESTINO: Debe permitir CRÉDITO (Activa o Bloqueada)
    receiver_status = _check_account_active(to_account_id, is_debit=False)
    if not receiver_status["success"]:
        return {"success": False, "error": f"Error en cuenta destino: {receiver_status['error']}"}

    current_balance = get_account_balance(from_account_id)
    if current_balance < amount:
        return {"success": False, "error": f"Fondos insuficientes (${current_balance})"}

    conn = None
    cursor = None

    try:
        conn = get_connection()
        cursor = conn.cursor()

        # ─────────────────────────────────────────────────────────────────────
        # BIFURCACIÓN POR MONTO
        # ─────────────────────────────────────────────────────────────────────
        
        if amount <= LIMIT_AUTO_APPROVE:
            # ✅ TRANSFERENCIA AUTOMÁTICA (monto <= límite)
            print(f"[TX_SERVICE] Monto ${amount} <= Límite ${LIMIT_AUTO_APPROVE}. Aprobación automática.")
            
            status_id = 3  # Finalizada
            tx_id = _insert_transaction(cursor, transaction_type_id, status_id, description, created_by_user_id)
            
            # Inserta inmediatamente en ledger
            create_ledger_entry(cursor=cursor, transaction_id=tx_id, account_id=from_account_id, amount=amount, entry_type=DEBIT)
            create_ledger_entry(cursor=cursor, transaction_id=tx_id, account_id=to_account_id, amount=amount, entry_type=CREDIT)
            
            conn.commit()
            return {
                "success": True,
                "transaction_id": tx_id,
                "requires_approval": False,
                "status_id": status_id
            }
        
        else:
            # ⏳ TRANSFERENCIA PENDIENTE (monto > límite)
            print(f"[TX_SERVICE] Monto ${amount} > Límite ${LIMIT_AUTO_APPROVE}. Requiere aprobación.")
            
            status_id = 2  # Pendiente
            tx_id = _insert_transaction(cursor, transaction_type_id, status_id, description, created_by_user_id)
            
            # NO inserta en ledger, pero sí registra en transaction_approvals
            sql_approval = """
                INSERT INTO transaction_approvals
                    (transaction_id, from_account_id, to_account_id, amount, created_at)
                VALUES (?, ?, ?, ?, ?)
            """
            now = datetime.now()
            cursor.execute(sql_approval, (tx_id, from_account_id, to_account_id, amount, now))
            print(f"[TX_SERVICE] Registro de aprobación insertado para transacción {tx_id}")
            
            conn.commit()
            return {
                "success": True,
                "transaction_id": tx_id,
                "requires_approval": True,
                "status_id": status_id
            }

    except Exception as e:
        if conn: conn.rollback()
        return {"success": False, "error": str(e)}
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

# ─────────────────────────────────────────────
# Servicio principal - Transacciones simples
# ─────────────────────────────────────────────

def create_simple_transaction(account_id: int, amount: float,
                               entry_type: str, description: str,
                               created_by_user_id: int,
                               transaction_type_id: int, 
                               status_id: int = 3,
                               card_number: str | None = None,
                               pin: str | None = None) -> dict[str, Any]:
    """
    Crea una transacción simple (depósito, retiro, pago con tarjeta, etc).
    
    Si card_number se proporciona, valida la tarjeta antes de procesar.
    Si se usó tarjeta, se añaden los últimos 4 dígitos a la descripción.
    
    Args:
        account_id: Cuenta a afectar
        amount: Monto de la transacción
        entry_type: DEBIT o CREDIT
        description: Descripción del movimiento
        created_by_user_id: Usuario que crea la transacción
        transaction_type_id: Tipo de transacción (2=Retiro, 3=Depósito, 4=Pago)
        status_id: Estado de la transacción (default=3=Finalizada)
        card_number: Número de tarjeta (opcional, 16 dígitos)
        pin: PIN de tarjeta (requerido si card_number se proporciona)
        
    Returns:
        dict: {'success': bool, 'transaction_id': int | None, 'ledger_entry_id': int | None}
    """
    
    if amount <= 0:
        return {"success": False, "error": "El monto debe ser mayor a cero."}

    # Verificar estado basándose en si es salida (DEBIT) o entrada (CREDIT)
    is_debit = (entry_type == DEBIT)
    acc_status = _check_account_active(account_id, is_debit=is_debit)
    if not acc_status["success"]:
        return acc_status

    if is_debit:
        current_balance = get_account_balance(account_id)
        if current_balance < amount:
            return {"success": False, "error": f"Fondos insuficientes (${current_balance})"}

    conn = None
    cursor = None

    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # VALIDACIÓN OPCIONAL: Si se proporciona card_number, validar tarjeta
        last4_for_description = None
        if card_number is not None:
            print(f"[TX_SERVICE] Validando tarjeta para transacción...")
            if pin is None:
                return {"success": False, "error": "PIN es requerido cuando se proporciona card_number"}
            
            # Importar aquí para evitar dependencias circulares
            from services.card_service import validate_card_for_transaction
            
            card_validation = validate_card_for_transaction(cursor, card_number, pin)
            if not card_validation["success"]:
                return {
                    "success": False, 
                    "error": card_validation["error"]
                }
            
            # Verificar que la tarjeta pertenece a la cuenta correcta
            card_account_id = card_validation["account_id"]
            if card_account_id != account_id:
                return {
                    "success": False,
                    "error": f"La tarjeta no pertenece a esta cuenta (Tarjeta: {card_account_id}, Cuenta: {account_id})"
                }
            
            # Obtener últimos 4 dígitos para agregar a la descripción
            last4_for_description = card_validation.get("last4")
            print(f"[TX_SERVICE] ✅ Tarjeta validada correctamente")

        # Actualizar descripción si se usó tarjeta
        final_description = description
        if last4_for_description:
            final_description = f"{description} (Tarj. ****{last4_for_description})"

        tx_id = _insert_transaction(cursor, transaction_type_id, status_id, final_description, created_by_user_id)
        ledger_id = create_ledger_entry(cursor=cursor, transaction_id=tx_id, account_id=account_id, amount=amount, entry_type=entry_type)

        conn.commit()
        return {"success": True, "transaction_id": tx_id, "ledger_entry_id": ledger_id}

    except Exception as e:
        if conn: conn.rollback()
        return {"success": False, "error": str(e)}
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

def get_account_history_by_type(account_id: int, transaction_type_id: int) -> list:
    sql = '''
        SELECT t.transaction_date, t.description, l.amount, l.entry_type
        FROM (ledger_entry l
        INNER JOIN [transaction] t ON l.transaction_id = t.Id_transaction)
        WHERE l.account_id = ? AND t.transaction_type_id = ?
        ORDER BY t.transaction_date DESC
    '''
    history = []
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(sql, (account_id, transaction_type_id))
        rows = cursor.fetchall()
        for row in rows:
            history.append({"date": row[0], "description": row[1], "amount": float(row[2]), "entry_type": row[3]})
        return history
    except Exception:
        return []
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

# ─────────────────────────────────────────────
# Revisión y Aprobación de Transferencias
# ─────────────────────────────────────────────

def review_pending_transfer(transaction_id: int, admin_id: int, is_approved: bool, review_note: str | None = None) -> dict[str, Any]:
    """
    Revisa y procesa una transferencia pendiente de aprobación.
    
    Actualiza la tabla transaction_approvals con la decisión del administrador.
    - Si es_aprobada: Actualiza status a 3 (Finalizada) e inserta movimientos en ledger
    - Si es_rechazada: Actualiza status a 5 (Rechazada), sin tocar ledger
    
    Args:
        transaction_id: ID de la transacción a revisar
        admin_id: ID del administrador que revisa
        is_approved: True para aprobar, False para rechazar
        review_note: Nota opcional del administrador (aprobación/rechazo)
        
    Returns:
        dict: {'success': bool, 'message': str, 'error': str | None}
    """
    
    print(f"\\n[TX_SERVICE] ─── Revisando Transferencia Pendiente (TX: {transaction_id}) ───────────")
    
    conn = None
    cursor = None
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # 1. OBTENER DATOS DE LA APROBACIÓN
        sql_get_approval = "SELECT from_account_id, to_account_id, amount FROM transaction_approvals WHERE transaction_id = ?"
        cursor.execute(sql_get_approval, (transaction_id,))
        approval_row = cursor.fetchone()
        
        if not approval_row:
            return {"success": False, "error": f"No se encontró aprobación pendiente para transacción {transaction_id}"}
        
        from_account_id, to_account_id, amount = approval_row
        print(f"[TX_SERVICE] Aprobación encontrada: {from_account_id} → {to_account_id} por ${amount}")
        
        # 2. ACTUALIZAR transaction_approvals
        sql_update_approval = """
            UPDATE transaction_approvals
            SET admin_id = ?, review_note = ?, reviewed_at = ?
            WHERE transaction_id = ?
        """
        now = datetime.now()
        cursor.execute(sql_update_approval, (admin_id, review_note, now, transaction_id))
        print(f"[TX_SERVICE] Registro de aprobación actualizado")
        
        # 3. PROCESAR SEGÚN DECISIÓN
        if is_approved:
            # ✅ APROBADA: Actualizar status a 3 (Finalizada) + insertar ledger
            print(f"[TX_SERVICE] ✅ APROBADA por Admin {admin_id}")
            
            status_id = 3  # Finalizada
            sql_update_tx = "UPDATE [transaction] SET status_id = ? WHERE Id_transaction = ?"
            cursor.execute(sql_update_tx, (status_id, transaction_id))
            
            # Inserta los movimientos en ledger
            create_ledger_entry(
                cursor=cursor,
                transaction_id=transaction_id,
                account_id=from_account_id,
                amount=amount,
                entry_type=DEBIT
            )
            create_ledger_entry(
                cursor=cursor,
                transaction_id=transaction_id,
                account_id=to_account_id,
                amount=amount,
                entry_type=CREDIT
            )
            
            conn.commit()
            return {
                "success": True,
                "message": f"Transferencia {transaction_id} aprobada y procesada. Movimientos insertados en ledger."
            }
        
        else:
            # ❌ RECHAZADA: Actualizar status a 5 (Rechazada), SIN tocar ledger
            print(f"[TX_SERVICE] ❌ RECHAZADA por Admin {admin_id}")
            
            status_id = 5  # Rechazada
            sql_update_tx = "UPDATE [transaction] SET status_id = ? WHERE Id_transaction = ?"
            cursor.execute(sql_update_tx, (status_id, transaction_id))
            
            conn.commit()
            return {
                "success": True,
                "message": f"Transferencia {transaction_id} rechazada. No se insertaron movimientos."
            }
    
    except Exception as e:
        if conn: conn.rollback()
        print(f"[TX_SERVICE] ❌ Error durante revisión: {str(e)}")
        return {"success": False, "error": str(e)}
    finally:
        if cursor: cursor.close()
        if conn: conn.close()