"""Parte A · Herramientas sobre el DENUE.

El modelo NUNCA ve los datos: sólo ve DECLARACIONES (el "menú" de herramientas).
Cuando pide una, agente.ejecutar() llama al método de la clase Herramientas.

Regla: las herramientas no truenan. Un argumento inválido lanza ErrorArgumento
internamente, y el decorador @_seguro lo convierte en
{"ok": False, "error": "...", "valores_validos": [...] o None}.
"""
import functools
import re
import unicodedata

import pandas as pd

FUENTE = "DENUE 05/2026, INEGI"
MUNICIPIOS = ["Tampico", "Ciudad Madero"]
ESTRATOS = [
    "0 a 5 personas",
    "6 a 10 personas",
    "11 a 30 personas",
    "31 a 50 personas",
    "51 a 100 personas",
    "101 a 250 personas",
    "251 y más personas",
]
POR_VALIDOS = ["municipio", "colonia", "sector", "codigo_act", "estrato"]
FILTROS = ["municipio", "codigo_act", "sector", "estrato", "colonia"]
NOMBRES_HERRAMIENTAS = ["buscar_actividades", "contar", "ranking", "listar"]
MAX_ACTIVIDADES = 15
MAX_TOP = 20
MAX_LIMITE = 20


class ErrorArgumento(ValueError):
    """Argumento inválido. Se convierte en un error estructurado, nunca llega como traceback."""

    def __init__(self, mensaje, valores_validos=None):
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.valores_validos = valores_validos

    def como_dict(self):
        return {"ok": False, "error": self.mensaje, "valores_validos": self.valores_validos}


# ---------------------------------------------------------------- utilidades

def normalizar(texto):
    """Minúsculas, sin acentos (NFKD y sólo ASCII) y espacios colapsados.

    " Cafeterías,   Neverías" -> "cafeterias, neverias"
    """
    if texto is None:
        return ""
    descompuesto = unicodedata.normalize("NFKD", str(texto))
    solo_ascii = descompuesto.encode("ascii", "ignore").decode("ascii")
    return " ".join(solo_ascii.lower().split())


def cargar_datos(ruta_denue, ruta_sectores):
    """Lee los dos CSV como texto y agrega colonia_norm y actividad_norm.

    Devuelve (DataFrame, dict sector -> nombre del sector).
    """
    datos = pd.read_csv(ruta_denue, dtype=str, keep_default_na=False, encoding="utf-8")
    datos["colonia_norm"] = datos["colonia"].map(normalizar)
    datos["actividad_norm"] = datos["actividad"].map(normalizar)

    tabla = pd.read_csv(ruta_sectores, dtype=str, keep_default_na=False, encoding="utf-8")
    # Primera columna: clave del sector; segunda: su nombre.
    clave, nombre = tabla.columns[0], tabla.columns[1]
    sectores = dict(zip(tabla[clave].str.strip(), tabla[nombre].str.strip()))
    return datos, sectores


def _dado(valor):
    """Un filtro cuenta como dado si no es None ni texto vacío."""
    return valor is not None and str(valor).strip() != ""


def _singular(palabra):
    """Plurales sencillos: hospitales -> hospital, farmacias -> farmacia."""
    if len(palabra) > 5 and palabra.endswith("es"):
        return palabra[:-2]
    if len(palabra) > 4 and palabra.endswith("s"):
        return palabra[:-1]
    return palabra


def _palabras(texto):
    """Palabras normalizadas de 3 letras o más, ya en singular."""
    return [_singular(p) for p in re.findall(r"[a-z0-9]+", normalizar(texto)) if len(p) >= 3]


def _entero_en_rango(valor, omision, minimo, maximo, nombre):
    """Convierte a entero (Gemini a veces manda 5.0) y lo ajusta al rango."""
    if valor is None or str(valor).strip() == "":
        return omision
    try:
        numero = int(float(valor))
    except (TypeError, ValueError):
        raise ErrorArgumento(f"'{nombre}' debe ser un número entero entre {minimo} y {maximo}")
    return max(minimo, min(maximo, numero))


