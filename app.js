(function () {
  const DIAS = ["Domingo", "Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"];
  const MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"];
  let datos = null;
  const porConfirmar = () => Boolean(datos && datos.aviso);

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

  const GCAL_ICON = `<svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true"><path fill="currentColor" d="M7 2v2H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6a2 2 0 0 0-2-2h-2V2h-2v2H9V2H7zm-2 7h14v11H5V9zm6 2v3H8v2h3v3h2v-3h3v-2h-3v-3h-2z"/></svg>`;

  function urlCalendario(catId) {
    const base = location.host + location.pathname.replace(/[^/]*$/, "");
    return `webcal://${base}cal/${catId}.ics`;
  }

  function linkGoogleEvento(cat, fecha, p) {
    const [h, m] = p.hora.split(":").map(Number);
    const ini = fecha.dia.replace(/-/g, "") + "T" + String(h).padStart(2, "0") + String(m).padStart(2, "0") + "00";
    const fin = fecha.dia.replace(/-/g, "") + "T" + String(h + 1).padStart(2, "0") + String(m).padStart(2, "0") + "00";
    const params = new URLSearchParams({
      action: "TEMPLATE",
      text: `${p.local || "Por definir"} vs ${p.visita || "Por definir"} · ${cat.nombre}`,
      dates: `${ini}/${fin}`,
      ctz: "America/Santiago",
      location: `Stadio Italiano, Las Condes, Santiago · Cancha ${p.cancha}`,
      details: `${fecha.nombre} (${fecha.fase}) · Cancha ${p.cancha}\n${location.origin}${location.pathname}#${cat.id}`,
    });
    return `https://calendar.google.com/calendar/render?${params}`;
  }

  function agendarHTML(cat) {
    const webcal = urlCalendario(cat.id);
    const google = "https://calendar.google.com/calendar/r?cid=" + encodeURIComponent(webcal);
    const https = webcal.replace(/^webcal:/, location.protocol);
    const txt = porConfirmar()
      ? `Las fechas están por confirmar. Si te suscribes ahora, tu calendario se corregirá solo cuando se publique el nuevo calendario de ${esc(cat.nombre)}.`
      : `Agrega todos los partidos de ${esc(cat.nombre)} a tu calendario. Se actualiza solo cuando cambian horarios o cruces.`;
    return `<p class="agendar-txt">${txt}</p>
      <div class="agendar-btns">
        <a class="btn btn-prim" href="${esc(google)}" target="_blank" rel="noopener">${GCAL_ICON} Google Calendar</a>
        <a class="btn" href="${esc(webcal)}">${GCAL_ICON} iPhone / Outlook</a>
        <a class="btn btn-link" href="${esc(https)}" download>Descargar .ics</a>
      </div>`;
  }

  function equipoHTML(nombre, clase) {
    return nombre ? `<span class="${clase}">${esc(nombre)}</span>` : `<span class="${clase} por-definir">Por definir</span>`;
  }

  function partidoHTML(p, cat, fecha) {
    const marcador = jugado(p)
      ? `<span class="marcador">${p.gl} - ${p.gv}</span>`
      : `<span class="marcador pend">vs</span>`;
    return `<div class="partido">
      <div class="meta">${esc(p.hora)} · Cancha ${esc(p.cancha)}${jugado(p) || porConfirmar() ? "" : `<br><a class="add-gcal" href="${esc(linkGoogleEvento(cat, fecha, p))}" target="_blank" rel="noopener" title="Agregar este partido a Google Calendar">${GCAL_ICON} Agendar</a>`}</div>
      ${equipoHTML(p.local, "local")}${marcador}${equipoHTML(p.visita, "visita")}
    </div>`;
  }

  function fechaHTML(f, cat) {
    const libre = f.libre ? `<div class="libre">Libre: ${esc(f.libre)}</div>` : "";
    const tag = f.fase === "Playoffs" ? `<span class="tag">Playoffs</span>` : "";
    const pc = porConfirmar() && !f.partidos.some(jugado);
    const dia = pc
      ? `<span class="dia-pc" title="Fecha original, por confirmar">${fechaTexto(f.dia)}</span><span class="tag tag-pc">Por confirmar</span>`
      : `<span>${fechaTexto(f.dia)}</span>`;
    return `<div class="fecha">
      <div class="fecha-head"><strong>${esc(f.nombre)}</strong>${dia}${tag}</div>
      ${f.partidos.map((p) => partidoHTML(p, cat, f)).join("")}${libre}
    </div>`;
  }

  function render(catId) {
    const cat = datos.categorias.find((c) => c.id === catId) || datos.categorias[0];

    document.querySelectorAll("#categorias button").forEach((b) => b.setAttribute("aria-selected", String(b.dataset.id === cat.id)));

    const hoy = hoyISO();
    const proxima = cat.fechas.find((f) => f.dia >= hoy);
    document.getElementById("proximos-body").innerHTML = proxima
      ? fechaHTML(proxima, cat)
      : `<p class="vacio">El campeonato de esta categoría ya terminó.</p>`;

    const filas = calcularPosiciones(cat).map((r, i) => `<tr class="${i === 0 && r.pts > 0 ? "primo" : ""}">
      <td class="pos">${i + 1}</td><td class="eq">${esc(r.equipo)}</td><td>${r.pj}</td><td>${r.pg}</td><td>${r.pe}</td><td>${r.pp}</td>
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

    document.getElementById("agendar").innerHTML = agendarHTML(cat);
    document.getElementById("fixture").innerHTML = cat.fechas.map((f) => fechaHTML(f, cat)).join("");

    const san = cat.sancionados || [];
    document.getElementById("sancionados").innerHTML = san.length
      ? `<div class="table-scroll"><table class="tabla"><thead><tr><th class="eq">Jugador</th><th class="eq">Equipo</th><th>Fechas por cumplir</th><th class="eq">Motivo</th></tr></thead><tbody>
        ${san.map((s) => `<tr><td class="eq">${esc(s.jugador)}</td><td class="eq">${esc(s.equipo)}</td><td>${esc(s.fechasPorCumplir)}</td><td class="eq">${esc(s.motivo)}</td></tr>`).join("")}
        </tbody></table></div>`
      : `<p class="vacio">No hay jugadores sancionados.</p>`;
  }

  function avisoHTML(a) {
    return `<div class="aviso">
      <svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true"><path fill="currentColor" d="M7 2v2H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6a2 2 0 0 0-2-2h-2V2h-2v2H9V2H7zM5 9h14v11H5V9zm6 2v5h2v-5h-2zm0 6v2h2v-2h-2z"/></svg>
      <div><strong>${esc(a.titulo || "Fechas por confirmar")}</strong><p>${esc(a.texto)}</p></div>
    </div>`;
  }

  function iniciar(json) {
    datos = json;
    if (datos.aviso) document.getElementById("aviso").innerHTML = avisoHTML(datos.aviso);
    document.getElementById("actualizado").textContent = `Actualizado al ${fechaTexto(datos.actualizado).toLowerCase()}`;
    const nav = document.getElementById("categorias");
    nav.innerHTML = datos.categorias.map((c) => `<button role="tab" data-id="${esc(c.id)}">${esc(c.nombre)}</button>`).join("");
    nav.addEventListener("click", (e) => {
      const b = e.target.closest("button");
      if (b) { history.replaceState(null, "", "#" + b.dataset.id); render(b.dataset.id); }
    });
    render(location.hash.slice(1));
  }

  // Las secciones y fotos entran con un movimiento suave al aparecer en pantalla.
  function revelar() {
    if (!("IntersectionObserver" in window) || matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    document.documentElement.classList.add("anim");
    const io = new IntersectionObserver((entradas) => {
      entradas.forEach((e) => {
        if (e.isIntersecting) { e.target.classList.add("visible"); io.unobserve(e.target); }
      });
    }, { rootMargin: "0px 0px -40px 0px" });
    document.querySelectorAll("main .card, .fotos .foto").forEach((el) => io.observe(el));
  }
  revelar();

  fetch("data/torneo.json", { cache: "no-cache" })
    .then((r) => r.json())
    .then(iniciar)
    .catch(() => {
      document.querySelector("main").innerHTML = `<section class="card visible"><p class="vacio">No se pudieron cargar los datos del campeonato.</p></section>`;
    });
})();
