# Card Validation Flow Diagrams

## 1. Simple Transaction WITH Card Validation

```
START: create_simple_transaction(
    account_id=1,
    amount=50.00,
    card_number="4532...",
    card_token="tok_abc..."
)
    ↓
═══════════════════════════════════════════════════════
    PRE-VALIDATIONS
═══════════════════════════════════════════════════════
    ↓
    Amount > 0?
    ├─ NO  → Return error "El monto debe ser mayor..."
    └─ YES → Continue
    ↓
    Check account status
    ├─ SUSPENDED → Return error "SUSPENDIDA"
    ├─ BLOCKED & is_debit → Return error "No se permiten retiros"
    └─ OK → Continue
    ↓
    Check balance (if DEBIT)
    ├─ Insufficient → Return error "Fondos insuficientes"
    └─ OK → Continue
═══════════════════════════════════════════════════════
    OPEN ATOMIC TRANSACTION
═══════════════════════════════════════════════════════
    ↓
    conn = get_connection()
    cursor = conn.cursor()
    ↓
    IF card_number is NOT None:
    ┌───────────────────────────────────────────────┐
    │ VALIDATE CARD VALIDATION BLOCK                │
    ├───────────────────────────────────────────────┤
    │                                               │
    │   SELECT [Id_card], [account_id],            │
    │          [card_token], [is_active],          │
    │          [expiration_date]                   │
    │   FROM [card]                                │
    │   WHERE [card_number] = ?                    │
    │         ↓                                     │
    │   Card exists?                               │
    │   ├─ NO  → ❌ ROLLBACK                       │
    │   │        Return "Tarjeta no encontrada"   │
    │   └─ YES → Continue                          │
    │         ↓                                     │
    │   is_active = True?                          │
    │   ├─ NO  → ❌ ROLLBACK                       │
    │   │        Return "La tarjeta está bloqueada"│
    │   └─ YES → Continue                          │
    │         ↓                                     │
    │   expiration_date > NOW()?                   │
    │   ├─ NO  → ❌ ROLLBACK                       │
    │   │        Return "Tarjeta vencida"         │
    │   └─ YES → Continue                          │
    │         ↓                                     │
    │   stored_token == input_token?               │
    │   ├─ NO  → ❌ ROLLBACK                       │
    │   │        Return "Token inválido"          │
    │   └─ YES → Continue                          │
    │         ↓                                     │
    │   card.account_id == tx.account_id?          │
    │   ├─ NO  → ❌ ROLLBACK                       │
    │   │        Return "Tarjeta no pertenece..."  │
    │   └─ YES → Continue (Card Valid! ✅)         │
    │                                              │
    └───────────────────────────────────────────────┘
    ELSE (card_number is None):
        Skip card validation, proceed
    ↓
═══════════════════════════════════════════════════════
    CREATE TRANSACTION & LEDGER
═══════════════════════════════════════════════════════
    ↓
    INSERT INTO [transaction]
    (transaction_type_id, status_id, description, ...)
    VALUES (...)
    ↓
    tx_id = SELECT @@IDENTITY
    ↓
    INSERT INTO ledger_entry
    (transaction_id, account_id, entry_type, amount, ...)
    VALUES (?, ?, ?, ?, ...)
    ↓
    ledger_id = SELECT @@IDENTITY
═══════════════════════════════════════════════════════
    COMMIT ATOMIC TRANSACTION
═══════════════════════════════════════════════════════
    ↓
    conn.commit()
    ↓
    Return {
        "success": True,
        "transaction_id": tx_id,
        "ledger_entry_id": ledger_id
    }
    ↓
    END ✅
```

---

## 2. Card Validation Function

```
START: validate_card_for_transaction(
    cursor,
    card_number="4532...",
    input_token="tok_abc..."
)
    ↓
    Query [card] table
    SELECT [Id_card], [account_id],
           [card_token], [is_active],
           [expiration_date]
    FROM [card]
    WHERE [card_number] = ?
    ↓
    ┌─────────────────────────────────────────────┐
    │         VALIDATION CHAIN                    │
    └─────────────────────────────────────────────┘
    ↓
    V1: Row exists?
    ├─ ❌ NO → Return {
    │              "success": False,
    │              "error": "Tarjeta no encontrada",
    │              "account_id": None
    │           }
    └─ ✅ YES → Continue
    ↓
    V2: is_active == True?
    ├─ ❌ NO → Return {
    │              "success": False,
    │              "error": "La tarjeta está bloqueada",
    │              "account_id": None
    │           }
    └─ ✅ YES → Continue
    ↓
    V3: expiration_date > NOW()?
    ├─ ❌ NO → Return {
    │              "success": False,
    │              "error": "Tarjeta vencida",
    │              "account_id": None
    │           }
    └─ ✅ YES → Continue
    ↓
    V4: card_token == input_token?
    ├─ ❌ NO → Return {
    │              "success": False,
    │              "error": "Token de tarjeta inválido",
    │              "account_id": None
    │           }
    └─ ✅ YES → Continue
    ↓
    ALL VALIDATIONS PASSED! ✅
    ↓
    Return {
        "success": True,
        "account_id": card_account_id,  # Extract from row
        "error": None
    }
    ↓
    END ✅
```

