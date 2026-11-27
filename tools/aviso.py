"""Activa o quita el aviso «Fechas por confirmar» en la web.

Uso:
  python3 tools/aviso.py activar ["texto opcional"]
  python3 tools/aviso.py quitar

Mientras está activo, la web muestra el aviso, marca cada fecha como «por
confirmar» y los calendarios marcan los partidos como tentativos. Se quita
solo cuando la planilla del Drive trae días u horarios distintos.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from importar_planilla import SALIDA, huella_fechas  # noqa: E402

TEXTO = ("El Futbolito se aplazó. Las fechas y horarios que ves son los originales "
         "y se actualizarán apenas la organización confirme el nuevo calendario.")

if len(sys.argv) < 2 or sys.argv[1] not in ("activar", "quitar"):
    sys.exit(__doc__)
datos = json.loads(SALIDA.read_text(encoding="utf-8"))
if sys.argv[1] == "activar":
    aviso = {"titulo": "Fechas por confirmar", "texto": sys.argv[2] if len(sys.argv) > 2 else TEXTO,
             "huella": huella_fechas(datos["categorias"])}
    nuevo = {k: v for k, v in datos.items() if k != "categorias"}
    nuevo["aviso"] = aviso
    nuevo["categorias"] = datos["categorias"]
    datos = nuevo
    print("Aviso activado.")
else:
    datos.pop("aviso", None)
    print("Aviso quitado.")
SALIDA.write_bytes((json.dumps(datos, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
