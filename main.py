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
import random
from datetime import datetime

from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ChatAction, ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
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
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# Mensaje exigido por la rúbrica cuando la IA falla o no entiende.
MENSAJE_ERROR_IA = (
    "🤔 No logré entender el gasto. "
    "Intenta decir algo como: 'Gasté 10.000 en transporte'"
)

LINEA = "━━━━━━━━━━━━━━━━━━"

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

MEDALLAS = ["🥇", "🥈", "🥉"]

TITULOS_REGISTRO = [
    "¡Anotado!",
    "¡Listo, gasto guardado!",
    "¡Hecho! Ya quedó registrado",
    "¡Pa' la libreta!",
    "¡Gasto en el bolsillo… digo, en la base de datos!",
]

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


# ---------------------------------------------------------------------------
# 2. UTILIDADES DE FORMATO
# ---------------------------------------------------------------------------
def formatear_monto(monto: float, moneda: str) -> str:
    """Formatea dinero al estilo latinoamericano: $25.000 COP / $15,50 USD."""
    if float(monto).is_integer():
        texto = f"{int(monto):,}".replace(",", ".")
    else:
        texto = f"{monto:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"${texto} {moneda}"


def barra_progreso(porcentaje: float, largo: int = 10) -> str:
    """Devuelve una barra visual tipo ▓▓▓▓░░░░░░ según el porcentaje."""
    llenos = max(1, round(porcentaje / 100 * largo)) if porcentaje > 0 else 0
    return "▓" * llenos + "░" * (largo - llenos)


# ---------------------------------------------------------------------------
# 3. COMANDO /start: mensaje de bienvenida
# ---------------------------------------------------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    nombre = html.escape(update.effective_user.first_name or "amigo")
    texto = (
        f"👋 <b>¡Hola, {nombre}!</b>\n"
        "Soy tu <b>asistente de gastos</b> con Inteligencia Artificial 🤖✨\n"
        f"{LINEA}\n\n"
        "💬 <b>¿Cómo funciono?</b>\n"
        "Cuéntame tus gastos como se los contarías a un amigo:\n\n"
        "   ▫️ <i>Gasté 25.000 en el almuerzo</i>\n"
        "   ▫️ <i>Pagué 15 dólares de internet</i>\n"
        "   ▫️ <i>taxi 12 mil</i>\n\n"
        "Yo entiendo el monto, la categoría y la moneda, y lo guardo por ti 💾\n\n"
        f"{LINEA}\n"
        "🧭 <b>Comandos</b>\n"
        "📊 /reporte — tus gastos del mes\n"
        "🗑️ /borrar — elimina tu último gasto\n"
        "🏠 /start — volver a este mensaje\n\n"
        "👇 <b>¡Pruébame! Escribe tu primer gasto.</b>"
    )
    await update.message.reply_text(texto, parse_mode=ParseMode.HTML)


