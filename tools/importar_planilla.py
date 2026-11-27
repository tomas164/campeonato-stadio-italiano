"""Lee la planilla del campeonato (Excel del Drive) y regenera data/torneo.json.

Uso: python3 tools/importar_planilla.py RUTA_AL_XLSX

Si la planilla tiene algo que no se entiende (un equipo desconocido, una fecha
sin día, etc.) el script termina con error y NO toca data/torneo.json, así la
web sigue mostrando la última versión buena.
"""
import difflib
import hashlib
import json
import os
import re
import sys
import unicodedata
import warnings
from datetime import date, datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

import openpyxl

warnings.filterwarnings("ignore", module="openpyxl")

RAIZ = Path(__file__).resolve().parent.parent
SALIDA = RAIZ / "data" / "torneo.json"
ANIO = 2026

CATEGORIAS = [
    {
        "id": "junior", "nombre": "Junior",
        "hojas": {"fixture": "Fixture JUNIOR", "goleadores": "Goleadores JUNIOR", "sancionados": "Sancionados JUNIOR"},
        "equipos": ["Internazionale", "Lazio", "Napoli", "Vecchia", "Scuola Junior"],
        "alias": {"Internazionales": "Internazionale", "Inter": "Internazionale", "Scuola": "Scuola Junior"},
    },
    {
        "id": "senior", "nombre": "Senior-Super",
        "hojas": {"fixture": "Fixture SEN-SUPER", "goleadores": "Goleadores SENIOR", "sancionados": "Sancionados SENIOR"},
        "equipos": ["Tanqueray", "Inter F.C.", "Quaranta Milan", "Cagliari Senior", "Match Point",
                    "La Cossa Nostra", "Sampdoria", "Scuola Senior"],
        "alias": {"Inter": "Inter F.C.", "La Cosa Nostra": "La Cossa Nostra", "Cagliari": "Cagliari Senior",
                  "Scuola": "Scuola Senior", "Quaranta": "Quaranta Milan"},
    },
    {
        "id": "dorados", "nombre": "Dorados",
        "hojas": {"fixture": "Fixture DORADOS", "goleadores": "Goleadores DORADOS", "sancionados": "Sancionados DORADOS"},
        "equipos": ["Tanque Invecchiato", "Cagliari Dorados", "Acheronte", "Scuola Dorados"],
        "alias": {"Tanqueray Invecchiato": "Tanque Invecchiato", "Tanque": "Tanque Invecchiato",
                  "Cagliari": "Cagliari Dorados", "Scuola": "Scuola Dorados"},
    },
    {
        "id": "femenino", "nombre": "Femenino",
        "hojas": {"fixture": "Fixture FEMENINO", "goleadores": "Goleadores FEMENINO", "sancionados": "Sancionados FEMENINO"},
        "equipos": ["Pantere Bianche", "Pink Demon", "Ragazze di Fuoco", "Scuola Fem"],
        "alias": {"Pantere": "Pantere Bianche", "Ragazze": "Ragazze di Fuoco", "Scuola": "Scuola Fem",
                  "Scuola Femenino": "Scuola Fem"},
    },
]

MESES = {"ENERO": 1, "FEBRERO": 2, "MARZO": 3, "ABRIL": 4, "MAYO": 5, "JUNIO": 6, "JULIO": 7,
         "AGOSTO": 8, "SEPTIEMBRE": 9, "SETIEMBRE": 9, "OCTUBRE": 10, "NOVIEMBRE": 11, "DICIEMBRE": 12}
RE_TITULO = re.compile(r"^(FECHA|CUARTOS|CUERTOS|SEMI|FINAL)")
RE_DIA = re.compile(r"(\d{1,2})\s+(?:DE\s+)?(" + "|".join(MESES) + r")\b")
VACIOS = {"", ".", "-", "–", "—"}


class ErrorPlanilla(Exception):
    pass


def clave(texto):
    t = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode()
    t = re.sub(r"[^A-Za-z0-9 ]", "", t)
    return re.sub(r"\s+", " ", t).strip().upper()


def texto(v):
    if v is None:
        return ""
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    return re.sub(r"\s+", " ", str(v)).strip()


def numero(v):
    if isinstance(v, bool) or v is None:
        return None
    if isinstance(v, (int, float)):
        return int(v) if float(v).is_integer() and v >= 0 else None
    t = texto(v)
    return int(t) if t.isdigit() else None


GENERICAS = {"FC", "CF", "LA", "EL", "DE", "DI", "SENIOR", "JUNIOR", "DORADOS", "FEM", "FEMENINO", "SUPER"}


def parecido(a, b):
    return difflib.SequenceMatcher(None, a, b).ratio()


