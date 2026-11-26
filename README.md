# Futbolito Stadio Italiano 2026

Sitio web del Futbolito de Stadio Italiano. Muestra el fixture, los resultados, la tabla de posiciones, los goleadores y los sancionados de las cuatro categorías: Junior, Senior-Super, Dorados y Femenino.

Es un sitio estático publicado con GitHub Pages. No necesita instalar nada.

## Cómo actualizar los datos

Toda la información está en un solo archivo: `data/torneo.json`. Se puede editar directo desde GitHub con el ícono del lápiz y guardar con "Commit changes". El sitio se actualiza solo en uno o dos minutos.

**Cargar un resultado.** Buscar el partido y cambiar `gl` (goles del local) y `gv` (goles de la visita):

```json
{ "hora": "17:00", "cancha": 1, "local": "Tanqueray", "visita": "Inter F.C.", "gl": 2, "gv": 1 }
```

La tabla de posiciones se calcula sola con los partidos de fase regular. Da 3 puntos por victoria y 1 por empate, y desempata por diferencia de gol y luego goles a favor.

**Definir un cruce de playoffs.** Reemplazar `null` por el nombre del equipo en `local` y `visita`.

**Agregar goleadores.** En la lista `goleadores` de la categoría:

```json
"goleadores": [
  { "jugador": "Nombre Apellido", "equipo": "Sampdoria", "goles": 3 }
]
```

**Agregar sancionados.** En la lista `sancionados` de la categoría:

```json
"sancionados": [
  { "jugador": "Nombre Apellido", "equipo": "Lazio", "fechasPorCumplir": 1, "motivo": "Roja directa" }
]
```

Al terminar, actualizar también el campo `actualizado` con la fecha del día.

Los nombres de equipo en los partidos deben escribirse igual que en la lista `equipos` de la categoría, si no el partido no suma en la tabla.

## Ver el sitio en tu computador

```sh
python3 -m http.server 8000
```

Después abrir http://localhost:8000.

## Calendarios

La carpeta `cal` tiene un archivo de calendario por categoría y uno con todas. Los visitantes se suscriben desde el sitio con Google Calendar, iPhone u Outlook, y su calendario se actualiza solo.

Esos archivos se regeneran automáticamente con GitHub Actions cada vez que cambia `data/torneo.json`. Para generarlos a mano:

```sh
python3 tools/generar_calendarios.py
```
