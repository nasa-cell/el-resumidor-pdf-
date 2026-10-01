// Campana del menú, en las páginas que no son «Crear resumen». Aparece solo si hay resúmenes en la
// lista (creándose o terminados en la última hora). El anillo se llena con el avance de todos; cuando
// termina uno suena, muestra cuántos hay para bajar y un aviso chico que se va solo. Al tocarla se
// abre la lista con el botón de descarga de cada uno y la escoba para limpiar los terminados.
(() => {
  const nav = document.querySelector(".nav");
  if (!nav || !ListaResumenes.leer().length) return;

  const ICONO = {
    campana: '<svg class="campana-icono" viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M6 16.5V11a6 6 0 1 1 12 0v5.5l1.5 2H4.5l1.5-2Z" stroke="currentColor" stroke-width="1.9" stroke-linejoin="round"/><path d="M10 20.5a2.2 2.2 0 0 0 4 0" stroke="currentColor" stroke-width="1.9" stroke-linecap="round"/></svg>',
    bajar: '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M12 4v11m0 0-4.5-4.5M12 15l4.5-4.5" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/><path d="M5 19.5h14" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"/></svg>',
    hecho: '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="m5.5 12.5 4 4 9-9.5" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    escoba: '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M20 3.5 13 10.5" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><path d="M11.4 9.4l3.2 3.2-1.2 1.2c-1 1-1.3 2.8-1.5 4.7l-.2 1.5c-2.8-.3-5.6-1.6-7.7-3.8l.5-.6c1.4.2 2.8-.3 3.7-1.2 1-1 .8-2.6 1.8-3.6l1.4-1.4Z" stroke="currentColor" stroke-width="1.9" stroke-linejoin="round"/><path d="M7.6 17.9l1.7-1.8M10 19.4l1.3-1.7" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>',
  };
  const VUELTA = 113;   // largo del anillo (2·π·18)

  const campana = document.createElement("button");
  campana.type = "button";
  campana.className = "campana";
  campana.setAttribute("aria-expanded", "false");
  campana.setAttribute("aria-controls", "campana-panel");
  campana.innerHTML = `<svg class="campana-anillo" viewBox="0 0 40 40" aria-hidden="true">
      <circle cx="20" cy="20" r="18" class="campana-anillo-fondo"/>
      <circle cx="20" cy="20" r="18" class="campana-anillo-avance" stroke-dasharray="${VUELTA}" stroke-dashoffset="${VUELTA}" transform="rotate(-90 20 20)"/>
    </svg>${ICONO.campana}<span class="campana-globo" hidden></span>`;
  (nav.querySelector(".enlaces") || nav).appendChild(campana);

  const panel = document.createElement("div");
  panel.className = "campana-panel";
  panel.id = "campana-panel";
  panel.hidden = true;
  panel.innerHTML = `<p class="campana-titulo">Tus resúmenes <span class="campana-cuenta"></span></p>
    <div class="campana-lista"></div>
    <div class="campana-pie"><a href="/crear">Ver todos</a>
      <button type="button" class="escoba campana-escoba">${ICONO.escoba}Limpiar</button></div>`;
  nav.appendChild(panel);

  const aviso = document.createElement("div");
  aviso.className = "campana-aviso";
  aviso.setAttribute("role", "status");
  aviso.hidden = true;
  document.body.appendChild(aviso);

  let estados = {};      // id -> último estado del servidor
  let avisados = null;   // ids que ya estaban listos (para sonar solo con los nuevos)
  let relojAviso = null;

  function abrir(abierto) {
    panel.hidden = !abierto;
    campana.setAttribute("aria-expanded", String(abierto));
  }
  campana.addEventListener("click", () => abrir(panel.hidden));
  document.addEventListener("click", ev => {
    if (!panel.hidden && !panel.contains(ev.target) && !campana.contains(ev.target)) abrir(false);
  });
  document.addEventListener("keydown", ev => { if (ev.key === "Escape" && !panel.hidden) { abrir(false); campana.focus(); } });

  panel.querySelector(".campana-escoba").addEventListener("click", () => {
    const lista = ListaResumenes.leer();
    ListaResumenes.quitar(lista.filter(t => estados[t.id]?.fase !== "procesando").map(t => t.id));
    pintar();
  });

  function pintar() {
    const lista = ListaResumenes.leer();
    if (!lista.length) {
      campana.remove(); panel.remove();
      return;
    }
    const fase = t => estados[t.id]?.fase || (t.listo ? "listo" : "procesando");
    const listos = lista.filter(t => fase(t) === "listo");
    const sinBajar = listos.filter(t => !t.bajado).length;
    const promedio = lista.reduce((suma, t) => suma + (fase(t) === "procesando" ? estados[t.id]?.porcentaje || 0 : 100), 0) / lista.length;
    campana.querySelector(".campana-anillo-avance").setAttribute("stroke-dashoffset", VUELTA * (1 - promedio / 100));
    const globo = campana.querySelector(".campana-globo");
    globo.hidden = !sinBajar;
    globo.textContent = sinBajar;
    const creando = lista.length - listos.length;
    campana.setAttribute("aria-label", `Tus resúmenes: ${listos.length} de ${lista.length} listos`
      + (sinBajar ? `, ${sinBajar} para descargar` : "") + (creando ? `, ${creando} creándose` : ""));

    panel.querySelector(".campana-cuenta").textContent = `${listos.length} de ${lista.length} listos`;
    panel.querySelector(".campana-escoba").disabled = lista.every(t => fase(t) === "procesando");
    const caja = panel.querySelector(".campana-lista");
    caja.innerHTML = "";
    lista.forEach(t => {
      const e = estados[t.id] || {};
      const listo = fase(t) === "listo";
      const fila = document.createElement("div");
      fila.className = "campana-item" + (listo ? " listo" : "") + (t.bajado ? " bajado" : "")
        + (fase(t) === "error" ? " error" : "");
      const porcentaje = listo ? 100 : e.porcentaje || 0;
      fila.innerHTML = `<span class="campana-nombre"></span>
        <span class="campana-mini"><span style="width:${porcentaje}%"></span></span>
        <span class="campana-pct">${fase(t) === "error" ? "Error" : listo ? "" : porcentaje + " %"}</span>
        <button type="button" class="pdf-bajar"${listo ? "" : " disabled"}>${t.bajado ? ICONO.hecho : ICONO.bajar}</button>`;
      fila.querySelector(".campana-nombre").textContent = t.nombre || "documento.pdf";
      fila.querySelector(".campana-nombre").title = t.nombre || "";
      const boton = fila.querySelector(".pdf-bajar");
      boton.setAttribute("aria-label", !listo ? `${t.nombre}: todavía se está creando`
        : t.bajado ? `Descargar ${t.nombre} otra vez` : `Descargar ${t.nombre}`);
      boton.addEventListener("click", async () => {
        boton.disabled = true;
        if (!await ListaResumenes.bajar(t.id)) {
          ListaResumenes.quitar([t.id]);
          avisar("Ese resumen ya no está en el servidor (pasa después de una hora).");
        }
        pintar();
      });
      caja.appendChild(fila);
    });

    // Suena solo con los que terminaron recién (no con los que ya estaban listos al abrir la página).
    const nuevos = listos.filter(t => avisados && !avisados.has(t.id));
    avisados = new Set(listos.map(t => t.id));
    if (nuevos.length) {
      campana.classList.remove("suena");
      void campana.offsetWidth;
      campana.classList.add("suena");
      avisar(nuevos.length === 1 ? `Terminó «${nuevos[0].nombre}». Toca la campana para bajarlo.`
        : `Terminaron ${nuevos.length} resúmenes. Toca la campana para bajarlos.`);
    }
  }

  function avisar(texto) {
    aviso.textContent = texto;
    aviso.hidden = false;
    clearTimeout(relojAviso);
    relojAviso = setTimeout(() => { aviso.hidden = true; }, 5000);
  }

  async function preguntar() {
    const lista = ListaResumenes.leer();
    if (!lista.length) return pintar();
    try {
      estados = await ListaResumenes.estados(lista.map(t => t.id));
    } catch {
      return setTimeout(preguntar, 3000);   // sin conexión: se vuelve a intentar
    }
    // Los terminados hace más de una hora ya no están en el servidor: se quitan de la lista.
    ListaResumenes.quitar(lista.filter(t => estados[t.id]?.perdido && t.listo).map(t => t.id));
    lista.forEach(t => { if (estados[t.id]?.fase === "listo" && !t.listo) ListaResumenes.cambiar(t.id, { listo: true }); });
    pintar();
    if (Object.values(estados).some(e => e.fase === "procesando")) setTimeout(preguntar, 1500);
  }
  pintar();
  preguntar();
})();
