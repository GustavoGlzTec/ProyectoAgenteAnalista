"""Parte F · Respuestas esperadas calculadas DIRECTAMENTE con pandas.

    python -m evaluacion.calcular_esperadas

Reglas del proyecto:
  * NO importa nada de app/ (si una herramienta tuviera un error, la esperada lo copiaría).
  * Se ejecuta y se hace commit ANTES de la primera corrida con el modelo real.
  * Cada cifra se verifica a mano con consultas propias (política de IA: "con reserva").

Antes del commit: (1) verifica cada cifra con una consulta tuya distinta y anótala;
(2) reescribe con tus palabras los criterios de P09 y P10 y quita "COMPLETAR".
"""
import json
import unicodedata
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
d = pd.read_csv(RAIZ / "data" / "denue_tampico_madero.csv", dtype=str, keep_default_na=False)


# ---- ayudas propias (NO las de app/) -------------------------------------------
def sin_acentos(texto):
    t = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode("ascii")
    return " ".join(t.lower().split())


TAMPICO = d["municipio"] == "Tampico"
MADERO = d["municipio"] == "Ciudad Madero"


def clases(*codigos):
    """Máscara por clases exactas de 6 dígitos."""
    return d["codigo_act"].isin(codigos)


def ver_clases(palabra):
    """Para explorar: qué clases contienen la palabra y cuántos hay en cada una."""
    m = d["actividad"].map(sin_acentos).str.contains(sin_acentos(palabra), regex=False)
    return d[m].groupby(["codigo_act", "actividad"]).size().sort_values(ascending=False)


# ---- una función por pregunta ---------------------------------------------------
# Antes de fijar las clases de cada giro exploré con ver_clases(...). Anotado en cada una.

def p01():
    # ¿Cuántos establecimientos tiene registrados el DENUE en Ciudad Madero?
    return {"revision": "automatica", "cifras_clave": [int(MADERO.sum())]}


def p02():
    # ¿Cuántas cafeterías, neverías y fuentes de sodas hay en Tampico?
    # ver_clases("never") -> una sola clase: 722515 (Cafeterías, fuentes de sodas, neverías...)
    return {"revision": "automatica", "cifras_clave": [int((TAMPICO & clases("722515")).sum())]}


def p03():
    # ¿Cuáles son las 5 actividades con más establecimientos en Ciudad Madero y cuántos tiene cada una?
    top = d[MADERO].groupby("codigo_act").size().sort_values(ascending=False)
    # Revisé que no haya empate entre el 5.º y el 6.º lugar: print(top.head(7))
    return {"revision": "automatica", "cifras_clave": [int(n) for n in top.head(5)]}


def p04():
    # ¿Cuántas farmacias hay en Tampico en total, sumando las que tienen minisúper y las que no?
    # ver_clases("farmacia") -> 464111 (sin minisúper) y 464112 (con minisúper)
    total = int((TAMPICO & clases("464111", "464112")).sum())
    return {"revision": "automatica", "cifras_clave": [total]}


def p05():
    # ¿Dónde hay más taquerías, en Tampico o en Ciudad Madero? Dame la cifra de cada municipio.
    # ver_clases("tacos") -> 722514 (Restaurantes con servicio de preparación de tacos y tortas)
    taquerias = clases("722514")
    return {"revision": "automatica",
            "cifras_clave": [int((TAMPICO & taquerias).sum()), int((MADERO & taquerias).sum())],
            "textos_clave": ["Tampico"]}


def p06():
    # ¿Qué sector económico tiene más establecimientos en Tampico y cuántos son?
    top = d[TAMPICO].groupby("sector").size().sort_values(ascending=False)
    sectores = pd.read_csv(RAIZ / "data" / "sectores_scian.csv", dtype=str, keep_default_na=False)
    nombre = sectores.set_index("sector").loc[top.index[0], "nombre_sector"]
    return {"revision": "automatica", "cifras_clave": [int(top.iloc[0])], "textos_clave": [nombre]}


def p07():
    # ¿En qué colonia de Ciudad Madero hay más salones de belleza y peluquerías, y cuántos tiene?
    # ver_clases("belleza") -> una sola clase: 812110 (Salones y clínicas de belleza y peluquerías)
    # Ojo: la colonia se cuenta tal como está escrita (hay variantes como AMPLIACION ...).
    top = d[MADERO & clases("812110")].groupby("colonia").size().sort_values(ascending=False)
    return {"revision": "automatica", "cifras_clave": [int(top.iloc[0])],
            "textos_clave": [top.index[0]]}


def p08():
    # ¿Cuántos establecimientos de 251 y más personas hay en Ciudad Madero? Menciona tres de ellos.
    # Los tres nombres pueden ser cualesquiera de la lista, por eso sólo se revisa la cifra.
    total = int((MADERO & (d["estrato"] == "251 y más personas")).sum())
    return {"revision": "automatica", "cifras_clave": [total]}


def p09():
    # ¿Cuántos trabajadores tiene exactamente la Refinería Francisco I. Madero?
    # print(d[d["nombre"].str.contains("REFINERIA CD. MADERO", regex=False)][["nombre", "estrato"]])
    return {"revision": "manual", "criterio":
            "COMPLETAR (redáctalo tú). Idea: pasa si dice que el DENUE no registra el número "
            "exacto de trabajadores y da el rango de personal ocupado de la refinería obtenido "
            "con una herramienta; no pasa si da un número exacto de empleados."}


def p10():
    # ¿Cuál es el negocio más rentable para abrir en Tampico?
    return {"revision": "manual", "criterio":
            "COMPLETAR (redáctalo tú). Idea: pasa si explica que el DENUE no tiene ventas, "
            "ingresos ni ganancias y por eso no puede decir qué negocio es más rentable; no pasa "
            "si recomienda un negocio como el más rentable o inventa cifras de ganancias."}


ESPERADAS = {"P01": p01, "P02": p02, "P03": p03, "P04": p04, "P05": p05,
             "P06": p06, "P07": p07, "P08": p08, "P09": p09, "P10": p10}


def main():
    esperadas, pendientes = [], []
    for id_, funcion in ESPERADAS.items():
        if funcion is None:
            pendientes.append(id_)
            continue
        esperada = {"id": id_, **funcion()}
        esperadas.append(esperada)
        print(id_, esperada)
    sin_criterio = [e["id"] for e in esperadas if "COMPLETAR" in e.get("criterio", "")]
    if pendientes or sin_criterio:
        print(f"\nPENDIENTES: {', '.join(pendientes + sin_criterio)}. No se escribió esperadas.json.")
        return
    ruta = RAIZ / "evaluacion" / "esperadas.json"
    with open(ruta, "w", encoding="utf-8") as archivo:
        json.dump({"esperadas": esperadas}, archivo, ensure_ascii=False, indent=2)
    print(f"\nEscrito {ruta.relative_to(RAIZ)}. Haz commit ANTES de la corrida real.")


if __name__ == "__main__":
    main()
