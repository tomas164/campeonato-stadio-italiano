"""Agrega ?v=<hash> a styles.css y app.js en index.html.

Cloudflare guarda CSS y JS por horas; con la versión en la URL, cada cambio
se descarga de inmediato y lo que no cambió sigue saliendo del caché.

Uso: python3 tools/versionar.py
"""
import hashlib
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
INDEX = RAIZ / "index.html"

html = INDEX.read_text(encoding="utf-8")
nuevo = html
for archivo in ("styles.css", "app.js"):
    v = hashlib.sha256((RAIZ / archivo).read_bytes()).hexdigest()[:10]
    nuevo = re.sub(rf'(["\']){re.escape(archivo)}(\?v=[0-9a-f]*)?\1', rf"\g<1>{archivo}?v={v}\g<1>", nuevo)
if nuevo != html:
    INDEX.write_bytes(nuevo.encode("utf-8"))
    print("index.html: versiones actualizadas.")
else:
    print("index.html: sin cambios.")
