"""Piezas compartidas por cli, lote y bot: rutas, carga, llamador y bitácora.

No contiene lógica del agente (eso vive en agente.py).
"""
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from app.herramientas import Herramientas, cargar_datos

RAIZ = Path(__file__).resolve().parent.parent
RUTA_DENUE = RAIZ / "data" / "denue_tampico_madero.csv"
RUTA_SECTORES = RAIZ / "data" / "sectores_scian.csv"
RUTA_SISTEMA = RAIZ / "prompts" / "sistema.md"
RUTA_PREGUNTAS = RAIZ / "data" / "preguntas_prueba.json"
DIR_LOGS = RAIZ / "logs"


def preparar_consola():
    """Evita errores de acentos en la terminal de Windows."""
    for flujo in (sys.stdout, sys.stderr):
        try:
            flujo.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass


def cargar_herramientas(ruta_denue=RUTA_DENUE, ruta_sectores=RUTA_SECTORES):
    datos, sectores = cargar_datos(ruta_denue, ruta_sectores)
    return Herramientas(datos, sectores)


def leer_sistema():
    return RUTA_SISTEMA.read_text(encoding="utf-8")


def crear_llamador(simulado):
    """Devuelve (funcion_llamar, nombre_del_modelo)."""
    if simulado:
        from app.modelo_simulado import ModeloSimulado
        return ModeloSimulado(), "simulado"
    load_dotenv(RAIZ / ".env")
    if not os.environ.get("GEMINI_API_KEY"):
        raise SystemExit("Falta GEMINI_API_KEY en el archivo .env (o usa --simulado).")
    from app.modelo import llamar_modelo, nombre_modelo
    return llamar_modelo, nombre_modelo()


class Bitacora:
    """logs/corrida-AAAAMMDD-HHMMSS.jsonl: una línea JSON por evento."""

    def __init__(self, modelo, directorio=DIR_LOGS):
        self.corrida = "corrida-" + datetime.now().strftime("%Y%m%d-%H%M%S")
        self.modelo = modelo
        directorio = Path(directorio)
        directorio.mkdir(parents=True, exist_ok=True)
        self.ruta = directorio / f"{self.corrida}.jsonl"

    def escribir(self, id_pregunta, evento, **campos):
        linea = {"ts": datetime.now().isoformat(timespec="seconds"), "corrida": self.corrida,
                 "modelo": self.modelo, "id": id_pregunta, "evento": evento, **campos}
        with open(self.ruta, "a", encoding="utf-8") as archivo:
            archivo.write(json.dumps(linea, ensure_ascii=False, default=str) + "\n")

    def pregunta(self, id_pregunta, **extra_inicio):
        """Bitácora 'atada' a una pregunta; extra_inicio se agrega al evento inicio."""
        return BitacoraPregunta(self, id_pregunta, extra_inicio)


class BitacoraPregunta:
    def __init__(self, bitacora, id_pregunta, extra_inicio):
        self.bitacora = bitacora
        self.id = id_pregunta
        self.extra_inicio = extra_inicio

    def evento(self, evento, **campos):
        if evento == "inicio":
            campos = {**campos, **self.extra_inicio}
        self.bitacora.escribir(self.id, evento, **campos)
