# Card Validation - API Reference

## Quick Start

### 1. Validar Tarjeta Dentro de una Transacción
```python
from config.database import get_connection
from services.card_service import validate_card_for_transaction

conn = get_connection()
cursor = conn.cursor()

try:
    result = validate_card_for_transaction(
        cursor=cursor,
        card_number="4532123456789012",
        input_token="tok_abcd1234"
    )
    
    if result['success']:
        print(f"Tarjeta válida, cuenta: {result['account_id']}")
    else:
        print(f"Error: {result['error']}")
finally:
    cursor.close()
    conn.close()
```

### 2. Bloquear/Desbloquear Tarjeta
```python
from config.database import get_connection
from services.card_service import update_card_active_status

conn = get_connection()
cursor = conn.cursor()

try:
    # Bloquear tarjeta
    update_card_active_status(cursor=cursor, card_id=5, status=False)
    conn.commit()
    print("✅ Tarjeta bloqueada")
except Exception as e:
    conn.rollback()
    print(f"❌ Error: {e}")
finally:
    cursor.close()
    conn.close()
```

### 3. Transacción con Validación de Tarjeta
```python
from services.transaction_service import create_simple_transaction, ENTRY_DEBIT

result = create_simple_transaction(
    account_id=1,
    amount=50.00,
    entry_type=ENTRY_DEBIT,
    description="Pago Netflix",
    created_by_user_id=1,
    transaction_type_id=4,  # Bill Payment
    card_number="4532123456789012",
    card_token="tok_abcd1234"
)

if result['success']:
    print(f"Transacción {result['transaction_id']} completada")
else:
    print(f"Error: {result['error']}")
```

---

## Function Reference

### `validate_card_for_transaction()`

```python
validate_card_for_transaction(cursor: Any, card_number: str, input_token: str) -> dict
```

**Propósito:** Valida que una tarjeta sea válida para transacciones

**Parámetros:**
| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| cursor | Any | Cursor pyodbc activo (NO abre conexión) |
| card_number | str | Número completo de la tarjeta |
| input_token | str | Token de la tarjeta proporcionado |

**Retorna:**
```python
{
    "success": True,          # bool - Validación exitosa
    "account_id": 5,         # int - ID de cuenta asociada (solo si success=True)
    "error": None            # str - Mensaje de error (solo si success=False)
}
```

**Validaciones Realizadas:**
1. ✅ Tarjeta existe en [card]
2. ✅ is_active = True
3. ✅ expiration_date > ahora
4. ✅ card_token == input_token

**Excepciones:**
- Lanza `Exception` si hay error de base de datos

**Ejemplo:**
```python
cursor.execute("...")
result = validate_card_for_transaction(cursor, "4532...", "tok_...")
```

---

### `update_card_active_status()`

```python
update_card_active_status(cursor: Any, card_id: int, status: bool) -> None
```

**Propósito:** Actualiza el estado activo/bloqueado de una tarjeta

**Parámetros:**
| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| cursor | Any | Cursor pyodbc activo (NO cierra conexión) |
| card_id | int | ID de la tarjeta a actualizar |
| status | bool | True=Activa, False=Bloqueada |

**Retorna:** None

**Nota Importante:**
- ⚠️ NO hace commit automático
- ⚠️ El llamador debe hacer commit/rollback
- 🔄 Ideal para operaciones atómicas múltiples

**Excepciones:**
- Lanza `Exception` si hay error de base de datos

**Ejemplo (Transacción Atómica):**
```python
conn = get_connection()
cursor = conn.cursor()
try:
    update_card_active_status(cursor, 5, False)   # Bloquear
    update_card_active_status(cursor, 6, False)   # Bloquear
    conn.commit()  # Ambas se aplican
except:
    conn.rollback()  # Ninguna se aplica
```

---

### `create_simple_transaction()` (Actualizado)

```python
create_simple_transaction(
    account_id: int,
    amount: float,
    entry_type: str,
    description: str,
    created_by_user_id: int,
    transaction_type_id: int,
    status_id: int = 1,
    card_number: str | None = None,
    card_token: str | None = None
) -> dict
```

