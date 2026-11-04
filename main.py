"""
main.py
-------
Punto de entrada del bot de Telegram.
Define los comandos (/start, /reporte, /borrar), el manejo de mensajes libres
y coordina los otros dos módulos: ai_service (IA) y database (SQLite).
"""

import html
import logging
import os
from datetime import datetime

from dotenv import load_dotenv
from telegram import Update
from telegram.constants import ChatAction, ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

import ai_service
import database

# ---------------------------------------------------------------------------
# 1. CONFIGURACIÓN: variables de entorno y logging
# ---------------------------------------------------------------------------
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logging.getLogger("httpx").setLevel(logging.WARNING)  # evita ruido en consola
logger = logging.getLogger(__name__)

MENSAJE_ERROR_IA = (
    "No logré entender el gasto. "
    "Intenta decir algo como: 'Gasté 10.000 en transporte'"
)

EMOJIS_CATEGORIA = {
    "Alimentación": "🍔",
    "Transporte": "🚌",
    "Servicios": "💡",
    "Entretenimiento": "🎬",
    "Salud": "💊",
    "Educación": "📚",
    "Hogar": "🏠",
    "Ropa": "👕",
    "Otros": "📦",
}

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


# ---------------------------------------------------------------------------
# 2. UTILIDAD: formatear dinero al estilo latinoamericano (25.000 / 15,50)
# ---------------------------------------------------------------------------
def formatear_monto(monto: float, moneda: str) -> str:
    if float(monto).is_integer():
        texto = f"{int(monto):,}".replace(",", ".")
    else:
        texto = f"{monto:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"${texto} {moneda}"


# ---------------------------------------------------------------------------
# 3. COMANDO /start: mensaje de bienvenida
# ---------------------------------------------------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    nombre = html.escape(update.effective_user.first_name or "amigo")
    texto = (
        f"👋 <b>¡Hola, {nombre}!</b>\n\n"
        "Soy tu asistente de <b>gastos personales</b> con Inteligencia Artificial 🤖\n\n"
        "Solo escríbeme tus gastos como se los contarías a un amigo:\n"
        "• <i>Gasté 25.000 en el almuerzo</i>\n"
        "• <i>Pagué 15 dólares de internet</i>\n\n"
        "Yo extraigo el monto y la categoría y lo guardo por ti 💾\n\n"
        "<b>Comandos disponibles:</b>\n"
        "📊 /reporte → gastos del mes por categoría\n"
        "🗑️ /borrar → elimina tu último gasto\n"
        "ℹ️ /start → muestra este mensaje"
    )
    await update.message.reply_text(texto, parse_mode=ParseMode.HTML)


