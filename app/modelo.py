"""La ÚNICA parte del programa que habla con Gemini.

La ejecución automática de funciones está DESACTIVADA: el modelo sólo pide
herramientas; nuestro ciclo (agente.responder) decide y ejecuta.
"""
import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

MODELO_POR_OMISION = "gemini-3.6-flash"
_cliente = None


def _obtener_cliente():
    global _cliente
    if _cliente is None:
        load_dotenv()
        _cliente = genai.Client(
            api_key=os.environ["GEMINI_API_KEY"],
            http_options=types.HttpOptions(retry_options=types.HttpRetryOptions(
                attempts=5, initial_delay=2.0, max_delay=30.0)))
    return _cliente


def nombre_modelo():
    load_dotenv()
    return os.environ.get("GEMINI_MODEL") or MODELO_POR_OMISION


def llamar_modelo(historial, sistema, declaraciones, forzar_texto=False):
    """Una llamada al modelo. Devuelve la respuesta del SDK tal cual."""
    config = types.GenerateContentConfig(
        system_instruction=sistema,
        tools=[types.Tool(function_declarations=declaraciones)],
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        tool_config=types.ToolConfig(function_calling_config=types.FunctionCallingConfig(
            mode="NONE" if forzar_texto else "AUTO")))   # NONE: prohibido pedir herramientas
    return _obtener_cliente().models.generate_content(
        model=nombre_modelo(), contents=historial, config=config)