class Equipos:
    """Reconoce un equipo aunque venga mal escrito.

    Orden: nombre exacto o alias conocido → una palabra propia de un solo
    equipo (con tolerancia a errores de tipeo) → parecido del nombre completo.
    Si dos equipos calzan igual de bien, no adivina y avisa del error.
    """

    def __init__(self, cat, correcciones):
        self.cat = cat["nombre"]
        self.equipos = cat["equipos"]
        self.correcciones = correcciones
        self.mapa = {}
        for nombre, equipo in [(e, e) for e in self.equipos] + list(cat["alias"].items()):
            self.mapa[clave(nombre)] = equipo
            self.mapa[clave(nombre).replace(" ", "")] = equipo
        palabras = {e: {w for w in clave(e).split() if w not in GENERICAS and len(w) >= 4}
                    for e in self.equipos}
        for alias, e in cat["alias"].items():
            palabras[e] |= {w for w in clave(alias).split() if w not in GENERICAS and len(w) >= 4}
        repetidas = {w for e, ws in palabras.items() for w in ws
                     if any(w in otras for o, otras in palabras.items() if o != e)}
        self.propias = {e: ws - repetidas for e, ws in palabras.items()}

    def adivinar(self, k):
        candidatos = set()
        for w in k.split():
            if len(w) < 4 or w in GENERICAS:
                continue
            for e, propias in self.propias.items():
                if any(parecido(w, p) >= 0.8 for p in propias):
                    candidatos.add(e)
        if len(candidatos) == 1:
            return candidatos.pop()
        if len(candidatos) > 1:
            return None
        puntajes = sorted(((max(parecido(k, c) for c, e2 in self.mapa.items() if e2 == e), e)
                           for e in self.equipos), reverse=True)
        (p1, e1), (p2, _) = puntajes[0], puntajes[1]
        return e1 if p1 >= 0.75 and p1 - p2 >= 0.1 else None

    def __call__(self, valor, donde):
        t = texto(valor)
        if t in VACIOS:
            return None
        k = clave(t)
        if k in self.mapa or k.replace(" ", "") in self.mapa:
            return self.mapa.get(k) or self.mapa[k.replace(" ", "")]
        equipo = self.adivinar(k)
        if equipo:
            self.mapa[k] = equipo
            self.correcciones.append(f"{self.cat}: «{t}» → {equipo} (primera vez en {donde})")
            return equipo
        raise ErrorPlanilla(f"{donde}: no reconozco el equipo «{t}» en {self.cat}. "
                            f"Equipos válidos: {', '.join(self.equipos)}.")


def nombre_fecha(titulo):
    t = clave(titulo)
    if t.startswith("FECHA"):
        m = re.match(r"FECHA (\d+)", t)
        if m:
            return f"Fecha {int(m.group(1))}", "Fase regular"
        if "RECUP" in t:
            return "Fecha recuperativa", "Fase regular"
        raise ErrorPlanilla(f"No entiendo el título de fecha «{titulo}».")
    if t.startswith(("CUARTOS", "CUERTOS")):
        if " IDA" in t:
            return "Cuartos de final (ida)", "Playoffs"
        if "VUELTA" in t or "VUETA" in t:
            return "Cuartos de final (vuelta)", "Playoffs"
        return "Cuartos de final", "Playoffs"
    if t.startswith("SEMI"):
        return "Semifinal", "Playoffs"
    return "Final", "Playoffs"


def dia_de(titulo, donde):
    m = RE_DIA.search(clave(titulo))
    if not m:
        raise ErrorPlanilla(f"{donde}: no encuentro el día en el título «{titulo}».")
    mes = MESES[m.group(2)]
    anio = ANIO + 1 if mes < 7 else ANIO
    try:
        return date(anio, mes, int(m.group(1))).isoformat()
    except ValueError:
        raise ErrorPlanilla(f"{donde}: el día de «{titulo}» no existe.")


def hora_de(v):
    if isinstance(v, time):
        return v.strftime("%H:%M")
    if isinstance(v, datetime):
        return v.strftime("%H:%M")
    if isinstance(v, float) and 0 < v < 1:  # Excel guarda horas como fracción del día
        minutos = round(v * 24 * 60)
        return f"{minutos // 60:02d}:{minutos % 60:02d}"
    m = re.match(r"^(\d{1,2})[:.](\d{2})", texto(v))
    return f"{int(m.group(1)):02d}:{m.group(2)}" if m else None