# ---------------------------------------------------------------------------
# 4. COMANDO /reporte: total del mes actual agrupado por categoría
# ---------------------------------------------------------------------------
async def reporte(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id

    try:
        filas = database.obtener_reporte_mensual(user_id)
    except Exception:
        logger.exception("Error consultando el reporte")
        await update.message.reply_text("⚠️ Ocurrió un error al generar el reporte.")
        return

    ahora = datetime.now()
    titulo = f"📊 <b>Reporte de {MESES[ahora.month - 1]} {ahora.year}</b>"

    if not filas:
        await update.message.reply_text(
            f"{titulo}\n\nAún no tienes gastos este mes 🙌", parse_mode=ParseMode.HTML
        )
        return

    # Agrupamos las filas por moneda: {"COP": [filas...], "USD": [filas...]}
    por_moneda: dict[str, list] = {}
    for fila in filas:
        por_moneda.setdefault(fila["moneda"], []).append(fila)

    lineas = [titulo]
    for moneda, items in por_moneda.items():
        lineas.append(f"\n💵 <b>{moneda}</b>")
        total_moneda = 0.0
        for item in items:
            emoji = EMOJIS_CATEGORIA.get(item["categoria"], "📦")
            lineas.append(
                f"{emoji} {item['categoria']}: "
                f"{formatear_monto(item['total'], moneda)} ({item['cantidad']})"
            )
            total_moneda += item["total"]
        lineas.append(f"➡️ <b>Total: {formatear_monto(total_moneda, moneda)}</b>")

    await update.message.reply_text("\n".join(lineas), parse_mode=ParseMode.HTML)


# ---------------------------------------------------------------------------
# 5. COMANDO /borrar: elimina el último gasto del usuario
# ---------------------------------------------------------------------------
async def borrar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id

    try:
        gasto = database.borrar_ultimo_gasto(user_id)
    except Exception:
        logger.exception("Error borrando el gasto")
        await update.message.reply_text("⚠️ Ocurrió un error al borrar el gasto.")
        return

    if gasto is None:
        await update.message.reply_text("No tienes gastos registrados para borrar 🤷")
        return

    emoji = EMOJIS_CATEGORIA.get(gasto["categoria"], "📦")
    await update.message.reply_text(
        "🗑️ <b>Gasto eliminado</b>\n"
        f"{emoji} {html.escape(gasto['descripcion'] or gasto['categoria'])}\n"
        f"💰 {formatear_monto(gasto['monto'], gasto['moneda'])}",
        parse_mode=ParseMode.HTML,
    )


# ---------------------------------------------------------------------------
# 6. MENSAJE LIBRE: flujo principal (IA → validación → SQLite → confirmación)
# ---------------------------------------------------------------------------
async def procesar_gasto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    texto = update.message.text

    # Muestra "escribiendo..." mientras la IA piensa.
    await context.bot.send_chat_action(update.effective_chat.id, ChatAction.TYPING)

    # Paso A: la IA interpreta el mensaje. Si falla, respondemos amablemente.
    try:
        gasto = await ai_service.extraer_gasto(texto)
    except ai_service.ErrorInterpretacionGasto as e:
        logger.warning("No se pudo interpretar %r: %s", texto, e)
        await update.message.reply_text(MENSAJE_ERROR_IA)
        return
    except Exception:
        logger.exception("Error inesperado con la IA")
        await update.message.reply_text(MENSAJE_ERROR_IA)
        return

    # Paso B: guardamos en SQLite.
    try:
        database.guardar_gasto(
            user_id=user_id,
            monto=gasto["monto"],
            moneda=gasto["moneda"],
            categoria=gasto["categoria"],
            descripcion=gasto["descripcion"],
        )
    except Exception:
        logger.exception("Error guardando en la base de datos")
        await update.message.reply_text("⚠️ No pude guardar el gasto. Intenta de nuevo.")
        return

    # Paso C: confirmamos al usuario con un mensaje formateado.
    emoji = EMOJIS_CATEGORIA.get(gasto["categoria"], "📦")
    await update.message.reply_text(
        "✅ <b>¡Gasto registrado!</b>\n\n"
        f"💰 Monto: <b>{formatear_monto(gasto['monto'], gasto['moneda'])}</b>\n"
        f"{emoji} Categoría: <b>{gasto['categoria']}</b>\n"
        f"📝 Detalle: {html.escape(gasto['descripcion'])}",
        parse_mode=ParseMode.HTML,
    )


# ---------------------------------------------------------------------------
# 7. MANEJADOR GLOBAL DE ERRORES (red de seguridad final)
# ---------------------------------------------------------------------------
async def manejar_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Excepción no controlada:", exc_info=context.error)


# ---------------------------------------------------------------------------
# 8. ARRANQUE DEL BOT
# ---------------------------------------------------------------------------
def main() -> None:
    if not TELEGRAM_TOKEN:
        raise RuntimeError("Falta TELEGRAM_TOKEN en el archivo .env")

    database.inicializar_db()

    app = Application.builder().token(TELEGRAM_TOKEN).build()

    # Comandos
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reporte", reporte))
    app.add_handler(CommandHandler("borrar", borrar))

    # Texto libre que NO sea un comando
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, procesar_gasto))

    app.add_error_handler(manejar_error)

    logger.info("🤖 Bot iniciado. Presiona Ctrl+C para detenerlo.")
    app.run_polling()


if __name__ == "__main__":
    main()