# ---------------------------------------------------------------------------
# 4. COMANDO /reporte: total del mes con medallas y barras de progreso
# ---------------------------------------------------------------------------
async def reporte(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id

    try:
        filas = database.obtener_reporte_mensual(user_id)
    except Exception:
        logger.exception("Error consultando el reporte")
        await update.message.reply_text("⚠️ Ups, ocurrió un error al generar el reporte.")
        return

    ahora = datetime.now()
    titulo = (
        f"📊 <b>REPORTE · {MESES[ahora.month - 1].upper()} {ahora.year}</b>\n{LINEA}"
    )

    if not filas:
        await update.message.reply_text(
            f"{titulo}\n\n🙌 Aún no tienes gastos este mes.\n"
            "Escríbeme el primero, por ejemplo: <i>Gasté 8.000 en un café</i> ☕",
            parse_mode=ParseMode.HTML,
        )
        return

    # Agrupamos por moneda: {"COP": [filas...], "USD": [filas...]}
    por_moneda: dict[str, list] = {}
    for fila in filas:
        por_moneda.setdefault(fila["moneda"], []).append(fila)

    bloques = [titulo]
    for moneda, items in por_moneda.items():
        total_moneda = sum(item["total"] for item in items)
        lineas = [f"\n💵 <b>{moneda}</b>\n"]

        # Las filas ya vienen ordenadas de mayor a menor gasto.
        for posicion, item in enumerate(items):
            medalla = MEDALLAS[posicion] if posicion < len(MEDALLAS) else "▫️"
            emoji = EMOJIS_CATEGORIA.get(item["categoria"], "📦")
            porcentaje = item["total"] / total_moneda * 100
            plural = "gasto" if item["cantidad"] == 1 else "gastos"
            lineas.append(
                f"{medalla} {emoji} <b>{item['categoria']}</b> · "
                f"{formatear_monto(item['total'], moneda)}\n"
                f"      {barra_progreso(porcentaje)} {porcentaje:.0f}% · "
                f"{item['cantidad']} {plural}\n"
            )

        lineas.append(f"{LINEA}\n🧾 <b>TOTAL: {formatear_monto(total_moneda, moneda)}</b>")
        bloques.append("\n".join(lineas))

    bloques.append("\n💡 <i>Sigue escribiendo tus gastos para actualizar el reporte.</i>")
    await update.message.reply_text("\n".join(bloques), parse_mode=ParseMode.HTML)


# ---------------------------------------------------------------------------
# 5. COMANDO /borrar: elimina el último gasto del usuario
# ---------------------------------------------------------------------------
async def borrar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id

    try:
        gasto = database.borrar_ultimo_gasto(user_id)
    except Exception:
        logger.exception("Error borrando el gasto")
        await update.message.reply_text("⚠️ Ups, ocurrió un error al borrar el gasto.")
        return

    if gasto is None:
        await update.message.reply_text(
            "🤷 No tienes gastos registrados para borrar.\n"
            "Cuéntame uno y lo anoto ✍️"
        )
        return

    emoji = EMOJIS_CATEGORIA.get(gasto["categoria"], "📦")
    await update.message.reply_text(
        "🗑️ <b>¡Gasto eliminado!</b>\n"
        f"{LINEA}\n"
        f"{emoji}  {html.escape(gasto['descripcion'] or gasto['categoria'])}\n"
        f"💰  {formatear_monto(gasto['monto'], gasto['moneda'])}\n"
        f"{LINEA}\n"
        "✨ Como si nunca hubiera existido.",
        parse_mode=ParseMode.HTML,
    )


# ---------------------------------------------------------------------------
# 6. MENSAJE LIBRE: flujo principal (IA → validación → SQLite → confirmación)
# ---------------------------------------------------------------------------
async def procesar_gasto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    texto = update.message.text

    await context.bot.send_chat_action(update.effective_chat.id, ChatAction.TYPING)

    # Paso A: la IA interpreta si es un gasto o una conversación normal
    try:
        resultado = await ai_service.extraer_gasto(texto)
    except ai_service.ErrorInterpretacionGasto as e:
        logger.warning("Fallo de IA interpretando %r: %s", texto, e)
        await update.message.reply_text(MENSAJE_ERROR_IA)
        return
    except Exception:
        logger.exception("Error inesperado con la IA")
        await update.message.reply_text(MENSAJE_ERROR_IA)
        return

    # Si no es un gasto (saludo, pregunta o falta el monto), responde como persona
    if not resultado["es_gasto"]:
        await update.message.reply_text(resultado["respuesta"])
        return

    # Paso B: guardamos en SQLite y consultamos el acumulado del mes
    try:
        gasto_id = database.guardar_gasto(
            user_id=user_id,
            monto=resultado["monto"],
            moneda=resultado["moneda"],
            categoria=resultado["categoria"],
            descripcion=resultado["descripcion"],
        )
        total_mes = database.obtener_total_mes(user_id, resultado["moneda"])
    except Exception:
        logger.exception("Error guardando en la base de datos")
        await update.message.reply_text("⚠️ No pude guardar el gasto. Intenta de nuevo.")
        return

    # Paso C: confirmamos usando el comentario natural generado por Gemini
    emoji = EMOJIS_CATEGORIA.get(resultado["categoria"], "📦")
    teclado = InlineKeyboardMarkup(
        [[InlineKeyboardButton("↩️ Deshacer", callback_data=f"deshacer:{gasto_id}")]]
    )
    await update.message.reply_text(
        f"✅ <b>{html.escape(resultado['comentario'])}</b>\n"
        f"{LINEA}\n"
        f"{emoji}  <b>{html.escape(resultado['descripcion'])}</b>\n\n"
        f"💰 Monto:  <b>{formatear_monto(resultado['monto'], resultado['moneda'])}</b>\n"
        f"🏷️ Categoría:  <b>{resultado['categoria']}</b>\n"
        f"{LINEA}\n"
        f"📅 Llevas <b>{formatear_monto(total_mes, resultado['moneda'])}</b> este mes",
        parse_mode=ParseMode.HTML,
        reply_markup=teclado,
    )


# ---------------------------------------------------------------------------
# 7. BOTÓN "DESHACER": borra el gasto exacto que se acaba de registrar
# ---------------------------------------------------------------------------
async def deshacer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()  # quita el "reloj" del botón en Telegram

    gasto_id = int(query.data.split(":")[1])

    try:
        gasto = database.borrar_gasto_por_id(query.from_user.id, gasto_id)
    except Exception:
        logger.exception("Error al deshacer el gasto")
        await query.edit_message_text("⚠️ No pude deshacer el gasto.")
        return

    if gasto is None:
        await query.edit_message_text("ℹ️ Este gasto ya no existe (quizá ya lo borraste).")
        return

    emoji = EMOJIS_CATEGORIA.get(gasto["categoria"], "📦")
    await query.edit_message_text(
        "↩️ <b>¡Gasto deshecho!</b>\n"
        f"{LINEA}\n"
        f"<s>{emoji} {html.escape(gasto['descripcion'] or gasto['categoria'])} · "
        f"{formatear_monto(gasto['monto'], gasto['moneda'])}</s>\n"
        f"{LINEA}\n"
        "✨ Listo, ya no aparece en tu reporte.",
        parse_mode=ParseMode.HTML,
    )


# ---------------------------------------------------------------------------
# 8. MANEJADOR GLOBAL DE ERRORES (red de seguridad final)
# ---------------------------------------------------------------------------
async def manejar_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Excepción no controlada:", exc_info=context.error)


# ---------------------------------------------------------------------------
# 9. ARRANQUE DEL BOT
# ---------------------------------------------------------------------------
def main() -> None:
    if not TELEGRAM_TOKEN:
        raise RuntimeError("Falta TELEGRAM_TOKEN en el archivo .env")

    database.inicializar_db()

    app = (
        Application.builder()
        .token(TELEGRAM_TOKEN)
        .concurrent_updates(True)
        .build()
    )
    # Comandos
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reporte", reporte))
    app.add_handler(CommandHandler("borrar", borrar))

    # Botón inline "Deshacer"
    app.add_handler(CallbackQueryHandler(deshacer, pattern=r"^deshacer:\d+$"))

    # Texto libre que NO sea un comando
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, procesar_gasto))

    app.add_error_handler(manejar_error)

    logger.info("🤖 Bot iniciado. Presiona Ctrl+C para detenerlo.")
    app.run_polling()


if __name__ == "__main__":
    main()
