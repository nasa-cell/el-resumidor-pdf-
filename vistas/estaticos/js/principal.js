// Lógica de la página: opciones, envío del PDF y resultado
const $ = id => document.getElementById(id);

document.querySelectorAll('input[name="color"]').forEach(r => r.addEventListener("change", () => {
  const punta = r.nextElementSibling;   // el color sale del CSS, no se repite aquí
  document.documentElement.style.setProperty("--res", getComputedStyle(punta).getPropertyValue("--c").trim());
  $("nombre-color").textContent = r.parentElement.title;
}));

// Cada campo solo deja escribir lo que tiene sentido para ese dato.
const SOLO_LETRAS = /[^A-Za-zÁÉÍÓÚÑÜáéíóúñü' .-]/g;
const LETRAS_Y_NUMEROS = /[^A-Za-zÁÉÍÓÚÑÜáéíóúñü0-9°ºª ,.-]/g;
[["estudiante", SOLO_LETRAS], ["docente", SOLO_LETRAS], ["autor", SOLO_LETRAS],
 ["curso", LETRAS_Y_NUMEROS]].forEach(([id, filtro]) =>
  $(id).addEventListener("input", () => {
    const limpio = $(id).value.replace(filtro, "");
    if (limpio !== $(id).value) $(id).value = limpio;
  }));

const EJEMPLOS_NIVEL = {
  ninos: '"Las plantas comen la luz del sol para crecer fuertes y sanas."',
  secundaria: '"La fotosíntesis convierte la luz solar en energía química que la planta usa para crecer."',
  adultos: '"La fotosíntesis es el proceso bioquímico mediante el cual los organismos autótrofos sintetizan compuestos orgánicos a partir de energía lumínica."',
};
document.querySelectorAll('input[name="nivel"]').forEach(r => r.addEventListener("change", () => {
  $("texto-nivel").textContent = EJEMPLOS_NIVEL[r.value] || "";
}));

[["con_imagenes", "det-imagenes"], ["con_graficos", "det-graficos"]].forEach(([c, d]) =>
  $(c).addEventListener("change", () => $(d).classList.toggle("visible", $(c).checked)));

function mostrar(msg, error = false) {
  $("estado").textContent = msg;
  $("estado").className = "estado" + (error ? " error" : "");
}
// Se pueden elegir varios PDF (hasta MAXIMO_PDF). Cada uno es una tarjeta con su propia barra.
const MAXIMO_PDF = 8;
const EN_CURSO = ["porsubir", "subiendo", "cola", "haciendo"];
let pdfs = [];   // {archivo, nombre, id, fase, porcentaje, paso, error, aviso, paginas, minAntes, minAhora, tarjeta}

function elegir(lista) {
  const elegidos = [...lista];
  if (!elegidos.length) return;
  const validos = elegidos.filter(f => f.name.toLowerCase().endsWith(".pdf"));
  const avisos = [];
  const noPdf = elegidos.length - validos.length;
  if (noPdf) avisos.push(noPdf === 1 ? "Un archivo no era PDF y no se agregó." : `${noPdf} archivos no eran PDF y no se agregaron.`);
  // Los terminados se quedan (para volver a bajarlos) hasta que se limpien con la escoba.
  $("ahorro").classList.remove("visible");
  // Máximo 8 entre los elegidos y los que se están creando: si no caben, se bloquean y se avisa.
  const pendientes = pdfs.filter(p => p.fase !== "listo" && p.fase !== "error").length;
  const caben = validos.slice(0, Math.max(0, MAXIMO_PDF - pendientes));
  if (validos.length && !caben.length) {
    avisos.push(`Ya hay ${MAXIMO_PDF} PDF, el máximo. Espera a que terminen los demás para agregar más.`);
  } else if (caben.length < validos.length) {
    avisos.push(`Solo se agregaron ${caben.length}: el máximo es ${MAXIMO_PDF} PDF a la vez. `
      + `Espera a que terminen los demás para agregar ${validos.length - caben.length === 1 ? "el otro" : "los otros"}.`);
  }
  caben.forEach(f => agregarTarjeta({ archivo: f, nombre: f.name, fase: "elegido", porcentaje: 0 }));
  $("pdf").value = "";
  mostrar(avisos.join(" "), avisos.length > 0);
  actualizarBoton();
}
$("pdf").addEventListener("change", e => elegir(e.target.files));
const zona = $("zona");
["dragover", "dragenter"].forEach(e => zona.addEventListener(e, ev => { ev.preventDefault(); zona.classList.add("activa"); }));
["dragleave", "drop"].forEach(e => zona.addEventListener(e, () => zona.classList.remove("activa")));
zona.addEventListener("drop", ev => { ev.preventDefault(); elegir(ev.dataTransfer.files); });

// Imagen de la portada: la vista previa usa el mismo recorte que el PDF (object-position = foco).
let portada = null;
let foco = { x: 0.5, y: 0.5 };
function aplicarFoco() {
  $("previa-img").style.objectPosition = `${foco.x * 100}% ${foco.y * 100}%`;
}
function elegirPortada(f) {
  if (!f) return;
  if (!/^image\/(jpeg|png|webp)$/.test(f.type)) return mostrar("La imagen de la portada tiene que ser JPG, PNG o WebP.", true);
  if (f.size > 8 * 1024 * 1024) return mostrar("La imagen de la portada pesa más de 8 MB. Elige una más liviana.", true);
  portada = f;
  foco = { x: 0.5, y: 0.5 };
  if ($("previa-img").src) URL.revokeObjectURL($("previa-img").src);
  $("previa-img").src = URL.createObjectURL(f);
  aplicarFoco();
  $("zona-portada").hidden = true;
  $("portada-previa").hidden = false;
  mostrar("");
}
function moverFoco(ev) {
  const caja = $("previa-marco").getBoundingClientRect();
  foco = {
    x: Math.min(1, Math.max(0, (ev.clientX - caja.left) / caja.width)),
    y: Math.min(1, Math.max(0, (ev.clientY - caja.top) / caja.height)),
  };
  aplicarFoco();
}
$("portada").addEventListener("change", e => elegirPortada(e.target.files[0]));
$("previa-marco").addEventListener("click", moverFoco);
$("previa-marco").addEventListener("keydown", ev => {   // con el teclado: flechas mueven el recorte
  const paso = { ArrowLeft: [-0.1, 0], ArrowRight: [0.1, 0], ArrowUp: [0, -0.1], ArrowDown: [0, 0.1] }[ev.key];
  if (!paso) return;
  ev.preventDefault();
  foco = { x: Math.min(1, Math.max(0, foco.x + paso[0])), y: Math.min(1, Math.max(0, foco.y + paso[1])) };
  aplicarFoco();
});
$("quitar-portada").addEventListener("click", () => {
  portada = null;
  $("portada").value = "";
  $("portada-previa").hidden = true;
  $("zona-portada").hidden = false;
});
const zonaPortada = $("zona-portada");
["dragover", "dragenter"].forEach(e => zonaPortada.addEventListener(e, ev => { ev.preventDefault(); zonaPortada.classList.add("activa"); }));
["dragleave", "drop"].forEach(e => zonaPortada.addEventListener(e, () => zonaPortada.classList.remove("activa")));
zonaPortada.addEventListener("drop", ev => { ev.preventDefault(); elegirPortada(ev.dataTransfer.files[0]); });

function opcionesComunes() {
  const comunes = [];
  if (portada) comunes.push(["portada", portada], ["foco_x", foco.x.toFixed(3)], ["foco_y", foco.y.toFixed(3)]);
  ["portada_respaldo", "nivel", "color", "cant_imagenes", "origen_imagenes", "cant_graficos"].forEach(n =>
    comunes.push([n, document.querySelector(`input[name="${n}"]:checked`).value]));
  ["estudiante", "curso", "docente", "autor"].forEach(n => comunes.push([n, $(n).value]));
  ["con_mapa", "con_imagenes", "con_graficos"].forEach(n => comunes.push([n, $(n).checked ? "si" : "no"]));
  return comunes;
}

$("boton").addEventListener("click", () => {
  const comunes = opcionesComunes();
  pdfs.filter(p => p.fase === "elegido").forEach(p => {
    Object.assign(p, { fase: "porsubir", comunes, porcentaje: 0, paso: "Esperando para subir…" });
    pintarTarjeta(p);
  });
  $("aviso").textContent = "";
  $("ahorro").classList.remove("visible");
  const varios = pdfs.filter(p => EN_CURSO.includes(p.fase)).length > 1;
  mostrar(varios ? "Se hacen todos a la vez. Puedes cambiar de página: siguen igual y la campana del menú te avisa."
    : "Puedes cambiar de página: el resumen sigue y la campana del menú te avisa.");
  empezar();
});

// ---- Tarjetas: una por PDF, con su barra y su botón de descarga ----
const CHIPS = { elegido: "Elegido", porsubir: "Por subir", subiendo: "Subiendo", cola: "En cola",
                haciendo: "Creando", listo: "Listo", error: "Error" };
const ICONO_BAJAR = '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M12 4v11m0 0-4.5-4.5M12 15l4.5-4.5" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/><path d="M5 19.5h14" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"/></svg>';
const ICONO_HECHO = '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="m5.5 12.5 4 4 9-9.5" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/></svg>';

function agregarTarjeta(p) {
  const t = document.createElement("div");
  t.className = "pdf-tarjeta";
  t.innerHTML = `<div class="pdf-fila"><span class="pdf-icono" aria-hidden="true">PDF</span>
      <span class="pdf-nombre"></span><span class="pdf-chip"></span>
      <button type="button" class="pdf-bajar" disabled></button></div>
    <div class="barra visible" role="progressbar" aria-valuemin="0" aria-valuemax="100"><div></div></div>
    <div class="pdf-fila"><span class="pdf-paso"></span><span class="pdf-accion"></span></div>
    <p class="pdf-aviso"></p>`;
  t.querySelector(".pdf-nombre").textContent = p.nombre;
  t.querySelector(".pdf-nombre").title = p.nombre;
  t.querySelector(".barra").setAttribute("aria-label", `Avance de ${p.nombre}`);
  t.querySelector(".pdf-bajar").addEventListener("click", () => bajarUno(p));
  p.tarjeta = t;
  pdfs.push(p);
  $("cuadros").appendChild(t);
  pintarTarjeta(p);
}
function quitarTarjeta(p) {
  p.tarjeta.remove();
  pdfs = pdfs.filter(x => x !== p);
}
function boton(texto, alTocar) {
  const b = document.createElement("button");
  b.type = "button"; b.className = "pdf-boton"; b.textContent = texto;
  b.addEventListener("click", alTocar);
  return b;
}
function pintarTarjeta(p) {
  const t = p.tarjeta;
  const porcentaje = p.fase === "listo" ? 100 : p.porcentaje || 0;
  t.dataset.fase = p.fase;
  t.classList.toggle("bajado", p.fase === "listo" && !!p.bajado);
  t.querySelector(".pdf-chip").textContent = CHIPS[p.fase];
  t.querySelector(".barra div").style.width = porcentaje + "%";
  t.querySelector(".barra").setAttribute("aria-valuenow", porcentaje);
  const detalle = p.paginas ? `${p.paginas} págs. · lectura de ${p.minAntes} a ${p.minAhora} min` : "";
  const pasos = {
    elegido: "Listo para empezar",
    cola: "En cola: empieza cuando termine otro resumen.",
    listo: p.bajado ? `Descargado${detalle ? " · " + detalle : ""}` : `Listo para descargar${detalle ? " · " + detalle : ""}`,
    error: p.error,
  };
  t.querySelector(".pdf-paso").textContent = pasos[p.fase] || p.paso || "";
  // Botón de descarga: apagado mientras se crea; al terminar se enciende y queda encendido.
  const bajar = t.querySelector(".pdf-bajar");
  bajar.hidden = p.fase === "elegido" || p.fase === "error";
  bajar.disabled = p.fase !== "listo" || !!p.bajando;
  bajar.innerHTML = p.bajado ? ICONO_HECHO : ICONO_BAJAR;
  bajar.setAttribute("aria-label", p.fase !== "listo" ? `${p.nombre}: todavía se está creando`
    : p.bajado ? `Descargar ${p.nombre} otra vez` : `Descargar ${p.nombre}`);
  bajar.title = p.fase !== "listo" ? "Se enciende cuando termine" : p.bajado ? "Descargar otra vez" : "Descargar";
  const accion = t.querySelector(".pdf-accion");
  accion.innerHTML = "";
  if (p.fase === "haciendo") accion.textContent = porcentaje + " %";
  if (p.fase === "elegido") {
    const quitar = boton("Quitar", () => { quitarTarjeta(p); actualizarBoton(); });
    quitar.setAttribute("aria-label", `Quitar ${p.nombre}`);
    accion.appendChild(quitar);
  }
  if (p.fase === "error" && p.archivo) accion.appendChild(boton("Reintentar", () => {
    Object.assign(p, { fase: "porsubir", porcentaje: 0, paso: "Esperando para subir…", error: null });
    pintarTarjeta(p);
    $("ahorro").classList.remove("visible");
    empezar();
  }));
  t.querySelector(".pdf-aviso").textContent = p.fase === "listo" ? p.aviso || "" : "";
  pintarTotal();
}
function pintarTotal() {
  const cuenta = (...fases) => pdfs.filter(p => fases.includes(p.fase)).length;
  const partes = [];
  if (cuenta(...EN_CURSO, "listo", "error")) {
    partes.push(`${cuenta("listo")} de ${pdfs.length} listos`);
    if (cuenta("haciendo")) partes.push(`${cuenta("haciendo")} creándose`);
    if (cuenta("cola")) partes.push(`${cuenta("cola")} en cola`);
    if (cuenta("porsubir", "subiendo")) partes.push(`${cuenta("porsubir", "subiendo")} subiendo`);
    if (cuenta("error")) partes.push(`${cuenta("error")} con error`);
  }
  $("total").textContent = partes.join(" · ");
  $("lote").hidden = !partes.length;
  $("escoba").disabled = !cuenta("listo", "error");
  const sinBajar = pdfs.filter(p => p.fase === "listo" && !p.bajado && !p.bajando).length;
  $("bajar-todos").hidden = !cuenta("listo");
  $("bajar-todos").disabled = !sinBajar;
  $("bajar-todos").textContent = sinBajar ? `Descargar los terminados (${sinBajar})` : "Descargar los terminados";
  $("nombre").textContent = pdfs.length === 1 ? pdfs[0].nombre : pdfs.length ? `${pdfs.length} PDF en la lista` : "";
}
function actualizarBoton() {
  const elegidos = pdfs.filter(p => p.fase === "elegido").length;
  $("boton").disabled = !elegidos;
  $("boton").textContent = elegidos > 1 ? `Crear ${elegidos} resúmenes` : "Crear mi resumen";
  pintarTotal();
}

// ---- Descargas: solo cuando la persona toca el botón ----
async function bajarUno(p) {
  if (p.fase !== "listo" || p.bajando) return;
  p.bajando = true;
  pintarTarjeta(p);
  const pudo = await ListaResumenes.bajar(p.id);
  p.bajando = false;
  if (pudo) {
    p.bajado = true;
    pintarTarjeta(p);
  } else {
    fallar(p, "Este resumen ya no está en el servidor (pasa después de una hora). Vuelve a crearlo.");
  }
}
$("bajar-todos").addEventListener("click", async () => {
  // De a uno, con una pausa corta: así el navegador no los toma como descargas no deseadas.
  for (const p of pdfs.filter(x => x.fase === "listo" && !x.bajado)) {
    await bajarUno(p);
    await esperar(400);
  }
});

// ---- Escoba: quita los terminados y los que fallaron, con «Deshacer» por 6 segundos ----
let limpiados = null, relojDeshacer = null;
$("escoba").addEventListener("click", () => {
  const quitar = pdfs.filter(p => p.fase === "listo" || p.fase === "error");
  if (!quitar.length) return;
  limpiados = quitar;
  quitar.forEach(quitarTarjeta);
  guardarTrabajos();
  $("ahorro").classList.remove("visible");
  $("aviso").textContent = "";
  mostrar("");
  $("deshacer-texto").textContent = quitar.length === 1 ? "Se limpió 1 resumen." : `Se limpiaron ${quitar.length} resúmenes.`;
  $("deshacer").hidden = false;
  pintarVacio();
  actualizarBoton();
  clearTimeout(relojDeshacer);
  relojDeshacer = setTimeout(() => { $("deshacer").hidden = true; limpiados = null; }, 6000);
});
$("boton-deshacer").addEventListener("click", () => {
  if (limpiados) {
    limpiados.forEach(p => { pdfs.push(p); $("cuadros").appendChild(p.tarjeta); });
    limpiados = null;
    guardarTrabajos();
    pintarVacio();
    actualizarBoton();
  }
  $("deshacer").hidden = true;
});
function pintarVacio() {
  $("vacio").hidden = pdfs.length > 0 || $("deshacer").hidden;
}

// ---- Avance real de los resúmenes ----
// El servidor hace cada resumen en segundo plano (hasta 8 a la vez) y la página pregunta cada
// segundo cómo van todos, en un solo pedido. La lista queda guardada en el navegador
// (ListaResumenes): si se recarga o se cierra la pestaña, al volver las barras siguen donde iban
// y los terminados se pueden bajar durante una hora.
const esperar = ms => new Promise(r => setTimeout(r, ms));
function guardarTrabajos() {
  ListaResumenes.guardar(pdfs.filter(p => p.id && ["cola", "haciendo", "listo"].includes(p.fase))
    .map(p => ({ id: p.id, nombre: p.nombre, inicio: p.inicio, listo: p.fase === "listo", bajado: !!p.bajado })));
}
function nuevoId() {
  return (crypto.randomUUID ? crypto.randomUUID() : Date.now().toString(16) + Math.random().toString(16).slice(2))
    .replace(/-/g, "").padEnd(32, "0").slice(0, 32);
}

let subiendo = false, vigilando = false;
function empezar() {
  actualizarBoton();
  if (!subiendo) subirPendientes();
  if (!vigilando) vigilar();
}

// Se suben de a uno (cada subida tarda un instante), así no se satura la conexión.
async function subirPendientes() {
  subiendo = true;
  // Mientras un archivo se está enviando, salir de la página cortaría la subida.
  const noSalir = ev => { ev.preventDefault(); ev.returnValue = ""; };
  window.addEventListener("beforeunload", noSalir);
  try {
    let p;
    while ((p = pdfs.find(x => x.fase === "porsubir"))) await subir(p);
  } finally {
    window.removeEventListener("beforeunload", noSalir);
    subiendo = false;
  }
}
async function subir(p) {
  const datos = new FormData();
  datos.append("pdf", p.archivo);
  p.comunes.forEach(([clave, valor]) => datos.append(clave, valor));
  Object.assign(p, { id: nuevoId(), inicio: Date.now(), fase: "subiendo", paso: "Subiendo el documento…", bajado: false });
  datos.append("id", p.id);
  pintarTarjeta(p);
  let r;
  try {
    r = await fetch("/resumir", { method: "POST", body: datos });
  } catch {
    return fallar(p, "No se pudo subir. Revisa tu internet y toca «Reintentar».");
  }
  const e = await r.json().catch(() => ({}));
  if (!r.ok) return fallar(p, e.error || "No se pudo crear el resumen. Inténtalo otra vez.");
  p.id = e.id;
  aplicar(p, e);
  guardarTrabajos();
}
function fallar(p, mensaje) {
  Object.assign(p, { fase: "error", error: mensaje });
  pintarTarjeta(p);
  guardarTrabajos();
}
function aplicar(p, e) {
  if (e.fase === "listo") {
    const r = e.resultado || {};
    Object.assign(p, { fase: "listo", porcentaje: 100, paginas: Number(r.paginas) || 0,
                       minAntes: Number(r.min_original) || 0, minAhora: Number(r.min_resumen) || 0, aviso: r.aviso || "" });
  } else {
    Object.assign(p, { porcentaje: e.porcentaje || 0, paso: e.paso, fase: e.en_cola ? "cola" : "haciendo" });
  }
  pintarTarjeta(p);
}

async function vigilar() {
  vigilando = true;
  let fallos = 0;
  while (pdfs.some(p => EN_CURSO.includes(p.fase))) {
    const enServidor = pdfs.filter(p => p.id && ["cola", "haciendo"].includes(p.fase));
    if (!enServidor.length) { await esperar(500); continue; }
    let estados;
    try {
      estados = await ListaResumenes.estados(enServidor.map(p => p.id));
    } catch {
      // Se cortó internet un momento: se sigue preguntando, el servidor no se detiene.
      if (++fallos > 60) {
        enServidor.forEach(p => fallar(p, "Se perdió la conexión con el servidor. Recarga la página para retomar."));
        continue;
      }
      mostrar("Sin conexión con el servidor. Reintentando…", true);
      await esperar(2000);
      continue;
    }
    if (fallos) mostrar("");
    fallos = 0;
    let cambio = false;
    for (const p of enServidor) {
      const e = estados[p.id];
      if (!e || !["cola", "haciendo"].includes(p.fase)) continue;
      if (e.fase === "error" && e.perdido && p.restaurado && p.listo) {
        quitarTarjeta(p);   // terminado hace más de una hora: ya se borró del servidor
        cambio = true;
      } else if (e.fase === "error") {
        // Recién empezado y el servidor no lo conoce: la subida se cortó al salir de la página.
        const cortado = e.perdido && p.inicio && Date.now() - p.inicio < 120000;
        fallar(p, cortado ? "La subida se interrumpió. Vuelve a elegir este PDF." : e.error);
      } else {
        if (e.fase === "listo") cambio = true;
        aplicar(p, e);
      }
    }
    if (cambio) guardarTrabajos();
    await esperar(1000);
  }
  vigilando = false;
  terminar();
}

// Cuando ya no queda nada creándose: el cuadro del tiempo ahorrado, con la suma de todos.
function terminar() {
  actualizarBoton();
  pintarVacio();
  const listos = pdfs.filter(p => p.fase === "listo");
  const errores = pdfs.filter(p => p.fase === "error").length;
  if (!listos.length) {
    if (errores) mostrar(pdfs.length === 1 ? pdfs[0].error : "No se pudo crear ningún resumen. Mira el error en cada documento.", true);
    return;
  }
  const suma = clave => listos.reduce((total, p) => total + (p[clave] || 0), 0);
  const varios = listos.length > 1;
  $("ahorro-titulo").textContent = varios ? `Tus ${listos.length} resúmenes están listos` : "Tu resumen está listo";
  $("ahorro-texto").textContent = varios
    ? `Los ${listos.length} documentos tenían ${suma("paginas")} páginas en total. Tiempo de lectura:`
    : `El documento tenía ${suma("paginas")} páginas. Tiempo de lectura:`;
  $("antes").textContent = `${suma("minAntes")} min`;
  $("ahora").textContent = `${suma("minAhora")} min`;
  $("descarga-nota").textContent = varios ? "Toca el botón amarillo de cada uno para descargarlo."
    : "Toca el botón amarillo para descargarlo.";
  $("ahorro").classList.add("visible");
  // Después de recargar la página el archivo ya no está en el navegador: hay que volver a elegirlo.
  const comoReintentar = pdfs.some(p => p.fase === "error" && p.archivo)
    ? "toca «Reintentar» en los que fallaron." : "vuelve a elegir los que fallaron.";
  mostrar(errores ? `${listos.length} listos y ${errores} con error: ${comoReintentar}` : "", errores > 0);
}

// Al abrir la página: los resúmenes de la lista (a medio hacer o terminados en la última hora)
// vuelven a aparecer y se retoman.
ListaResumenes.leer().forEach(t => agregarTarjeta({
  id: t.id, nombre: t.nombre || "documento.pdf", inicio: t.inicio, bajado: !!t.bajado, listo: !!t.listo,
  restaurado: true, fase: "cola", porcentaje: 0, paso: t.listo ? "Buscando tu resumen…" : "Retomando…" }));
if (pdfs.length) {
  if (pdfs.some(p => !p.listo)) mostrar(pdfs.length > 1 ? "Retomando tus resúmenes…" : "Retomando tu resumen…");
  empezar();
}
pintarVacio();
