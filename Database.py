"""
database.py
-----------
Capa de acceso a datos (Supabase).
Aquí vive la comunicación con la tabla `gastos`.
"""

import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
from supabase import Client, create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError(
        "Faltan SUPABASE_URL o SUPABASE_KEY en el archivo .env"
    )

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Zona horaria local para filtrar correctamente los reportes del mes actual
LOCAL_TZ = ZoneInfo("America/Bogota")


def _rango_mes_actual_utc() -> tuple[str, str]:
    """Calcula el inicio y fin del mes actual en hora local y los convierte a UTC ISO."""
    ahora_local = datetime.now(LOCAL_TZ)
    inicio_local = ahora_local.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    if inicio_local.month == 12:
        fin_local = inicio_local.replace(year=inicio_local.year + 1, month=1)
    else:
        fin_local = inicio_local.replace(month=inicio_local.month + 1)

    return (
        inicio_local.astimezone(timezone.utc).isoformat(),
        fin_local.astimezone(timezone.utc).isoformat(),
    )


# ---------------------------------------------------------------------------
# 1. INICIALIZACIÓN (compatibilidad con main.py)
# ---------------------------------------------------------------------------
def inicializar_db() -> None:
    """Verifica conexión con la tabla `gastos` en Supabase al arrancar el bot."""
    supabase.table("gastos").select("id").limit(1).execute()


# ---------------------------------------------------------------------------
# 2. INSERTAR UN GASTO
# ---------------------------------------------------------------------------
def guardar_gasto(
    user_id: int,
    monto: float,
    moneda: str,
    categoria: str,
    descripcion: str,
) -> int | None:
    """Guarda un gasto en Supabase asociado al telegram_user_id y devuelve su id."""
    _ = moneda
    payload = {
        "telegram_user_id": user_id,
        "monto": float(monto),
        "categoria": categoria,
        "descripcion": descripcion,
    }
    respuesta = supabase.table("gastos").insert(payload).execute()
    if respuesta.data:
        return respuesta.data[0].get("id")
    return None


# ---------------------------------------------------------------------------
# 3. REPORTE DEL MES ACTUAL (agrupado por moneda y categoría)
# ---------------------------------------------------------------------------
def obtener_reporte_mensual(user_id: int) -> list[dict]:
    """
    Suma los gastos del mes actual del usuario, agrupados por moneda y categoría.
    """
    inicio_utc, fin_utc = _rango_mes_actual_utc()
    respuesta = (
        supabase.table("gastos")
        .select("monto, categoria, fecha_registro")
        .eq("telegram_user_id", user_id)
        .gte("fecha_registro", inicio_utc)
        .lt("fecha_registro", fin_utc)
        .execute()
    )

    agrupado: dict[tuple[str, str], dict] = {}
    for fila in respuesta.data:
        moneda = "COP"
        categoria = fila.get("categoria") or "Sin categoría"
        monto = float(fila.get("monto") or 0)
        clave = (moneda, categoria)

        if clave not in agrupado:
            agrupado[clave] = {
                "moneda": moneda,
                "categoria": categoria,
                "total": 0.0,
                "cantidad": 0,
            }
        agrupado[clave]["total"] += monto
        agrupado[clave]["cantidad"] += 1

    resultados = list(agrupado.values())
    resultados.sort(key=lambda item: (item["moneda"], -item["total"]))
    return resultados


# ---------------------------------------------------------------------------
# 4. BORRAR EL ÚLTIMO GASTO
# ---------------------------------------------------------------------------
def borrar_ultimo_gasto(user_id: int) -> dict | None:
    """
    Elimina el último gasto registrado por el usuario.
    Devuelve los datos del gasto borrado, o None si no tenía gastos.
    """
    consulta = (
        supabase.table("gastos")
        .select("*")
        .eq("telegram_user_id", user_id)
        .order("id", desc=True)
        .limit(1)
        .execute()
    )
    if not consulta.data:
        return None

    gasto = consulta.data[0]
    supabase.table("gastos").delete().eq("id", gasto["id"]).eq("telegram_user_id", user_id).execute()
    gasto.setdefault("moneda", "COP")
    return gasto


# ---------------------------------------------------------------------------
# 5. TOTAL DEL MES
# ---------------------------------------------------------------------------
def obtener_total_mes(user_id: int, moneda: str) -> float:
    """Suma todos los gastos del mes actual del usuario en una moneda."""
    _ = moneda
    inicio_utc, fin_utc = _rango_mes_actual_utc()
    respuesta = (
        supabase.table("gastos")
        .select("monto")
        .eq("telegram_user_id", user_id)
        .gte("fecha_registro", inicio_utc)
        .lt("fecha_registro", fin_utc)
        .execute()
    )
    return sum(float(fila.get("monto") or 0) for fila in respuesta.data)


# ---------------------------------------------------------------------------
# 6. BORRAR UN GASTO ESPECÍFICO ("Deshacer")
# ---------------------------------------------------------------------------
def borrar_gasto_por_id(user_id: int, gasto_id: int) -> dict | None:
    """
    Borra un gasto concreto, verificando que pertenezca al usuario.
    Devuelve el gasto borrado o None si no existe.
    """
    consulta = (
        supabase.table("gastos")
        .select("*")
        .eq("id", gasto_id)
        .eq("telegram_user_id", user_id)
        .limit(1)
        .execute()
    )
    if not consulta.data:
        return None

    gasto = consulta.data[0]
    supabase.table("gastos").delete().eq("id", gasto_id).eq("telegram_user_id", user_id).execute()
    gasto.setdefault("moneda", "COP")
    return gasto
