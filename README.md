# Futbolito Stadio Italiano 2026

Sitio web del Futbolito de Stadio Italiano. Muestra el fixture, los resultados, la tabla de posiciones, los goleadores y los sancionados de las cuatro categorías: Junior, Senior-Super, Dorados y Femenino.

Es un sitio estático publicado con GitHub Pages. No necesita instalar nada.

## Cómo se actualizan los datos

**La fuente es la planilla Excel del Drive.** Los organizadores la editan como siempre y la web se actualiza sola:

1. Cada 15 minutos, el proceso [Actualizar desde Drive](.github/workflows/actualizar-desde-drive.yml) descarga la planilla. Debe seguir compartida como «Cualquier persona con el enlace puede ver».
2. `tools/importar_planilla.py` lee el fixture, los resultados, los goleadores y los sancionados de cada categoría y regenera `data/torneo.json`.
3. Si hubo cambios, se regeneran los calendarios y se publica. La web queda al día en uno o dos minutos más.

Para actualizar al instante (por ejemplo, justo después de cargar una fecha): en GitHub, **Actions → Actualizar desde Drive → Run workflow**. GitHub a veces atrasa los procesos programados unos minutos.

**Si la planilla tiene un error,** la web no se toca y sigue mostrando la última versión buena. Se abre un aviso en la pestaña **Issues** explicando qué fila revisar, y se cierra solo cuando la planilla vuelve a leerse bien. Errores típicos:

- Un equipo que no se puede reconocer. Los errores de tipeo se corrigen solos («Lazzio», «Tanquerai», «Cosa Nostra», «Panteras», «Inter FC», «Escuola»…): el importador busca una palabra propia de un solo equipo o un nombre muy parecido, y deja la lista de correcciones en el resumen de cada ejecución en Actions. Solo frena cuando el nombre no se parece a ningún equipo de esa categoría o calza igual con dos. Para enseñarle una variante nueva, se suma en `alias` dentro de `CATEGORIAS` en `tools/importar_planilla.py`.
- Le cambiaron el nombre a una hoja, o el título de una fecha quedó sin día.
- Cambiaron el archivo por otro nuevo en el Drive. Para reemplazarlo hay que usar **Administrar versiones → Subir nueva versión**, así el enlace se mantiene. Si el enlace cambia, se actualiza `DRIVE_ID` en el workflow.

**Qué lee de la planilla:**

- **Fixture:** cada bloque con título «FECHA 1 SABADO 28 NOVIEMBRE» y encabezado HORARIO / CANCHA. Los goles van en las celdas del «-» a cada lado del V/S. Si solo hay un marcador escrito, el partido queda como pendiente.
- **Goleadores:** jugador, equipo y TOTAL. Si TOTAL está vacío, suma las fechas. Las filas con TOTAL en error (#REF!) se omiten.
- **Sancionados:** jugadores con «FECHAS POR CUMPLIR» mayor a 0, con su descripción.
- **Posiciones:** no se leen de la planilla. La web las calcula con los resultados: 3 puntos por victoria y 1 por empate; desempata por diferencia de gol y luego goles a favor.

No conviene editar `data/torneo.json` a mano: el próximo ciclo lo reemplaza con lo que diga la planilla.

Para probar el importador en tu computador:

```sh
pip install --require-hashes -r tools/requirements.txt
python3 tools/importar_planilla.py ruta/a/planilla.xlsx
```

## Aviso «Fechas por confirmar»

Si el campeonato se aplaza, se puede marcar todo el calendario como por confirmar:

```sh
python3 tools/aviso.py activar            # texto por defecto
python3 tools/aviso.py activar "Otro texto para el aviso"
python3 tools/aviso.py quitar
```

Mientras está activo, la web muestra el aviso arriba, tacha el día de cada fecha sin jugar con la etiqueta «Por confirmar» y oculta el botón «Agendar» de cada partido. En los calendarios, los partidos salen como tentativos y con «[Por confirmar]» en el título.

**Se quita solo:** apenas la planilla del Drive trae días u horarios distintos, el siguiente ciclo de actualización saca el aviso. Si confirman las mismas fechas originales, hay que quitarlo a mano con `quitar`.

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

## Dominio y seguridad

El dominio futbolitostadioitaliano.cl está registrado en GoDaddy y su DNS lo administra Cloudflare, en la cuenta de tomas@austerra.org, con el plan gratuito. Cloudflare está delante de GitHub Pages y aplica:

- HTTPS obligatorio, con cifrado "Full" hacia GitHub.
- HSTS de seis meses, con subdominios y sin precarga.
- Una regla de transformación llamada "Cabeceras de seguridad" que agrega X-Frame-Options, Permissions-Policy, Content-Security-Policy y Referrer-Policy.
- La cabecera X-Content-Type-Options: nosniff.

El dominio no envía correo. Por eso tiene registros SPF y DMARC que rechazan cualquier correo que diga venir de él.

La página además trae su propia política de seguridad de contenido, para que siga protegida si alguien la abre desde la dirección de github.io.