**Nuevos Parámetros:**
| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| card_number | str \| None | Número de tarjeta (opcional) |
| card_token | str \| None | Token de tarjeta (requerido si card_number se proporciona) |

**Flujo de Validación:**
1. Validar monto > 0
2. Verificar estado de cuenta
3. Verificar saldo (si es débito)
4. **Si card_number no es None:**
   - Validar tarjeta con `validate_card_for_transaction()`
   - Verificar que la tarjeta pertenece a la cuenta
   - Si falla: Abort transacción
5. Crear registro de transacción
6. Crear entrada en ledger
7. Commit

**Retorna:**
```python
# Éxito
{
    "success": True,
    "transaction_id": 123,       # ID de la transacción
    "ledger_entry_id": 456       # ID de la entrada contable
}

# Fallo
{
    "success": False,
    "error": "Descripción del error"
}
```

**Errores Posibles:**
- "El monto debe ser mayor a cero."
- "Cuenta SUSPENDIDA..."
- "Fondos insuficientes..."
- "Tarjeta no encontrada"
- "La tarjeta está bloqueada"
- "Tarjeta vencida"
- "Token de tarjeta inválido"
- "La tarjeta no pertenece a esta cuenta..."

**Backward Compatibility:**
```python
# ✅ Aún funciona sin tarjeta
result = create_simple_transaction(
    account_id=1,
    amount=50.00,
    entry_type=ENTRY_DEBIT,
    description="Retiro",
    created_by_user_id=1,
    transaction_type_id=2
    # card_number=None (omitido)
)
```

---

## Error Messages Reference

| Error | Causa | Solución |
|-------|-------|----------|
| "Tarjeta no encontrada" | card_number no existe en BD | Verificar número de tarjeta |
| "La tarjeta está bloqueada" | is_active = False | Desbloquear con update_card_active_status() |
| "Tarjeta vencida" | expiration_date < ahora | Usar tarjeta nueva o renovar |
| "Token de tarjeta inválido" | card_token no coincide | Usar token correcto |
| "La tarjeta no pertenece..." | card.account_id ≠ tx.account_id | Usar tarjeta de la cuenta correcta |
| "card_token es requerido..." | card_number sin card_token | Proporcionar card_token |
| "El monto debe ser mayor..." | amount ≤ 0 | Usar monto positivo |
| "Fondos insuficientes..." | balance < amount | Depositar fondos |

---

## Common Patterns

### Pattern 1: Pago con Tarjeta Validada
```python
from services.transaction_service import create_simple_transaction, ENTRY_DEBIT

def pay_with_card(account_id, amount, card_number, card_token, merchant):
    result = create_simple_transaction(
        account_id=account_id,
        amount=amount,
        entry_type=ENTRY_DEBIT,
        description=f"Pago a {merchant}",
        created_by_user_id=1,  # Sistema
        transaction_type_id=4,  # Bill Payment
        card_number=card_number,
        card_token=card_token
    )
    return result
```

### Pattern 2: Bloquear Múltiples Tarjetas
```python
def block_all_cards(account_id):
    from config.database import get_connection
    from services.card_service import update_card_active_status
    from models.card_model import get_cards_by_account
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cards = get_cards_by_account(account_id)
        for card_id in cards:
            update_card_active_status(cursor, card_id, False)
        conn.commit()
        return {"success": True, "blocked": len(cards)}
    except Exception as e:
        conn.rollback()
        return {"success": False, "error": str(e)}
    finally:
        cursor.close()
        conn.close()
```

### Pattern 3: Validar sin Procesar Transacción
```python
def validate_card_only(card_number, card_token):
    from config.database import get_connection
    from services.card_service import validate_card_for_transaction
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        result = validate_card_for_transaction(
            cursor,
            card_number,
            card_token
        )
        return result
    finally:
        cursor.close()
        conn.close()
```

---

## Testing Your Implementation

### Test Script
See `test_card_validation.py` for comprehensive examples:

```bash
python test_card_validation.py
```