---

## 3. Update Card Status Function

```
START: update_card_active_status(
    cursor,
    card_id=5,
    status=False  # Block the card
)
    ↓
    ⚠️ NOTE: Caller must provide active cursor
           in an open transaction
    ↓
    Execute UPDATE statement:
    
    UPDATE [card]
    SET [is_active] = ?
    WHERE [Id_card] = ?
    
    Parameters: (status, card_id)
    ↓
    ┌──────────────────────┐
    │ Database Error?      │
    └──────────────────────┘
    ├─ YES → Raise Exception
    │         (Caller should rollback)
    └─ NO → Continue
    ↓
    Log: "[CARD_SERVICE] ✅ Estado de tarjeta actualizado"
    ↓
    Return None
    ↓
    ⚠️ NOTE: No commit executed
             Caller must commit or rollback
    ↓
    END
```

---

## 4. Atomic Multi-Card Operation

```
START: Block multiple cards
       (account_id=1)
    ↓
    conn = get_connection()
    cursor = conn.cursor()
    ↓
    Get all cards for account
    card_ids = [5, 6, 7, 8]
    ↓
    TRY:
    ┌────────────────────────────────────────────┐
    │ FOR EACH card_id IN card_ids:              │
    │   update_card_active_status(cursor, id, F) │
    │   (No commit yet!)                         │
    ├────────────────────────────────────────────┤
    │ card 5 → is_active = False (pending)      │
    │ card 6 → is_active = False (pending)      │
    │ card 7 → is_active = False (pending)      │
    │ card 8 → is_active = False (pending)      │
    │                                            │
    │ conn.commit()  ← ALL COMMIT TOGETHER! ✅  │
    │                                            │
    │ Result:                                    │
    │ ✅ card 5 → is_active = False              │
    │ ✅ card 6 → is_active = False              │
    │ ✅ card 7 → is_active = False              │
    │ ✅ card 8 → is_active = False              │
    └────────────────────────────────────────────┘
    ↓
    EXCEPT:
    ┌────────────────────────────────────────────┐
    │ conn.rollback()  ← UNDO ALL! ❌           │
    │                                            │
    │ Result:                                    │
    │ ❌ card 5 → UNCHANGED                      │
    │ ❌ card 6 → UNCHANGED                      │
    │ ❌ card 7 → UNCHANGED                      │
    │ ❌ card 8 → UNCHANGED                      │
    │ Return error                               │
    └────────────────────────────────────────────┘
    ↓
    FINALLY:
    cursor.close()
    conn.close()
    ↓
    END
    
    IMPORTANT: Either ALL succeed or ALL fail
               No partial updates!
```

---

## 5. Transaction State Machine

```
                    ┌─────────────────┐
                    │   VALIDATION    │
                    │   CHECKS        │
                    └────────┬────────┘
                             │
                    ┌────────v────────┐
                    │ All Pass?       │
                    └────────┬────────┘
                      ├─ NO  → ❌ Return error
                      │        (No DB changes)
                      └─ YES → Continue
                             │
         ┌────────────────────v─────────────────────┐
         │   ATOMIC TRANSACTION BEGINS              │
         │   (Connection open, cursor ready)        │
         └────────────────────┬─────────────────────┘
                              │
                   ┌──────────v──────────┐
                   │ Card Validation?    │
                   │ (if provided)       │
                   └──────────┬──────────┘
                      ├─ FAIL → conn.rollback()
                      │         Return error
                      └─ PASS → Continue
                             │
                   ┌─────────v─────────┐
                   │ Create Transaction│
                   │ (INSERT)          │
                   └─────────┬─────────┘
                             │
                   ┌─────────v─────────┐
                   │ Create Ledger     │
                   │ Entry (INSERT)    │
                   └─────────┬─────────┘
                             │
                   ┌─────────v─────────┐
                   │ conn.commit() ✅  │
                   │ (All changes)     │
                   └─────────┬─────────┘
                             │
         ┌────────────────────v─────────────────────┐
         │   TRANSACTION COMMITTED                 │
         │   (Changes permanent in database)       │
         └────────────────────┬─────────────────────┘
                              │
                   ┌──────────v──────────┐
                   │ Return Success      │
                   │ + tx_id             │
                   │ + ledger_id         │
                   └─────────┬──────────┘
                             │
                            END ✅

═══════════════════════════════════════════════════════

ERROR PATH (Exception or Validation Failure):

         ┌─────────────────────────┐
         │   Exception Caught      │
         │   OR Validation Failed  │
         └──────────┬──────────────┘
                    │
         ┌──────────v──────────┐
         │ conn.rollback() ❌  │
         │ (Undo ALL changes)  │
         └──────────┬──────────┘
                    │
         ┌──────────v────────────────────┐
         │ Return Error                  │
         │ {success: False, error: "..."} │
         └──────────┬────────────────────┘
                    │
         ┌──────────v──────────┐
         │ cursor.close()      │
         │ conn.close()        │
         └──────────┬──────────┘
                    │
                   END ❌
```