def _seguro(metodo):
    """Convierte ErrorArgumento en un error estructurado."""
    @functools.wraps(metodo)
    def envoltura(self, *args, **kwargs):
        try:
            return metodo(self, *args, **kwargs)
        except ErrorArgumento as error:
            return error.como_dict()
    return envoltura


# ---------------------------------------------------------------- herramientas

class Herramientas:
    def __init__(self, datos, sectores):
        self.datos = datos
        self.sectores = sectores
        self._estrato_norm = datos["estrato"].map(normalizar)
        self._orden_estrato = {normalizar(e): i for i, e in enumerate(ESTRATOS)}
        self._sectores_validos = sorted(set(datos["sector"]) - {""})
        unicos = datos.drop_duplicates("codigo_act")
        self._actividad_de = dict(zip(unicos["codigo_act"], unicos["actividad"]))

    # -- filtros comunes (sección 6.2) -------------------------------------
    def _filtrar(self, municipio=None, codigo_act=None, sector=None, estrato=None, colonia=None):
        d = self.datos
        mascara = pd.Series(True, index=d.index)
        filtros = {}

        if _dado(municipio):
            canonicos = {normalizar(m): m for m in MUNICIPIOS}
            buscado = normalizar(municipio)
            if buscado not in canonicos:
                raise ErrorArgumento(f"municipio no válido: '{municipio}'", MUNICIPIOS)
            mascara &= d["municipio"] == canonicos[buscado]
            filtros["municipio"] = canonicos[buscado]

        if _dado(codigo_act):
            codigos = [c.strip() for c in str(codigo_act).split(",") if c.strip()]
            for codigo in codigos:
                if not re.fullmatch(r"[0-9]{2,6}", codigo):
                    raise ErrorArgumento(
                        f"código SCIAN no válido: '{codigo}'. Cada código debe tener sólo "
                        "dígitos y medir de 2 a 6; separa varios con coma.")
            mascara &= d["codigo_act"].str.startswith(tuple(codigos))
            filtros["codigo_act"] = ",".join(codigos)

        if _dado(sector):
            valor = str(sector).strip()
            if valor not in self._sectores_validos:
                raise ErrorArgumento(f"sector no existe: '{sector}'", self._sectores_validos)
            mascara &= d["sector"] == valor
            filtros["sector"] = valor

        if _dado(estrato):
            buscado = normalizar(estrato)
            if buscado not in self._orden_estrato:
                raise ErrorArgumento(f"estrato no válido: '{estrato}'", ESTRATOS)
            mascara &= self._estrato_norm == buscado
            filtros["estrato"] = ESTRATOS[self._orden_estrato[buscado]]

        subconjunto = d[mascara]

        # La colonia se aplica al final, sobre lo que dejaron los demás filtros.
        if _dado(colonia):
            buscada = normalizar(colonia)
            con_colonia = subconjunto[subconjunto["colonia_norm"] == buscada]
            if con_colonia.empty:
                contienen = subconjunto["colonia_norm"].str.contains(buscada, regex=False)
                parecidas = sorted(subconjunto.loc[contienen, "colonia"].unique())[:10]
                raise ErrorArgumento(
                    f"no hay establecimientos en la colonia '{colonia}' con los demás filtros. "
                    "valores_validos lista colonias (con esos filtros) que contienen ese texto.",
                    parecidas)
            subconjunto = con_colonia
            filtros["colonia"] = con_colonia["colonia"].iloc[0]

        return subconjunto, filtros

    @staticmethod
    def _resultado(filtros, **campos):
        return {"ok": True, "fuente": FUENTE, "filtros": filtros, **campos}

    # -- las cuatro herramientas (sección 6.3) -----------------------------
    @_seguro
    def buscar_actividades(self, texto=None):
        if not _dado(texto):
            raise ErrorArgumento("falta el argumento obligatorio 'texto'")
        palabras = _palabras(texto)
        actividades = []
        if palabras:
            d = self.datos
            mascara = pd.Series(True, index=d.index)
            for palabra in palabras:
                mascara &= d["actividad_norm"].str.contains(palabra, regex=False)
            conteo = (d[mascara].groupby(["codigo_act", "actividad"]).size()
                      .reset_index(name="establecimientos")
                      .sort_values(["establecimientos", "codigo_act"], ascending=[False, True])
                      .head(MAX_ACTIVIDADES))
            actividades = [
                {"codigo_act": fila.codigo_act, "actividad": fila.actividad,
                 "establecimientos": int(fila.establecimientos)}
                for fila in conteo.itertuples(index=False)
            ]
        return {"ok": True, "fuente": FUENTE, "texto": texto, "palabras": palabras,
                "actividades": actividades}

    @_seguro
    def contar(self, municipio=None, codigo_act=None, sector=None, estrato=None, colonia=None):
        subconjunto, filtros = self._filtrar(municipio, codigo_act, sector, estrato, colonia)
        return self._resultado(filtros, total=int(len(subconjunto)))

    @_seguro
    def ranking(self, por=None, top=5, municipio=None, codigo_act=None, sector=None,
                estrato=None, colonia=None):
        if _dado(colonia):
            raise ErrorArgumento(
                "ranking no acepta el filtro colonia. Para agrupar por colonia usa por='colonia'; "
                "para una colonia concreta usa contar o listar.")
        if not _dado(por):
            raise ErrorArgumento("falta el argumento obligatorio 'por'", POR_VALIDOS)
        columna = normalizar(por)
        if columna not in POR_VALIDOS:
            raise ErrorArgumento(f"'por' no válido: '{por}'", POR_VALIDOS)
        top = _entero_en_rango(top, 5, 1, MAX_TOP, "top")

        subconjunto, filtros = self._filtrar(municipio, codigo_act, sector, estrato)
        conteo = (subconjunto.groupby(columna).size().reset_index(name="total")
                  .sort_values(["total", columna], ascending=[False, True])
                  .head(top))
        filas = []
        for valor, total in zip(conteo[columna], conteo["total"]):
            fila = {"valor": valor, "total": int(total)}
            if columna == "codigo_act":
                fila["actividad"] = self._actividad_de.get(valor, "")
            if columna == "sector":
                fila["nombre_sector"] = self.sectores.get(valor, "")
            filas.append(fila)
        return self._resultado(filtros, por=columna, total_filtrado=int(len(subconjunto)),
                               filas=filas)

    @_seguro
    def listar(self, limite=10, municipio=None, codigo_act=None, sector=None, estrato=None,
               colonia=None):
        if not any(_dado(v) for v in (municipio, codigo_act, sector, estrato, colonia)):
            raise ErrorArgumento("listar exige al menos un filtro", FILTROS)
        limite = _entero_en_rango(limite, 10, 1, MAX_LIMITE, "limite")

        subconjunto, filtros = self._filtrar(municipio, codigo_act, sector, estrato, colonia)
        orden = self._estrato_norm.loc[subconjunto.index].map(self._orden_estrato).fillna(-1)
        elegidos = (subconjunto.assign(_orden=orden)
                    .sort_values(["_orden", "nombre"], ascending=[False, True])
                    .head(limite))
        establecimientos = [
            {"id": f.id, "nombre": f.nombre, "actividad": f.actividad, "estrato": f.estrato,
             "colonia": f.colonia, "municipio": f.municipio}
            for f in elegidos.itertuples(index=False)
        ]
        return self._resultado(filtros, total=int(len(subconjunto)),
                               mostrados=len(establecimientos), establecimientos=establecimientos)


