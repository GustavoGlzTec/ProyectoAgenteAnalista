"""Parte C · La guardia de cifras.

El prompt PIDE no calcular; la guardia GARANTIZA que ninguna cifra salió de la nada:
toda cifra de la respuesta debe aparecer en la pregunta o en los resultados de las
herramientas de esa pregunta.
"""
import re

# "1. " o "2) " al inicio de un renglón: marcas de lista, no cifras.
_MARCA_LISTA = re.compile(r"^[ \t]*\d+[.)][ \t]", re.MULTILINE)

# Primero enteros con comas de miles (7,184), luego enteros o decimales con punto (5.5).
_NUMERO = re.compile(r"\d{1,3}(?:,\d{3})+(?!\d)(?:\.\d+)?|\d+(?:\.\d+)?")


def _a_numero(cadena):
    valor = float(cadena.replace(",", ""))
    return int(valor) if valor.is_integer() else valor   # 5.0 -> 5 ; 05 -> 5


def numeros(texto):
    """Conjunto de cifras de un texto: '7,184' -> 7184, '5.5' -> 5.5, '05' -> 5."""
    if not texto:
        return set()
    limpio = _MARCA_LISTA.sub("", str(texto))
    return {_a_numero(m) for m in _NUMERO.findall(limpio)}


def numeros_en(objeto):
    """Cifras dentro de dicts (sus valores), listas y textos, recursivamente."""
    encontrados = set()
    if objeto is None or isinstance(objeto, bool):      # bool va antes que int: True es int
        return encontrados
    if isinstance(objeto, dict):
        for valor in objeto.values():
            encontrados |= numeros_en(valor)
    elif isinstance(objeto, (list, tuple, set)):
        for elemento in objeto:
            encontrados |= numeros_en(elemento)
    elif isinstance(objeto, str):
        encontrados |= numeros(objeto)
    elif isinstance(objeto, (int, float)):
        encontrados |= numeros(str(objeto))
    return encontrados


def cifras_sin_respaldo(respuesta, pregunta, resultados):
    """Cifras de la respuesta que no están ni en la pregunta ni en los resultados, ordenadas."""
    respaldo = numeros(pregunta) | numeros_en(resultados)
    return sorted(numeros(respuesta) - respaldo)