---

## 6. Database Query Execution Order

### With Card Validation

```
1. VALIDATE phase (Before transaction)
   ├─ Amount > 0?
   ├─ Account active?
   ├─ Sufficient balance?
   └─ (Decision: proceed or abort)
   
2. OPEN TRANSACTION
   ├─ conn = get_connection()
   └─ cursor = conn.cursor()
   
3. CARD VALIDATION (if card_number provided)
   ├─ Query [card] table
   │  SELECT [Id_card], [account_id],
   │         [card_token], [is_active],
   │         [expiration_date]
   │  WHERE [card_number] = ?
   │
   ├─ Check all 4 validations
   └─ (Decision: proceed with transaction or rollback)

4. CREATE TRANSACTION
   └─ INSERT INTO [transaction] (...)
      cursor.execute(...)
      → No commit yet!

5. GET TRANSACTION ID
   └─ SELECT @@IDENTITY
      → Retrieve last inserted ID

6. CREATE LEDGER ENTRY
   └─ INSERT INTO ledger_entry (...)
      cursor.execute(...)
      → No commit yet!

7. GET LEDGER ID
   └─ SELECT @@IDENTITY
      → Retrieve last inserted ID

8. COMMIT ATOMIC TRANSACTION ✅
   └─ conn.commit()
      → All 2 inserts now permanent

9. CLOSE RESOURCES
   ├─ cursor.close()
   └─ conn.close()

10. RETURN RESULT
    └─ {success: True, transaction_id: X, ledger_id: Y}
```

---

## 7. Error Decision Tree

```
                    Start Transaction
                            │
                ┌───────────┴───────────┐
                │   Amount <= 0?        │
                └───────────┬───────────┘
                     ┌──────NO─────┐
                     │             │
                    YES            │
                     │             │
              ❌ Return       Continue
              "Monto..."     │
                            │
              ┌─────────────┴──────────────┐
              │  Account Status OK?        │
              └─────────────┬──────────────┘
                     ┌──────NO─────┐
                     │             │
                    YES     ❌ Return error
                     │      (SUSPENDED/BLOCKED)
                     │
              ┌──────┴──────────────────┐
              │  Sufficient Balance?    │
              │  (if DEBIT)             │
              └──────┬──────────────────┘
                ┌────NO─────┐
                │           │
               YES    ❌ Return
                │     "Fondos insuficientes"
                │
        ┌───────┴────────────────────┐
        │  card_number provided?     │
        └───────┬────────────────────┘
         ┌──────NO─────┐
         │             │
        YES        Skip card
         │          validation
         │          │
    ┌────┴──────────┴───────────┐
    │ Validate Card             │
    ├─ Exists?  ❌ Return error │
    ├─ Active?  ❌ Return error │
    ├─ Expired? ❌ Return error │
    ├─ Token?   ❌ Return error │
    └────┬──────────────────────┘
         │ (All 4 pass)
    ┌────┴──────────────────────┐
    │ Card belongs to account?  │
    └────┬──────────────────────┘
      ┌──NO───┐
      │       │
     YES  ❌ Return error
      │   "No pertenece..."
      │
    ┌─┴────────────────────────┐
    │ CREATE TRANSACTION       │
    │ + LEDGER ENTRY          │
    │ + COMMIT ✅             │
    └────┬────────────────────┘
         │
    ┌────┴──────────────────────┐
    │ Return Success            │
    │ {success: True, ...}      │
    └───────────────────────────┘
```

---

## Key Insights

1. **Validation happens BEFORE transaction** - Fail fast
2. **Card validation happens INSIDE transaction** - Atomicity
3. **All-or-nothing commitment** - No partial updates
4. **Four sequential card checks** - Any can block
5. **Optional card parameter** - Backward compatible
6. **Clear error messages** - Easy debugging
