"""Genera un archivo .ics por categoría (y uno con todas) a partir de data/torneo.json.

Uso: python3 tools/generar_calendarios.py
"""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

RAIZ = Path(__file__).resolve().parent.parent
ZONA = ZoneInfo("America/Santiago")
DURACION = timedelta(hours=1)
LUGAR = "Stadio Italiano, Las Condes, Santiago"
DOMINIO = "futbolitostadioitaliano.cl"


def esc(texto):
    return str(texto).replace("\\", "\\\\").replace(";", "\;").replace(",", "\\,").replace("\n", "\\n")


def plegar(linea):
    datos = linea.encode("utf-8")
    if len(datos) <= 75:
        return linea
    partes, actual = [], b""
    for ch in linea:
        b = ch.encode("utf-8")
        limite = 75 if not partes else 74
        if len(actual) + len(b) > limite:
            partes.append(actual.decode("utf-8"))
            actual = b""
        actual += b
    partes.append(actual.decode("utf-8"))
    return "\r\n ".join(partes)


def utc(dt):
    return dt.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def eventos(cat, ahora, por_confirmar=False):
    for i, fecha in enumerate(cat["fechas"]):
        for j, p in enumerate(fecha["partidos"]):
            local = p["local"] or "Por definir"
            visita = p["visita"] or "Por definir"
            jugado = isinstance(p.get("gl"), int) and isinstance(p.get("gv"), int)
            marcador = f" {p['gl']}-{p['gv']} " if jugado else " vs "
            titulo = f"{local}{marcador}{visita} · {cat['nombre']}"
            tentativo = por_confirmar and not jugado
            if tentativo:
                titulo = "[Por confirmar] " + titulo
            inicio = datetime.fromisoformat(f"{fecha['dia']}T{p['hora']}").replace(tzinfo=ZONA)
            desc = f"{fecha['nombre']} ({fecha['fase']}) · Cancha {p['cancha']}\nhttps://{DOMINIO}/#{cat['id']}"
            yield [
                "BEGIN:VEVENT",
                f"UID:{cat['id']}-{i}-{j}@{DOMINIO}",
                f"DTSTAMP:{ahora}",
                f"DTSTART:{utc(inicio)}",
                f"DTEND:{utc(inicio + DURACION)}",
                f"SUMMARY:{esc(titulo)}",
                f"STATUS:{'TENTATIVE' if tentativo else 'CONFIRMED'}",
                f"LOCATION:{esc(LUGAR + ' · Cancha ' + str(p['cancha']))}",
                f"DESCRIPTION:{esc(desc)}",
                "END:VEVENT",
            ]


def calendario(nombre, categorias, ahora, por_confirmar=False):
    lineas = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        f"PRODID:-//{DOMINIO}//Futbolito Stadio Italiano//ES",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{esc(nombre)}",
        "X-WR-TIMEZONE:America/Santiago",
        "REFRESH-INTERVAL;VALUE=DURATION:PT6H",
        "X-PUBLISHED-TTL:PT6H",
    ]
    for cat in categorias:
        for ev in eventos(cat, ahora, por_confirmar):
            lineas += ev
    lineas.append("END:VCALENDAR")
    return "\r\n".join(plegar(l) for l in lineas) + "\r\n"


def main():
    datos = json.loads((RAIZ / "data" / "torneo.json").read_text(encoding="utf-8"))
    # Marca estable: los archivos solo cambian cuando cambian los datos.
    ahora = datos["actualizado"].replace("-", "") + "T000000Z"
    salida = RAIZ / "cal"
    salida.mkdir(exist_ok=True)
    cats = datos["categorias"]
    pc = bool(datos.get("aviso"))
    for cat in cats:
        (salida / f"{cat['id']}.ics").write_bytes(calendario(f"Futbolito Stadio Italiano · {cat['nombre']}", [cat], ahora, pc).encode("utf-8"))
    (salida / "todas.ics").write_bytes(calendario("Futbolito Stadio Italiano · Todas las categorías", cats, ahora, pc).encode("utf-8"))
    print("Calendarios generados:", ", ".join(sorted(p.name for p in salida.glob("*.ics"))))


if __name__ == "__main__":
    main()