# ---------------------------------------------------------------- declaraciones (6.4)

def _propiedades_filtros(incluir_colonia=True):
    propiedades = {
        "municipio": {"type": "string", "description":
                      "'Tampico' o 'Ciudad Madero'. Omítelo para incluir ambos municipios."},
        "codigo_act": {"type": "string", "description":
                       "Uno o varios códigos SCIAN separados por coma ('464111,464112'). Cada "
                       "código funciona como PREFIJO: '7225' incluye todas las clases que empiezan "
                       "con 7225. Sólo dígitos, de 2 a 6. Consigue los códigos con "
                       "buscar_actividades y pon TODAS las clases del giro en un solo codigo_act."},
        "sector": {"type": "string", "description":
                   "Sector SCIAN exacto: dos dígitos ('46' comercio al por menor, '72' alojamiento "
                   "y alimentos) o '31-33' (manufacturas) y '48-49' (transportes)."},
        "estrato": {"type": "string", "description":
                    "Rango de personal ocupado. Uno de: " + "; ".join(f"'{e}'" for e in ESTRATOS)
                    + ". El DENUE no tiene el número exacto de empleados."},
    }
    if incluir_colonia:
        propiedades["colonia"] = {"type": "string", "description":
                                  "Nombre de la colonia como aparece en el DENUE (por ejemplo "
                                  "'ZONA CENTRO'). Coincidencia exacta sin importar mayúsculas ni "
                                  "acentos. Si no existe, el error trae en valores_validos colonias "
                                  "que contienen el texto: elige de ahí, no adivines."}
    return propiedades


