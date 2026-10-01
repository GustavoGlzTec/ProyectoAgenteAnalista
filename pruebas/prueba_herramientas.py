"""Parte D · Pruebas sin red.   python -m pruebas.prueba_herramientas

Usa el archivo COMPLETO data/denue_tampico_madero.csv y cifras publicadas en el
enunciado y en data/diccionario_datos.md (22900 filas, 7184 en Ciudad Madero,
154 farmacias en Tampico, 866 taquerías...).
Cada comprobación es un `assert` en su propio renglón, seguido de ok("...").
"""
import hashlib
import sys

from app.agente import ejecutar, responder
from app.bot import leer_permitidos, partir_mensaje, usuario_anonimo
from app.comun import RUTA_DENUE, RUTA_SECTORES, preparar_consola
from app.guardia import cifras_sin_respaldo, numeros, numeros_en
from app.herramientas import ESTRATOS, MUNICIPIOS, Herramientas, cargar_datos, normalizar
from app.modelo_simulado import ModeloSimulado

comprobaciones = 0


def ok(descripcion):
    """Se llama después de cada assert que pasó."""
    global comprobaciones
    comprobaciones += 1
    print(f"  ok  {descripcion}")


class BitacoraMemoria:
    def __init__(self):
        self.eventos = []

    def evento(self, evento, **campos):
        self.eventos.append({"evento": evento, **campos})


# ------------------------------------------------------------------ E.2 (TU TRAZA)
# Llena ESPERADO_E2 con lo que predijiste A MANO en traza_manual.md (sección E.2):
# la lista ordenada que debe devolver cifras_sin_respaldo para cada respuesta.
# Mientras quede algún None, la prueba termina en PENDIENTE (código de salida 1).
PREGUNTA_E2 = ("¿Dónde hay más taquerías, en Tampico o en Ciudad Madero? "
               "Dame la cifra de cada municipio.")
RESULTADOS_E2 = [
    {"ok": True, "fuente": "DENUE 05/2026, INEGI",
     "actividades": [{"codigo_act": "722514",
                      "actividad": "Restaurantes con servicio de preparación de tacos y tortas",
                      "establecimientos": 866}]},
    {"ok": True, "fuente": "DENUE 05/2026, INEGI", "por": "municipio",
     "filtros": {"codigo_act": "722514"}, "total_filtrado": 866,
     "filas": [{"valor": "Tampico", "total": 570}, {"valor": "Ciudad Madero", "total": 296}]},
]
RESPUESTAS_E2 = {
    "G1": "Tampico tiene 570 taquerías y Ciudad Madero 296.",
    "G2": "Tampico tiene 570 y Madero 296: una diferencia de 274.",
    "G3": "En total hay 866; Tampico concentra el 65.8 %.",
    "G4": "1. Tampico: 570\n2. Ciudad Madero: 296\nClase SCIAN 722514, DENUE 05/2026.",
    "G5": "Tampico tiene 1,570 taquerías.",
    "G6": "Ciudad Madero tiene 570 taquerías y Tampico 296.",
}
ESPERADO_E2 = {"G1": None, "G2": None, "G3": None, "G4": None, "G5": None, "G6": None}