def leer_fixture(ws, cat, equipo, avisos):
    """Cada bloque tiene un título («FECHA 1 SABADO 28 NOVIEMBRE») y una fila
    de encabezado HORARIO | CANCHA | categoría. Las columnas siguientes son
    local, goles local, V/S, goles visita y visita."""
    fechas, actual, hora, base = [], None, None, None
    for fila in ws.iter_rows():
        celdas = [c for c in fila if texto(c.value)]
        for c in celdas:
            t = clave(c.value)
            if RE_TITULO.match(t) and RE_DIA.search(t):
                nombre, fase = nombre_fecha(c.value)
                actual = {"nombre": nombre, "fase": fase,
                          "dia": dia_de(c.value, f"{ws.title}!{c.coordinate}"), "partidos": []}
                fechas.append(actual)
                hora = None
                break
        encabezado = next((c for c in celdas if clave(c.value) == "HORARIO"), None)
        if encabezado is not None:
            base = encabezado.column
            continue
        if actual is None or base is None:
            continue
        f = fila[0].row
        val = lambda d: ws.cell(row=f, column=base + d).value
        donde = f"{ws.title}, fila {f}"
        h = hora_de(val(0))
        if h:
            hora = h
        cancha = numero(val(1))
        textos = [texto(val(2)), texto(val(6))]
        libres = [re.match(r"^LIBRE\b\s*:?\s*(.*)$", x, re.I) for x in textos]
        if any(libres):
            m = libres[0] or libres[1]
            otro = texto(m.group(1)) or (textos[1] if libres[0] else textos[0])
            if otro not in VACIOS:
                actual["libre"] = equipo(otro, donde)
            continue
        if cancha is None:
            continue
        local, visita = equipo(val(2), donde), equipo(val(6), donde)
        if actual["fase"] == "Fase regular" and (local is None) != (visita is None):
            avisos.append(f"{donde}: partido con un solo equipo, lo omito.")
            continue
        if not (local or visita) and clave(val(4)) not in ("VS", "V S"):
            continue  # fila vacía sin V/S: no es un partido
        gl, gv = numero(val(3)), numero(val(5))
        if (gl is None) != (gv is None):
            avisos.append(f"{donde}: hay un solo marcador escrito ({local} vs {visita}); queda como pendiente.")
            gl = gv = None
        if hora is None:
            raise ErrorPlanilla(f"{donde}: partido sin horario.")
        actual["partidos"].append({"hora": hora, "cancha": cancha, "local": local, "visita": visita,
                                   "gl": gl, "gv": gv})
    # La planilla trae filas vacías de sobra. Los partidos con equipos se
    # conservan siempre; los cupos «por definir» solo en playoffs o en fechas
    # aún sin programar, y hasta completar el máximo posible (equipos / 2).
    maximo = len(cat["equipos"]) // 2
    for fe in fechas:
        llenos = [p for p in fe["partidos"] if p["local"] or p["visita"]]
        cupos = maximo - len(llenos) if (fe["fase"] == "Playoffs" or not llenos) else 0
        usados, lista = set(), []
        for p in fe["partidos"]:
            lugar = (p["hora"], p["cancha"])
            if p["local"] or p["visita"]:
                lista.append(p)
            elif cupos > 0 and lugar not in usados:  # sin cupos repetidos misma hora y cancha
                cupos -= 1
                lista.append(p)
            usados.add(lugar)
        fe["partidos"] = lista
    for fe in fechas:
        if "libre" in fe:  # mantener el orden de claves del JSON original
            fe["partidos"] = fe.pop("partidos")
    if not fechas:
        raise ErrorPlanilla(f"{ws.title}: no encontré ninguna fecha.")
    return fechas


def encabezados(ws):
    for fila in ws.iter_rows():
        nombres = {clave(c.value): c.column for c in fila if texto(c.value)}
        if "JUGADOR" in nombres:
            return fila[0].row, nombres
    raise ErrorPlanilla(f"{ws.title}: no encuentro la columna JUGADOR.")


def leer_goleadores(ws, equipo, avisos):
    fila0, cols = encabezados(ws)
    cj, ce = cols["JUGADOR"], cols.get("EQUIPO")
    ct = cols.get("TOTAL")
    parciales = [c for k, c in cols.items() if c not in (cj, ce, ct)]
    lista = []
    for f in range(fila0 + 1, ws.max_row + 1):
        jugador = texto(ws.cell(f, cj).value)
        if jugador in VACIOS or jugador.startswith("#"):
            continue
        total = ws.cell(f, ct).value if ct else None
        if texto(total).startswith("#"):
            avisos.append(f"{ws.title}, fila {f}: el TOTAL de {jugador} tiene un error ({texto(total)}), lo omito.")
            continue
        goles = numero(total)
        if goles is None:
            goles = sum(numero(ws.cell(f, c).value) or 0 for c in parciales)
        if goles <= 0:
            continue
        lista.append({"jugador": jugador,
                      "equipo": equipo(ws.cell(f, ce).value, f"{ws.title}, fila {f}") if ce else None,
                      "goles": goles})
    lista.sort(key=lambda g: (-g["goles"], g["jugador"]))
    return lista