Tests included:
- ✓ Validación de tarjeta activa
- ✓ Validación de tarjeta bloqueada
- ✓ Validación de tarjeta vencida
- ✓ Validación con token incorrecto
- ✓ Actualización de estado de tarjeta
- ✓ Transacción con validación
- ✓ Transacción sin validación (backward compat)

---

## Arquitectura de Transacciones Atómicas

### Por qué cursor externo?
```
✅ CORRECTO - Atómico:
  conn.begin()
    validate_card()        ← Desde cursor de transacción
    create_transaction()   ← Desde cursor de transacción
    create_ledger()        ← Desde cursor de transacción
  conn.commit()            ← Todo sucede junto

❌ INCORRECTO - No atómico:
  validate_card()          ← Abre/cierra conexión propia
  create_transaction()     ← Abre/cierra conexión propia
  create_ledger()          ← Abre/cierra conexión propia
                           ← Puede fallar a mitad
```

---

## Notas de Implementación

### Campos de Tabla [card]
- `[Id_card]` - PK, identificador único
- `[account_id]` - FK a [account]
- `[card_number]` - Número completo de 16 dígitos
- `[card_token]` - Token único para la tarjeta
- `[holder_name]` - Nombre del titular
- `[expiration_date]` - DATETIME de vencimiento
- `[is_active]` - BOOLEAN (0=bloqueada, 1=activa)
- `[created_at]` - DATETIME de creación

### Importes Correctos
```python
from services.card_service import validate_card_for_transaction, update_card_active_status
from services.transaction_service import create_simple_transaction, ENTRY_DEBIT, ENTRY_CREDIT
```

### Estructura de Respuesta Consistente
Todas las funciones retornan diccionarios con:
- `success` (bool) - Indica éxito/fallo
- `error` (str) - Descripción si falla
- Campos adicionales según la función

---

## Troubleshooting

### Error: "La tarjeta no pertenece a esta cuenta"
```python
# Causa: card.account_id != transaction.account_id
# Solución: Verificar que estés usando la tarjeta correcta

# ❌ Incorrecto
create_simple_transaction(
    account_id=1,  # Cuenta A
    card_number="...",  # De cuenta B
    card_token="..."
)

# ✅ Correcto
create_simple_transaction(
    account_id=1,  # Debe coincidir con account_id de la tarjeta
    card_number="...",
    card_token="..."
)
```

### Error: "Token de tarjeta inválido"
```python
# Causa: card_token en BD ≠ input_token
# Solución: Usar el token correcto

# Verificar el token correcto:
conn = get_connection()
cursor = conn.cursor()
cursor.execute("""
    SELECT [card_token] FROM [card] WHERE [card_number] = ?
""", (card_num,))
row = cursor.fetchone()
correct_token = row[0]  # Usar este token
cursor.close()
conn.close()
```

### Transaction Rollback
```python
# Si algo falla, la transacción se revierte automáticamente
try:
    result = create_simple_transaction(...)
    # Si result['success'] == False, automáticamente se hizo rollback
except Exception as e:
    # Si hay excepción, se ejecutó rollback en el except
    print(f"Transacción revertida: {e}")
```

---

## Performance Considerations

- **Validación de tarjeta:** ~5-10ms
- **Validación de token:** ~1-2ms
- **Bloqueo de tarjeta:** ~1-3ms
- **Creación de transacción:** ~10-20ms

Total para transacción completa con tarjeta: **~20-35ms**

---

## Security Best Practices

✅ **Hacer:**
- Usar card_token en lugar de número completo después de validación
- Hashear números de tarjeta antes de almacenar
- Validar tarjeta antes de procesar dinero
- Usar transacciones atómicas en todas las operaciones
- Implementar rate limiting en validaciones

❌ **No hacer:**
- Mostrar número completo de tarjeta en logs
- Enviar numbers de tarjeta en responses API
- Validar tarjeta fuera de una transacción
- Almacenar PIN o CVV
- Usar tarjeta si no está bloqueada explícitamente

---

## Más Información

Para detalles completos, ver:
- [CARD_VALIDATION_GUIDE.md](CARD_VALIDATION_GUIDE.md) - Documentación técnica
- [test_card_validation.py](test_card_validation.py) - Ejemplos de uso
