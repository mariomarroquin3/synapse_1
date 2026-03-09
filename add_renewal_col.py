import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))
from config.database import get_cursor

try:
    with get_cursor(commit=True) as cursor:
        cursor.execute("ALTER TABLE [card] ADD COLUMN renewal_requested BIT")
    print("Column added successfully.")
except Exception as e:
    print(f"Error adding column (might already exist): {e}")
    
try:
    with get_cursor(commit=True) as cursor:
        # Default existing to 0/False
        cursor.execute("UPDATE [card] SET renewal_requested = 0 WHERE renewal_requested IS NULL")
    print("Column updated to defaults.")
except Exception as e:
    print(f"Error updating defaults: {e}")
