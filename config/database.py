import pyodbc
import os
from contextlib import contextmanager
from typing import Generator
from dotenv import load_dotenv

load_dotenv()

DATABASE_PATH = os.getenv("ACCESS_DB_PATH")

if not DATABASE_PATH:
    raise ValueError("La variable de entorno ACCESS_DB_PATH no está definida.")


def get_connection() -> pyodbc.Connection:
    """
    Retorna una conexión activa a la base de datos Access.
    """
    try:
        connection_string = (
            r"DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};"
            rf"DBQ={DATABASE_PATH};"
        )
        return pyodbc.connect(connection_string)
    except pyodbc.Error as e:
        raise Exception(f"Error conectando a la base de datos: {e}")


@contextmanager
def get_cursor(commit: bool = False) -> Generator[pyodbc.Cursor, None, None]:
    """
    Context manager para manejar cursor y conexión automáticamente.

    :param commit: Si True, hace commit automático.
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        yield cursor
        if commit:
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()
