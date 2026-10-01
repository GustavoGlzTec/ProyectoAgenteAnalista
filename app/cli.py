"""Una pregunta desde la terminal.

    python -m app.cli "¿Cuántas farmacias hay en Tampico?" [--simulado]
    python -m app.cli "..." --simulado --max-herramientas 1     (para la traza E.1)
"""
import argparse

from app import agente
from app.comun import Bitacora, cargar_herramientas, crear_llamador, leer_sistema, preparar_consola


def main(argv=None):
    parser = argparse.ArgumentParser(description="Agente analista del DENUE (una pregunta)")
    parser.add_argument("pregunta")
    parser.add_argument("--simulado", action="store_true", help="usar el modelo simulado")
    parser.add_argument("--max-herramientas", type=int, help="cambia MAX_HERRAMIENTAS")
    parser.add_argument("--max-turnos", type=int, help="cambia MAX_TURNOS")
    opciones = parser.parse_args(argv)
    preparar_consola()

    if opciones.max_herramientas:
        agente.MAX_HERRAMIENTAS = opciones.max_herramientas
    if opciones.max_turnos:
        agente.MAX_TURNOS = opciones.max_turnos

    herramientas = cargar_herramientas()
    llamar, modelo = crear_llamador(opciones.simulado)
    bitacora = Bitacora(modelo)
    registro = bitacora.pregunta("CLI-1")
    try:
        fin = agente.responder(opciones.pregunta, herramientas, leer_sistema(), llamar, registro)
    except Exception as error:
        registro.evento("error", tipo=type(error).__name__, mensaje=str(error))
        print(f"No se pudo responder: {error}")
        return 1

    print(fin["respuesta"])
    print(f"\n-- Turnos: {fin['turnos']} · Herramientas: {fin['herramientas']} · "
          f"Segundos: {fin['segundos']} · Bitácora: logs/{bitacora.ruta.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
