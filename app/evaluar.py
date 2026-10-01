"""Parte F · Compara las respuestas del agente con evaluacion/esperadas.json.

    python -m app.evaluar logs/corrida-A.jsonl logs/corrida-B.jsonl

Toma, de las bitácoras dadas, el ÚLTIMO evento 'fin' real (modelo != simulado)
de cada pregunta. Una pregunta automática pasa si numeros(respuesta) contiene
todas sus cifras_clave y la respuesta normalizada contiene sus textos_clave.
"""
import argparse
import json

from app.comun import RAIZ, preparar_consola
from app.guardia import numeros
from app.herramientas import normalizar

RUTA_ESPERADAS = RAIZ / "evaluacion" / "esperadas.json"
RUTA_RESULTADOS = RAIZ / "evaluacion" / "resultados.json"


def leer_eventos(rutas):
    eventos = []
    for ruta in rutas:
        with open(ruta, encoding="utf-8") as archivo:
            eventos += [json.loads(linea) for linea in archivo if linea.strip()]
    return sorted(eventos, key=lambda e: e.get("ts", ""))   # estable: respeta el orden dado


def ultimos_fin_reales(eventos):
    fines = {}
    for e in eventos:
        if e.get("evento") == "fin" and e.get("modelo") != "simulado":
            fines[e["id"]] = e
    return fines


def llamadas_reales(eventos, ids):
    return sum(1 for e in eventos
               if e.get("evento") == "modelo" and e.get("modelo") != "simulado" and e["id"] in ids)


def evaluar_una(esperada, fin):
    fila = {"id": esperada["id"], "revision": esperada["revision"]}
    if fin is None:
        return {**fila, "resultado": "SIN CORRIDA", "turnos": None, "herramientas": None,
                "cifras_sin_respaldo": None, "respuesta": None}
    fila.update({"turnos": fin["turnos"], "herramientas": fin["herramientas"],
                 "cifras_sin_respaldo": fin["cifras_sin_respaldo"], "respuesta": fin["respuesta"]})
    if esperada["revision"] == "manual":
        return {**fila, "resultado": "MANUAL", "criterio": esperada.get("criterio", "")}

    encontradas = numeros(fin["respuesta"])
    faltan_cifras = [c for c in esperada.get("cifras_clave", []) if c not in encontradas]
    texto = normalizar(fin["respuesta"])
    faltan_textos = [t for t in esperada.get("textos_clave", []) if normalizar(t) not in texto]
    pasa = not faltan_cifras and not faltan_textos
    return {**fila, "resultado": "PASA" if pasa else "FALLA",
            "faltan_cifras": faltan_cifras, "faltan_textos": faltan_textos}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Evalúa las corridas contra las esperadas")
    parser.add_argument("bitacoras", nargs="+")
    opciones = parser.parse_args(argv)
    preparar_consola()

    with open(RUTA_ESPERADAS, encoding="utf-8") as archivo:
        esperadas = json.load(archivo)["esperadas"]
    eventos = leer_eventos(opciones.bitacoras)
    fines = ultimos_fin_reales(eventos)
    filas = [evaluar_una(e, fines.get(e["id"])) for e in esperadas]

    print(f"{'ID':<5}{'REVISION':<12}{'RESULTADO':<13}{'TURNOS':>7}{'HERR.':>7}  SIN RESPALDO")
    for f in filas:
        print(f"{f['id']:<5}{f['revision']:<12}{f['resultado']:<13}"
              f"{str(f['turnos'] or '-'):>7}{str(f['herramientas'] or '-'):>7}  "
              f"{f['cifras_sin_respaldo'] if f['cifras_sin_respaldo'] is not None else '-'}")
        if f["resultado"] == "FALLA":
            print(f"     faltan cifras {f['faltan_cifras']} · faltan textos {f['faltan_textos']}")
    for f in filas:
        if f["resultado"] == "MANUAL":
            print(f"\n{f['id']} (manual) criterio: {f['criterio']}\n  respuesta: {f['respuesta']}")

    automaticas = [f for f in filas if f["revision"] == "automatica"]
    totales = {
        "aprobadas_automaticas": sum(f["resultado"] == "PASA" for f in automaticas),
        "total_automaticas": len(automaticas),
        "manuales": sum(f["revision"] == "manual" for f in filas),
        "llamadas_en_respuestas_finales": sum(f["turnos"] or 0 for f in filas),
        "llamadas_reales_en_bitacoras": llamadas_reales(eventos, {f["id"] for f in filas}),
    }
    print(f"\nAutomáticas aprobadas: {totales['aprobadas_automaticas']}/{totales['total_automaticas']}"
          f" · manuales: {totales['manuales']} (revísalas tú)"
          f" · llamadas al modelo: {totales['llamadas_reales_en_bitacoras']}")

    with open(RUTA_RESULTADOS, "w", encoding="utf-8") as archivo:
        json.dump({"bitacoras": opciones.bitacoras, "totales": totales, "preguntas": filas},
                  archivo, ensure_ascii=False, indent=2)
    print(f"Escrito {RUTA_RESULTADOS.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
