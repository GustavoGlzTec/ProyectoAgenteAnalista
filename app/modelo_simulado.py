"""Parte D · Modelo simulado: guion fijo de 4 pasos, sin red y sin gastar cuota.

Paso 1: pide buscar_actividades(texto="farmacia")                  id "sim-1"
Paso 2: pide contar(codigo_act="464111,464112", municipio="Tampico") id "sim-2"
Paso 3: texto con una cifra INVENTADA (160) -> la guardia debe atraparla
Paso 4: texto correcto (154)
Después del paso 4 vuelve al 1. Si forzar_texto es verdadero y el paso es una
petición, devuelve TEXTO_PRESUPUESTO (y de todos modos avanza un paso).
"""
from google.genai import types

TEXTO_INVENTADO = "Respuesta: En Tampico hay 160 farmacias.\nDatos: DENUE 05/2026, INEGI"
TEXTO_CORRECTO = ("Respuesta: En Tampico hay 154 farmacias (clases 464111 y 464112).\n"
                  "Datos: DENUE 05/2026, INEGI")
TEXTO_PRESUPUESTO = "Respuesta: No pude completar la consulta con el presupuesto."


def respuesta_falsa(partes):
    return types.GenerateContentResponse(candidates=[types.Candidate(
        content=types.Content(role="model", parts=partes))])


def _pedir(id_, nombre, args):
    return types.Part(function_call=types.FunctionCall(id=id_, name=nombre, args=args))


def _texto(texto):
    return types.Part(text=texto)


class ModeloSimulado:
    """Invocable con la misma firma que modelo.llamar_modelo."""

    def __init__(self):
        self.paso = 1

    def __call__(self, historial, sistema, declaraciones, forzar_texto=False):
        paso = self.paso
        self.paso = 1 if paso == 4 else paso + 1          # avanza siempre

        if paso in (1, 2) and forzar_texto:
            parte = _texto(TEXTO_PRESUPUESTO)
        elif paso == 1:
            parte = _pedir("sim-1", "buscar_actividades", {"texto": "farmacia"})
        elif paso == 2:
            parte = _pedir("sim-2", "contar", {"codigo_act": "464111,464112", "municipio": "Tampico"})
        elif paso == 3:
            parte = _texto(TEXTO_INVENTADO)
        else:
            parte = _texto(TEXTO_CORRECTO)
        return respuesta_falsa([parte])