def main():
    preparar_consola()

    print("Datos y normalizar")
    datos, sectores = cargar_datos(RUTA_DENUE, RUTA_SECTORES)
    h = Herramientas(datos, sectores)
    assert len(datos) == 22900, "el archivo completo tiene 22900 establecimientos"
    ok("el archivo completo tiene 22900 establecimientos")
    assert normalizar(" Cafeterías,   Neverías") == "cafeterias, neverias", "normalizar"
    ok("normalizar quita acentos y colapsa espacios")
    assert datos["codigo_act"].map(type).eq(str).all(), "codigo_act debe ser texto"
    ok("codigo_act se leyó como texto, no como número")

    print("Herramientas sobre el archivo completo")
    assert h.contar()["total"] == 22900, "contar sin filtros"
    ok("contar() sin filtros = 22900")
    r = h.contar(municipio="ciudad madero")
    assert r["total"] == 7184 and r["filtros"]["municipio"] == "Ciudad Madero", "contar Madero"
    ok("contar Ciudad Madero = 7184, con el municipio corregido en filtros")
    r = h.contar(codigo_act="464111,464112", municipio="Tampico")
    assert r["ok"] and r["total"] == 154, "farmacias en Tampico"
    ok("contar farmacias 464111,464112 en Tampico = 154")
    assert h.contar(codigo_act="722514")["total"] == 866, "taquerías"
    ok("contar taquerías 722514 = 866")
    r = h.ranking(por="municipio", codigo_act="722514")
    assert [(f["valor"], f["total"]) for f in r["filas"]] == [("Tampico", 570), ("Ciudad Madero", 296)]
    ok("ranking de taquerías por municipio: 570 y 296")
    r = h.ranking(por="municipio")
    assert sum(f["total"] for f in r["filas"]) == 22900, "suma de municipios"
    ok("los dos municipios suman 22900")
    r = h.ranking(por="codigo_act", codigo_act="464111,464112", municipio="Tampico")
    assert sorted(f["total"] for f in r["filas"]) == [36, 118] and "actividad" in r["filas"][0]
    ok("ranking por clase de farmacias en Tampico: 118 y 36, con actividad")
    r = h.ranking(por="colonia", top=99)
    assert r["ok"] and len(r["filas"]) == 20, "top se ajusta a 20"
    ok("top fuera de rango se ajusta a 20")
    r = h.ranking(por="sector", top=3)
    assert r["filas"][0]["nombre_sector"] != "", "nombre_sector"
    ok("ranking por sector trae nombre_sector")
    codigos = {a["codigo_act"] for a in h.buscar_actividades("farmacias")["actividades"]}
    assert {"464111", "464112"} <= codigos, "buscar farmacias"
    ok("buscar_actividades('farmacias') halla 464111 y 464112")
    r = h.buscar_actividades("zzqxw")
    assert r["ok"] and r["actividades"] == [], "buscar sin coincidencias"
    ok("buscar sin coincidencias: lista vacía, no error")
    r = h.listar(limite=3, codigo_act="464111", municipio="Tampico")
    assert r["mostrados"] == 3 and r["total"] == 118, "listar con limite"
    ok("listar respeta limite y cuenta el total")
    rango = [normalizar(e) for e in ESTRATOS]
    orden = [rango.index(normalizar(e["estrato"]))
             for e in h.listar(limite=20, municipio="Tampico")["establecimientos"]]
    assert orden == sorted(orden, reverse=True), "orden de listar"
    ok("listar ordena del estrato mayor al menor")
    r = h.contar(colonia="zona centro", municipio="Tampico")
    assert r["ok"] and r["filtros"]["colonia"] == "ZONA CENTRO", "colonia exacta"
    ok("colonia exacta sin importar mayúsculas")
    r = h.contar(colonia="centro de la galaxia")
    assert not r["ok"] and isinstance(r["valores_validos"], list), "colonia inexistente"
    ok("colonia inexistente: error con sugerencias")

    print("Errores estructurados de ejecutar")
    r = ejecutar(h, "contar", {"municipio": "Altamira"})
    assert not r["ok"] and r["valores_validos"] == MUNICIPIOS, "municipio inválido"
    ok("municipio inválido")
    r = ejecutar(h, "contar", {"codigo_act": "46A1"})
    assert not r["ok"] and "error" in r, "código con letras"
    ok("código con letras")
    r = ejecutar(h, "listar", {})
    assert not r["ok"], "listar sin filtros"
    ok("listar sin filtros")
    r = ejecutar(h, "borrar_todo", {})
    assert not r["ok"] and r["error"].startswith("herramienta inexistente"), "herramienta inexistente"
    ok("herramienta inexistente")
    r = ejecutar(h, "contar", {"ciudad": "Tampico"})
    assert not r["ok"] and "ciudad" in r["error"], "argumento inexistente"
    ok("argumento inexistente")
    r = ejecutar(h, "contar", {"estrato": "muchos"})
    assert not r["ok"] and r["valores_validos"] == ESTRATOS, "estrato inválido"
    ok("estrato inválido lista los 7")

    print("Guardia")
    assert numeros("Hay 7,184 negocios y 5.5 %") == {7184, 5.5}, "comas y decimales"
    ok("numeros con comas de miles y decimales")
    assert numeros("1. Tampico: 570\n2) Madero: 296") == {570, 296}, "marcas de lista"
    ok("numeros quita marcas de lista")
    assert numeros("5.0 y 05/2026") == {5, 2026}, "5.0 y 05"
    ok("5.0 -> 5 y 05 -> 5")
    assert numeros_en({"a": [1, "x 22"], "b": True, "c": None}) == {1, 22}, "numeros_en"
    ok("numeros_en recorre dicts y listas; True y None no aportan")

    print("Traza E.2 (valores que tú predijiste)")
    pendientes = [g for g, v in ESPERADO_E2.items() if v is None]
    for g, esperado in ESPERADO_E2.items():
        if esperado is not None:
            assert cifras_sin_respaldo(RESPUESTAS_E2[g], PREGUNTA_E2, RESULTADOS_E2) == esperado, g
            ok(f"traza E.2 {g}")

    print("Ciclo completo con el simulado")
    bitacora = BitacoraMemoria()
    fin = responder("¿Cuántas farmacias hay en Tampico?", h, "sistema", ModeloSimulado(), bitacora)
    assert fin["turnos"] == 4, "turnos"
    ok("el simulado termina en el turno 4")
    assert fin["herramientas"] == 2, "herramientas"
    ok("usó 2 herramientas")
    assert "154 farmacias" in fin["respuesta"] and "[Aviso]" not in fin["respuesta"], "respuesta"
    ok("respuesta final corregida (154) y sin aviso")
    assert fin["cifras_sin_respaldo"] == [], "sin respaldo"
    ok("sin cifras sin respaldo al final")
    assert [e["evento"] for e in bitacora.eventos] == [
        "inicio", "modelo", "herramienta", "modelo", "herramienta", "modelo", "guardia",
        "modelo", "guardia", "fin"], "secuencia de eventos"
    ok("secuencia de eventos del ciclo")
    assert bitacora.eventos[6]["cifras_sin_respaldo"] == [160], "guardia atrapa 160"
    ok("la guardia atrapó el 160")

    print("Funciones puras del bot")
    assert leer_permitidos("123, 456,,abc") == {123, 456}, "leer_permitidos"
    ok("leer_permitidos ignora basura")
    assert leer_permitidos("") == set(), "lista vacía"
    ok("lista vacía: nadie autorizado")
    trozos = partir_mensaje("línea de prueba número\n" * 600)
    assert len(trozos) >= 3 and all(len(t) <= 4096 and not t.startswith("\n") for t in trozos)
    ok("partir_mensaje corta en saltos de línea, trozos <= 4096")
    assert [len(t) for t in partir_mensaje("x" * 10000)] == [4096, 4096, 1808], "corte duro"
    ok("partir_mensaje corta a 4096 si no hay saltos")
    assert usuario_anonimo(123456789) == hashlib.sha256(b"123456789").hexdigest()[:10], "hash"
    ok("usuario_anonimo = 10 caracteres del SHA-256")

    print(f"\n{comprobaciones} comprobaciones pasaron.")
    if pendientes:
        print(f"PENDIENTE: llena ESPERADO_E2 ({', '.join(pendientes)}) con tu traza a mano.")
        sys.exit(1)
    print("OK")


if __name__ == "__main__":
    main()
