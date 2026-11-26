(function () {
  const DIAS = ["Domingo", "Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"];
  const MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"];
  let datos = null;

  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const jugado = (p) => Number.isInteger(p.gl) && Number.isInteger(p.gv);

  function fechaTexto(iso) {
    const [y, m, d] = iso.split("-").map(Number);
    const f = new Date(y, m - 1, d);
    return `${DIAS[f.getDay()]} ${d} de ${MESES[m - 1]}`;
  }

  function hoyISO() {
    const h = new Date();
    return `${h.getFullYear()}-${String(h.getMonth() + 1).padStart(2, "0")}-${String(h.getDate()).padStart(2, "0")}`;
  }

  function calcularPosiciones(cat) {
    const pts = datos.puntos;
    const t = {};
    cat.equipos.forEach((e) => (t[e] = { equipo: e, pj: 0, pg: 0, pe: 0, pp: 0, gf: 0, gc: 0 }));
    cat.fechas
      .filter((f) => f.fase === "Fase regular")
      .flatMap((f) => f.partidos)
      .filter((p) => jugado(p) && t[p.local] && t[p.visita])
      .forEach((p) => {
        const L = t[p.local], V = t[p.visita];
        L.pj++; V.pj++;
        L.gf += p.gl; L.gc += p.gv; V.gf += p.gv; V.gc += p.gl;
        if (p.gl > p.gv) { L.pg++; V.pp++; }
        else if (p.gl < p.gv) { V.pg++; L.pp++; }
        else { L.pe++; V.pe++; }
      });
    return Object.values(t)
      .map((r) => ({ ...r, dif: r.gf - r.gc, pts: r.pg * pts.victoria + r.pe * pts.empate + r.pp * pts.derrota }))
      .sort((a, b) => b.pts - a.pts || b.dif - a.dif || b.gf - a.gf || a.equipo.localeCompare(b.equipo));
  }

  function equipoHTML(nombre, clase) {
    return nombre ? `<span class="${clase}">${esc(nombre)}</span>` : `<span class="${clase} por-definir">Por definir</span>`;
  }

  function partidoHTML(p) {
    const marcador = jugado(p)
      ? `<span class="marcador">${p.gl} - ${p.gv}</span>`
      : `<span class="marcador pend">vs</span>`;
    return `<div class="partido">
      <div class="meta">${esc(p.hora)}<br>Cancha ${esc(p.cancha)}</div>
      ${equipoHTML(p.local, "local")}${marcador}${equipoHTML(p.visita, "visita")}
    </div>`;
  }

  function fechaHTML(f) {
    const libre = f.libre ? `<div class="libre">Libre: ${esc(f.libre)}</div>` : "";
    const tag = f.fase === "Playoffs" ? `<span class="tag">Playoffs</span>` : "";
    return `<div class="fecha">
      <div class="fecha-head"><strong>${esc(f.nombre)}</strong><span>${fechaTexto(f.dia)}</span>${tag}</div>
      ${f.partidos.map(partidoHTML).join("")}${libre}
    </div>`;
  }

  function render(catId) {
    const cat = datos.categorias.find((c) => c.id === catId) || datos.categorias[0];

    document.querySelectorAll("#categorias button").forEach((b) => b.setAttribute("aria-selected", String(b.dataset.id === cat.id)));

    const hoy = hoyISO();
    const proxima = cat.fechas.find((f) => f.dia >= hoy);
    document.getElementById("proximos-body").innerHTML = proxima
      ? fechaHTML(proxima)
      : `<p class="vacio">El campeonato de esta categoría ya terminó.</p>`;

    const filas = calcularPosiciones(cat).map((r, i) => `<tr>
      <td>${i + 1}</td><td class="eq">${esc(r.equipo)}</td><td>${r.pj}</td><td>${r.pg}</td><td>${r.pe}</td><td>${r.pp}</td>
      <td>${r.gf}</td><td>${r.gc}</td><td>${r.dif > 0 ? "+" : ""}${r.dif}</td><td class="pts">${r.pts}</td></tr>`).join("");
    document.getElementById("posiciones").innerHTML = `<thead><tr>
      <th>#</th><th class="eq">Equipo</th><th title="Partidos jugados">PJ</th><th title="Ganados">PG</th><th title="Empatados">PE</th>
      <th title="Perdidos">PP</th><th title="Goles a favor">GF</th><th title="Goles en contra">GC</th><th title="Diferencia de gol">DIF</th><th>PTS</th>
      </tr></thead><tbody>${filas}</tbody>`;

    const gol = [...(cat.goleadores || [])].filter((g) => g.goles > 0).sort((a, b) => b.goles - a.goles || a.jugador.localeCompare(b.jugador));
    document.getElementById("goleadores").innerHTML = gol.length
      ? `<div class="table-scroll"><table class="tabla"><thead><tr><th>#</th><th class="eq">Jugador</th><th class="eq">Equipo</th><th>Goles</th></tr></thead><tbody>
        ${gol.map((g, i) => `<tr><td>${i + 1}</td><td class="eq">${esc(g.jugador)}</td><td class="eq">${esc(g.equipo)}</td><td class="pts">${g.goles}</td></tr>`).join("")}
        </tbody></table></div>`
      : `<p class="vacio">Todavía no hay goles registrados.</p>`;

    document.getElementById("fixture").innerHTML = cat.fechas.map(fechaHTML).join("");

    const san = cat.sancionados || [];
    document.getElementById("sancionados").innerHTML = san.length
      ? `<div class="table-scroll"><table class="tabla"><thead><tr><th class="eq">Jugador</th><th class="eq">Equipo</th><th>Fechas por cumplir</th><th class="eq">Motivo</th></tr></thead><tbody>
        ${san.map((s) => `<tr><td class="eq">${esc(s.jugador)}</td><td class="eq">${esc(s.equipo)}</td><td>${esc(s.fechasPorCumplir)}</td><td class="eq">${esc(s.motivo)}</td></tr>`).join("")}
        </tbody></table></div>`
      : `<p class="vacio">No hay jugadores sancionados.</p>`;
  }

  function iniciar(json) {
    datos = json;
    document.getElementById("actualizado").textContent = `Actualizado al ${fechaTexto(datos.actualizado).toLowerCase()}`;
    const nav = document.getElementById("categorias");
    nav.innerHTML = datos.categorias.map((c) => `<button role="tab" data-id="${esc(c.id)}">${esc(c.nombre)}</button>`).join("");
    nav.addEventListener("click", (e) => {
      const b = e.target.closest("button");
      if (b) { history.replaceState(null, "", "#" + b.dataset.id); render(b.dataset.id); }
    });
    render(location.hash.slice(1));
  }

  fetch("data/torneo.json", { cache: "no-cache" })
    .then((r) => r.json())
    .then(iniciar)
    .catch(() => {
      document.querySelector("main").innerHTML = `<section class="card"><p class="vacio">No se pudieron cargar los datos del campeonato.</p></section>`;
    });
})();
