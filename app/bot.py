"""Parte H · Bot de Telegram: SÓLO recibe y entrega mensajes.

    python -m app.bot [--simulado]

No contiene lógica del agente: llama al mismo agente.responder que la terminal.
La llamada bloqueante corre en otro hilo (asyncio.to_thread) para no congelar el bot.
"""
import argparse
import asyncio
import hashlib
import logging
import os

from app import agente
from app.comun import (RAIZ, Bitacora, cargar_herramientas, crear_llamador, leer_sistema,
                       preparar_consola)

LIMITE_TELEGRAM = 4096

TEXTO_START = (
    "Hola. Soy un agente analista del DENUE (INEGI, edición 05/2026) para Tampico y "
    "Ciudad Madero.\n\n"
    "Puedo responder: cuántos negocios hay de un giro, en qué colonias o municipio se "
    "concentran, rankings por sector o actividad, y listar establecimientos (por ejemplo, "
    "los más grandes).\n\n"
    "El DENUE NO tiene: número exacto de empleados (sólo rangos), ventas, ganancias, "
    "salarios, opiniones ni datos de otros municipios.\n\n"
    "Una respuesta puede tardar hasta un par de minutos.\n\n"
    "Privacidad: no escribas datos personales. Tus mensajes pasan por Telegram y por Google "
    "(Gemini) para ser procesados.")

TEXTO_FUENTE = (
    "Fuente: Directorio Estadístico Nacional de Unidades Económicas (DENUE), edición 05/2026, "
    "INEGI. Recorte: municipios de Tampico y Ciudad Madero, Tamaulipas, sin razón social, "
    "teléfono, correo ni página web. Uso conforme a los Términos de Libre Uso de la "
    "Información del INEGI.")

TEXTO_ERROR = ("Lo siento, no pude responder esa pregunta en este momento (falló la consulta al "
               "modelo o se agotó la cuota). Intenta de nuevo más tarde.")


# ---------------------------------------------------------------- funciones puras (sin red)

def leer_permitidos(texto):
    """'123, 456,,abc' -> {123, 456}. Vacío -> conjunto vacío (nadie autorizado)."""
    permitidos = set()
    for trozo in (texto or "").split(","):
        trozo = trozo.strip()
        if trozo.isdigit():
            permitidos.add(int(trozo))
    return permitidos


def partir_mensaje(texto, limite=LIMITE_TELEGRAM):
    """Trozos de <= limite caracteres, cortando de preferencia en un salto de línea."""
    trozos = []
    resto = texto or ""
    while len(resto) > limite:
        corte = resto.rfind("\n", 0, limite + 1)
        if corte > 0:
            trozos.append(resto[:corte])
            resto = resto[corte + 1:]          # el salto de línea se descarta
        else:
            trozos.append(resto[:limite])
            resto = resto[limite:]
    trozos.append(resto)
    return [t for t in trozos if t] or [""]


def usuario_anonimo(identificador):
    """Primeros 10 caracteres del SHA-256 del identificador: nunca el id real."""
    return hashlib.sha256(str(identificador).encode()).hexdigest()[:10]


# ---------------------------------------------------------------- manejadores

async def _autorizado(update, context):
    usuario = update.effective_user.id
    if usuario in context.bot_data["permitidos"]:
        return True
    await update.effective_message.reply_text(
        f"Este bot es privado. Tu identificador de Telegram es {usuario}.")
    return False


async def inicio(update, context):
    if await _autorizado(update, context):
        await update.effective_message.reply_text(TEXTO_START)


async def fuente(update, context):
    if await _autorizado(update, context):
        await update.effective_message.reply_text(TEXTO_FUENTE)


async def con_escribiendo(chat, funcion, *args):
    """Corre funcion en otro hilo y muestra 'escribiendo...' cada 4 s mientras tanto."""
    from telegram.constants import ChatAction
    tarea = asyncio.ensure_future(asyncio.to_thread(funcion, *args))
    while not tarea.done():
        try:
            await chat.send_action(ChatAction.TYPING)
        except Exception:
            pass                               # el aviso es cosmético; la respuesta importa
        await asyncio.wait([tarea], timeout=4)
    return tarea.result()                      # si la función falló, aquí se relanza


async def pregunta(update, context):
    if not await _autorizado(update, context):
        return
    datos = context.bot_data
    datos["contador"] += 1
    registro = datos["bitacora"].pregunta(
        f"TG-{datos['contador']}", canal="telegram",
        usuario=usuario_anonimo(update.effective_user.id))
    llamar = datos["crear_llamar"]()
    texto = update.effective_message.text
    try:
        fin = await con_escribiendo(update.effective_chat, agente.responder, texto,
                                    datos["herramientas"], datos["sistema"], llamar, registro)
        respuesta = fin["respuesta"]
    except Exception as error:
        registro.evento("error", tipo=type(error).__name__, mensaje=str(error))
        respuesta = TEXTO_ERROR
    for trozo in partir_mensaje(respuesta):
        await update.effective_message.reply_text(trozo)


# ---------------------------------------------------------------- arranque

def main(argv=None):
    parser = argparse.ArgumentParser(description="Bot de Telegram del agente del DENUE")
    parser.add_argument("--simulado", action="store_true")
    opciones = parser.parse_args(argv)
    preparar_consola()

    from dotenv import load_dotenv
    from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

    logging.basicConfig(level=logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)   # su URL contiene el token

    load_dotenv(RAIZ / ".env")
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise SystemExit("Falta TELEGRAM_BOT_TOKEN en el archivo .env")
    permitidos = leer_permitidos(os.environ.get("TELEGRAM_USUARIOS_PERMITIDOS", ""))

    llamar_real, modelo = crear_llamador(opciones.simulado)
    if opciones.simulado:
        from app.modelo_simulado import ModeloSimulado
        crear_llamar = ModeloSimulado            # uno nuevo por pregunta: guion desde el paso 1
    else:
        def crear_llamar():
            return llamar_real

    aplicacion = ApplicationBuilder().token(token).build()
    aplicacion.bot_data.update({
        "herramientas": cargar_herramientas(), "sistema": leer_sistema(),
        "crear_llamar": crear_llamar, "bitacora": Bitacora(modelo),
        "permitidos": permitidos, "contador": 0})
    aplicacion.add_handler(CommandHandler("start", inicio))
    aplicacion.add_handler(CommandHandler("fuente", fuente))
    aplicacion.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, pregunta))

    print(f"Bot en marcha (modelo: {modelo}). Usuarios autorizados: {len(permitidos)}. "
          "Ctrl+C para detener.")
    if not permitidos:
        print("AVISO: TELEGRAM_USUARIOS_PERMITIDOS está vacío: el bot no atenderá a nadie. "
              "Escríbele para ver tu identificador y agrégalo al .env.")
    aplicacion.run_polling()


if __name__ == "__main__":
    main()