DECLARACIONES = [
    {
        "name": "buscar_actividades",
        "description":
            "Busca clases de actividad SCIAN cuyo nombre contiene TODAS las palabras del texto "
            "(palabras de 3 letras o más; tolera plurales sencillos). Devuelve hasta 15 clases "
            "{codigo_act, actividad, establecimientos} de ambos municipios, de más a menos "
            "establecimientos. Úsala SIEMPRE antes de contar un giro para conocer sus códigos. "
            "Si no hay coincidencias devuelve una lista vacía: prueba sinónimos o una palabra más "
            "general (por ejemplo 'tacos' en lugar de 'taquerías').",
        "parameters": {"type": "object", "properties": {
            "texto": {"type": "string", "description":
                      "Una o dos palabras del giro, en español: 'farmacia', 'tacos', 'belleza'."}},
            "required": ["texto"]},
    },
    {
        "name": "contar",
        "description":
            "Cuenta establecimientos que cumplen TODOS los filtros dados (y lógico). Sin filtros "
            "cuenta todo el conjunto de Tampico y Ciudad Madero. Para un total de varias clases, "
            "pásalas juntas en codigo_act en lugar de sumar tú.",
        "parameters": {"type": "object", "properties": _propiedades_filtros()},
    },
    {
        "name": "ranking",
        "description":
            "Agrupa los establecimientos que cumplen los filtros y devuelve los grupos con más "
            "establecimientos, de mayor a menor: filas {valor, total}, más 'actividad' si por es "
            "codigo_act y 'nombre_sector' si por es sector; también total_filtrado. Úsala para "
            "comparar municipios, encontrar las colonias con más negocios de un giro, etc. No "
            "acepta el filtro colonia.",
        "parameters": {"type": "object", "properties": {
            "por": {"type": "string", "enum": POR_VALIDOS,
                    "description": "Columna por la que se agrupa."},
            "top": {"type": "integer",
                    "description": "Cuántos grupos devolver, de 1 a 20 (por omisión 5)."},
            **_propiedades_filtros(incluir_colonia=False)},
            "required": ["por"]},
    },
    {
        "name": "listar",
        "description":
            "Lista establecimientos concretos que cumplen los filtros (exige al menos uno): "
            "{id, nombre, actividad, estrato, colonia, municipio}, ordenados del estrato más "
            "grande al más chico y luego por nombre. Devuelve también total y mostrados. Úsala "
            "para preguntas como '¿qué empresas grandes hay?' o 'dame ejemplos de...'.",
        "parameters": {"type": "object", "properties": {
            "limite": {"type": "integer",
                       "description": "Cuántos establecimientos mostrar, de 1 a 20 (por omisión 10)."},
            **_propiedades_filtros()}},
    },
]
