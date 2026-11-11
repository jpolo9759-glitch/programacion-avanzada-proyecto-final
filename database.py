"""
database.py
-----------
Capa de acceso a datos (SQLite).
Aquí vive TODO el SQL del proyecto. main.py nunca escribe consultas directamente.
"""

import sqlite3
from contextlib import contextmanager

DB_PATH = "gastos.db"


# ---------------------------------------------------------------------------
# 1. CONEXIÓN
# ---------------------------------------------------------------------------
@contextmanager
def _conexion():
    """
    Abre una conexión, confirma (commit) si todo salió bien,
    revierte (rollback) si hubo un error y SIEMPRE la cierra.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # permite acceder a columnas por nombre
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# 2. CREACIÓN DE LA TABLA (se ejecuta al iniciar el bot)
# ---------------------------------------------------------------------------
def inicializar_db() -> None:
    """Crea la tabla de gastos si todavía no existe."""
    with _conexion() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS gastos (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                monto       REAL    NOT NULL,
                moneda      TEXT    NOT NULL DEFAULT 'COP',
                categoria   TEXT    NOT NULL,
                descripcion TEXT,
                fecha       TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
            )
            """
        )
        # Índice para que las consultas por usuario sean rápidas.
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_gastos_usuario ON gastos (user_id)"
        )


# ---------------------------------------------------------------------------
# 3. INSERTAR UN GASTO
# ---------------------------------------------------------------------------
def guardar_gasto(user_id: int, monto: float, moneda: str,
                  categoria: str, descripcion: str) -> int:
    """Guarda un gasto y devuelve su id. Usa parámetros (?) contra SQL Injection."""
    with _conexion() as conn:
        cursor = conn.execute(
            """
            INSERT INTO gastos (user_id, monto, moneda, categoria, descripcion)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, monto, moneda, categoria, descripcion),
        )
        return cursor.lastrowid


# ---------------------------------------------------------------------------
# 4. REPORTE DEL MES ACTUAL (agrupado por moneda y categoría)
# ---------------------------------------------------------------------------
def obtener_reporte_mensual(user_id: int) -> list[sqlite3.Row]:
    """
    Suma los gastos del mes actual del usuario, agrupados por moneda y categoría.
    Se agrupa por moneda para no mezclar pesos con dólares.
    """
    with _conexion() as conn:
        return conn.execute(
            """
            SELECT moneda,
                   categoria,
                   SUM(monto) AS total,
                   COUNT(*)   AS cantidad
            FROM gastos
            WHERE user_id = ?
              AND strftime('%Y-%m', fecha) = strftime('%Y-%m', 'now', 'localtime')
            GROUP BY moneda, categoria
            ORDER BY moneda, total DESC
            """,
            (user_id,),
        ).fetchall()


# ---------------------------------------------------------------------------
# 5. BORRAR EL ÚLTIMO GASTO
# ---------------------------------------------------------------------------
def borrar_ultimo_gasto(user_id: int) -> dict | None:
    """
    Elimina el último gasto registrado por el usuario.
    Devuelve los datos del gasto borrado, o None si no tenía gastos.
    """
    with _conexion() as conn:
        fila = conn.execute(
            "SELECT * FROM gastos WHERE user_id = ? ORDER BY id DESC LIMIT 1",
            (user_id,),
        ).fetchone()

        if fila is None:
            return None

        conn.execute("DELETE FROM gastos WHERE id = ?", (fila["id"],))
        return dict(fila)