def leer_sancionados(ws, equipo):
    fila0, cols = encabezados(ws)
    cj, ce = cols["JUGADOR"], cols.get("EQUIPO")
    cp = cols.get("FECHAS POR CUMPLIR")
    cd = cols.get("DESCRIPCION")
    lista = []
    for f in range(fila0 + 1, ws.max_row + 1):
        jugador = texto(ws.cell(f, cj).value)
        if jugador in VACIOS or jugador.startswith("#"):
            continue
        pendientes = numero(ws.cell(f, cp).value) if cp else None
        if not pendientes:
            continue
        motivo = texto(ws.cell(f, cd).value) if cd else ""
        lista.append({"jugador": jugador,
                      "equipo": equipo(ws.cell(f, ce).value, f"{ws.title}, fila {f}") if ce else None,
                      "fechasPorCumplir": pendientes,
                      "motivo": "" if motivo in VACIOS else motivo})
    return lista


def importar(ruta):
    try:
        wb = openpyxl.load_workbook(ruta, data_only=True, read_only=False)
    except Exception as e:
        raise ErrorPlanilla(f"No pude abrir la planilla: {e}")
    avisos, correcciones, categorias = [], [], []
    for cat in CATEGORIAS:
        faltan = [h for h in cat["hojas"].values() if h not in wb.sheetnames]
        if faltan:
            raise ErrorPlanilla(f"Falta la hoja {', '.join(faltan)} (¿le cambiaron el nombre?).")
        equipo = Equipos(cat, correcciones)
        categorias.append({
            "id": cat["id"], "nombre": cat["nombre"], "equipos": cat["equipos"],
            "fechas": leer_fixture(wb[cat["hojas"]["fixture"]], cat, equipo, avisos),
            "goleadores": leer_goleadores(wb[cat["hojas"]["goleadores"]], equipo, avisos),
            "sancionados": leer_sancionados(wb[cat["hojas"]["sancionados"]], equipo),
        })
    return categorias, avisos, correcciones


def resumen(avisos, correcciones):
    """Deja las correcciones y avisos a la vista en el resumen de GitHub Actions."""
    ruta = os.environ.get("GITHUB_STEP_SUMMARY")
    if not ruta or not (avisos or correcciones):
        return
    lineas = []
    if correcciones:
        lineas += ["### Nombres de equipo corregidos automáticamente", ""] + [f"- {c}" for c in correcciones] + [""]
    if avisos:
        lineas += ["### Avisos", ""] + [f"- {a}" for a in avisos] + [""]
    with open(ruta, "a", encoding="utf-8") as f:
        f.write("\n".join(lineas) + "\n")


def huella_fechas(categorias):
    """Resume días y horarios de todo el fixture. Sirve para saber si la
    planilla ya trae un calendario distinto al que tenía el aviso."""
    base = [(c["id"], f["nombre"], f["dia"], [p["hora"] for p in f["partidos"]])
            for c in categorias for f in c["fechas"]]
    return hashlib.sha256(json.dumps(base, ensure_ascii=False).encode()).hexdigest()[:16]


def main():
    if len(sys.argv) != 2:
        sys.exit("Uso: python3 tools/importar_planilla.py RUTA_AL_XLSX")
    try:
        categorias, avisos, correcciones = importar(sys.argv[1])
    except ErrorPlanilla as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    for c in correcciones:
        print(f"Corregido: {c}")
    for a in avisos:
        print(f"Aviso: {a}")
    resumen(avisos, correcciones)

    anterior = json.loads(SALIDA.read_text(encoding="utf-8")) if SALIDA.exists() else {}
    if anterior.get("categorias") == categorias:
        print("La planilla no tiene cambios.")
        return
    hoy = datetime.now(ZoneInfo("America/Santiago")).date().isoformat()
    datos = {"torneo": "Futbolito Stadio Italiano 2026", "actualizado": hoy,
             "puntos": anterior.get("puntos", {"victoria": 3, "empate": 1, "derrota": 0})}
    # El aviso «fechas por confirmar» se mantiene mientras la planilla siga
    # con el mismo calendario; apenas cambian días u horarios, se quita solo.
    aviso = anterior.get("aviso")
    if aviso:
        if aviso.get("huella") == huella_fechas(categorias):
            datos["aviso"] = aviso
        else:
            print("Las fechas cambiaron en la planilla: se quita el aviso «por confirmar».")
    datos["categorias"] = categorias
    SALIDA.write_bytes((json.dumps(datos, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    print(f"data/torneo.json actualizado ({hoy}).")


if __name__ == "__main__":
    main()
