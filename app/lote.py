"""Parte F · Corre el banco de preguntas de data/preguntas_prueba.json.

    python -m app.lote --simulado
    python -m app.lote --desde P01 --hasta P05
Si una pregunta falla, registra un evento 'error' y sigue con la siguiente.
"""
import argparse
import json
import time

from app import agente
from app.comun import (RUTA_PREGUNTAS, Bitacora, cargar_herramientas, crear_llamador,
                       leer_sistema, preparar_consola)
from app.modelo_simulado import ModeloSimulado

PAUSA_SEGUNDOS = 4


def leer_preguntas(ruta=RUTA_PREGUNTAS):
    """Acepta una lista de preguntas o un objeto con la lista dentro."""
    with open(ruta, encoding="utf-8") as archivo:
        contenido = json.load(archivo)
    if isinstance(contenido, dict):
        contenido = contenido.get("preguntas") or next(
            v for v in contenido.values() if isinstance(v, list))
    return [{"id": p["id"], "pregunta": p.get("pregunta") or p.get("texto")} for p in contenido]


def seleccionar(preguntas, desde=None, hasta=None):
    ids = [p["id"] for p in preguntas]
    for extremo in (desde, hasta):
        if extremo and extremo not in ids:
            raise SystemExit(f"No existe la pregunta {extremo}. Ids: {', '.join(ids)}")
    inicio = ids.index(desde) if desde else 0
    final = ids.index(hasta) if hasta else len(ids) - 1
    return preguntas[inicio:final + 1]


def main(argv=None):
    parser = argparse.ArgumentParser(description="Corre el banco de preguntas")
    parser.add_argument("--desde")
    parser.add_argument("--hasta")
    parser.add_argument("--simulado", action="store_true")
    opciones = parser.parse_args(argv)
    preparar_consola()

    preguntas = seleccionar(leer_preguntas(), opciones.desde, opciones.hasta)
    herramientas = cargar_herramientas()
    sistema = leer_sistema()
    llamar_real, modelo = crear_llamador(opciones.simulado)
    bitacora = Bitacora(modelo)
    print(f"Bitácora: logs/{bitacora.ruta.name} · modelo: {modelo} · {len(preguntas)} preguntas\n")

    for numero, p in enumerate(preguntas):
        if numero > 0 and not opciones.simulado:
            time.sleep(PAUSA_SEGUNDOS)
        llamar = ModeloSimulado() if opciones.simulado else llamar_real
        registro = bitacora.pregunta(p["id"])
        print(f"== {p['id']}: {p['pregunta']}")
        try:
            fin = agente.responder(p["pregunta"], herramientas, sistema, llamar, registro)
            print(fin["respuesta"])
            print(f"-- turnos {fin['turnos']} · herramientas {fin['herramientas']} · "
                  f"{fin['segundos']} s\n")
        except Exception as error:
            registro.evento("error", tipo=type(error).__name__, mensaje=str(error))
            print(f"ERROR en {p['id']}: {type(error).__name__}: {error}\n")


if __name__ == "__main__":
    main()
