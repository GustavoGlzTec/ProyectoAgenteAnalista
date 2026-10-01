"""Parte B · El ciclo del agente: percibir, decidir, actuar, observar.

El ciclo es NUESTRO, no del SDK: el modelo sólo pide herramientas y este código
decide si las ejecuta, cuántas, y cuándo se obliga al modelo a redactar.
"""
import inspect
import time

from google.genai import types

from app.guardia import cifras_sin_respaldo
from app.herramientas import DECLARACIONES, NOMBRES_HERRAMIENTAS, ErrorArgumento

MAX_TURNOS = 5          # llamadas al modelo por pregunta
MAX_HERRAMIENTAS = 6    # herramientas ejecutadas por pregunta


class AgenteError(RuntimeError):
    """Falla del ciclo (no de una herramienta): se registra como evento 'error'."""


class _SinBitacora:
    def evento(self, evento, **campos):
        pass


# ---------------------------------------------------------------- 7.1 ejecutar

def _parametros(herramientas, nombre):
    try:
        return [p for p in inspect.signature(getattr(herramientas, nombre)).parameters]
    except (TypeError, ValueError, AttributeError):
        return None


def ejecutar(herramientas, nombre, args):
    """Ejecuta una herramienta declarada. Nunca lanza excepciones; nunca usa eval/exec."""
    if nombre not in NOMBRES_HERRAMIENTAS:
        return {"ok": False, "error": f"herramienta inexistente: {nombre}",
                "valores_validos": list(NOMBRES_HERRAMIENTAS)}
    try:
        return getattr(herramientas, nombre)(**dict(args or {}))
    except ErrorArgumento as error:
        return error.como_dict()
    except TypeError as error:          # p. ej. ciudad="Tampico": argumento que no existe
        return {"ok": False, "error": f"argumento no válido para {nombre}: {error}",
                "valores_validos": _parametros(herramientas, nombre)}
    except Exception as error:          # último recurso: ningún traceback llega al modelo
        return {"ok": False, "error": f"error interno en {nombre}: {type(error).__name__}",
                "valores_validos": None}


# ---------------------------------------------------------------- 7.2 responder

def _mensaje_usuario(texto):
    return types.Content(role="user", parts=[types.Part(text=texto)])


def _lista(cifras):
    return "[" + ", ".join(str(c) for c in cifras) + "]"


def mensaje_correccion(cifras):
    return ("Revisión automática: estas cifras de tu respuesta no aparecen en la pregunta ni en "
            f"los resultados de las herramientas: {_lista(cifras)}. No calcules sumas ni "
            "porcentajes: si necesitas un total, pídelo a una herramienta. Corrige la respuesta.")


def _tokens_entrada(respuesta):
    uso = getattr(respuesta, "usage_metadata", None)   # None en el simulado
    return getattr(uso, "prompt_token_count", None) if uso is not None else None


def responder(pregunta, herramientas, sistema, llamar, bitacora=None):
    """Responde una pregunta. Devuelve {respuesta, turnos, herramientas,
    cifras_sin_respaldo, segundos}. Lanza AgenteError si no logra una respuesta."""
    bitacora = bitacora or _SinBitacora()
    max_turnos, max_herramientas = MAX_TURNOS, MAX_HERRAMIENTAS   # se leen en cada llamada
    inicio = time.perf_counter()
    bitacora.evento("inicio", pregunta=pregunta)

    historial = [_mensaje_usuario(pregunta)]    # 1
    resultados = []
    usadas = 0
    corregida = False
    forzar_texto = False

    for turno in range(1, max_turnos + 1):                                  # 2
        if turno == max_turnos:                                             # 3
            forzar_texto = True
        respuesta = llamar(historial, sistema, DECLARACIONES, forzar_texto)  # 4
        bitacora.evento("modelo", turno=turno, forzar_texto=forzar_texto,
                        tokens_entrada=_tokens_entrada(respuesta))

        if not respuesta.candidates or respuesta.candidates[0].content is None:
            raise AgenteError("el modelo no devolvió contenido (¿respuesta bloqueada?)")
        historial.append(respuesta.candidates[0].content)                   # 5 tal como llegó

        pedidas = respuesta.function_calls or []
        if pedidas:                                                          # 6
            partes = []
            for peticion in pedidas:                                         # 7
                args = dict(peticion.args or {})
                if usadas >= max_herramientas:                               # 8
                    resultado = {"ok": False, "valores_validos": None, "error":
                                 "presupuesto agotado: no se ejecutan más herramientas en esta "
                                 "pregunta; redacta la respuesta con los resultados que ya tienes"}
                else:                                                        # 9
                    usadas += 1
                    resultado = ejecutar(herramientas, peticion.name, args)
                    resultados.append(resultado)
                bitacora.evento("herramienta", nombre=peticion.name, args=args,   # 10
                                ok=bool(resultado.get("ok")), error=resultado.get("error"))
                partes.append(types.Part(function_response=types.FunctionResponse(
                    id=peticion.id, name=peticion.name, response=resultado)))   # MISMO id
            historial.append(types.Content(role="user", parts=partes))       # 11
            if usadas >= max_herramientas:                                   # 12
                forzar_texto = True
            continue                                                         # 13

        texto = (respuesta.text or "").strip()                               # 14
        if not texto:   # el modelo no pidió nada ni escribió nada
            if turno < max_turnos:
                historial.append(_mensaje_usuario(
                    "Redacta ahora la respuesta final en texto, con el formato indicado."))
                continue
            break

        sin_respaldo = cifras_sin_respaldo(texto, pregunta, resultados)
        pide_correccion = bool(sin_respaldo) and not corregida and turno < max_turnos   # 16
        bitacora.evento("guardia", cifras_sin_respaldo=sin_respaldo,                  # 15
                        corregida=pide_correccion, segunda_revision=corregida)
        if pide_correccion:
            corregida = True                                                 # 17
            historial.append(_mensaje_usuario(mensaje_correccion(sin_respaldo)))  # 18
            continue

        if sin_respaldo:                                                     # 19
            texto += f"\n\n[Aviso] Cifras sin respaldo en los datos: {_lista(sin_respaldo)}"
        salida = {"respuesta": texto, "turnos": turno, "herramientas": usadas,
                  "cifras_sin_respaldo": sin_respaldo,
                  "segundos": round(time.perf_counter() - inicio, 2)}
        bitacora.evento("fin", **salida)                                     # 20
        return salida

    raise AgenteError("se agotaron los turnos sin una respuesta en texto")   # 21
