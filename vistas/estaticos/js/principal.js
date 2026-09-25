// Lógica de la página: opciones, envío del PDF y resultado
const $ = id => document.getElementById(id);
let archivo = null;

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
function elegir(f) {
  if (!f) return;
  if (!f.name.toLowerCase().endsWith(".pdf")) return mostrar("Ese archivo no es un PDF. Elige uno que termine en .pdf.", true);
  archivo = f; $("nombre").textContent = f.name; $("boton").disabled = false; mostrar("");
}
$("pdf").addEventListener("change", e => elegir(e.target.files[0]));
const zona = $("zona");
["dragover", "dragenter"].forEach(e => zona.addEventListener(e, ev => { ev.preventDefault(); zona.classList.add("activa"); }));
["dragleave", "drop"].forEach(e => zona.addEventListener(e, () => zona.classList.remove("activa")));
zona.addEventListener("drop", ev => { ev.preventDefault(); elegir(ev.dataTransfer.files[0]); });

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

$("boton").addEventListener("click", async () => {
  const datos = new FormData();
  datos.append("pdf", archivo);
  if (portada) {
    datos.append("portada", portada);
    datos.append("foco_x", foco.x.toFixed(3));
    datos.append("foco_y", foco.y.toFixed(3));
  }
  datos.append("portada_respaldo", document.querySelector('input[name="portada_respaldo"]:checked').value);
  ["nivel", "color"].forEach(n => datos.append(n, document.querySelector(`input[name="${n}"]:checked`).value));
  ["estudiante", "curso", "docente", "autor"].forEach(n => datos.append(n, $(n).value));
  datos.append("con_mapa", $("con_mapa").checked ? "si" : "no");
  datos.append("con_imagenes", $("con_imagenes").checked ? "si" : "no");
  datos.append("con_graficos", $("con_graficos").checked ? "si" : "no");
  ["cant_imagenes", "origen_imagenes", "cant_graficos"].forEach(n =>
    datos.append(n, document.querySelector(`input[name="${n}"]:checked`).value));
  $("aviso").textContent = "";

  empezarEspera();
  mostrar("Subiendo el documento…");
  await conEspera(async () => {
    const r = await fetch("/resumir", { method: "POST", body: datos });
    const e = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(e.error || "No se pudo crear el resumen. Inténtalo otra vez.");
    guardarTrabajo({ id: e.id, nombre: archivo.name });
    await seguir(e.id);
  });
});

// ---- Avance real del resumen ----
// El servidor hace el resumen en segundo plano y la página pregunta cada poco cómo va. El número
// de trabajo queda guardado en el navegador: si se recarga o se cierra la pestaña, al volver la
// barra sigue desde donde iba y el PDF se descarga igual cuando termina.
const CLAVE_TRABAJO = "resumidor_trabajo";
const esperar = ms => new Promise(r => setTimeout(r, ms));
function guardarTrabajo(t) { try { localStorage.setItem(CLAVE_TRABAJO, JSON.stringify(t)); } catch { /* navegador sin almacenamiento */ } }
function leerTrabajo() { try { return JSON.parse(localStorage.getItem(CLAVE_TRABAJO)); } catch { return null; } }
function olvidarTrabajo() { try { localStorage.removeItem(CLAVE_TRABAJO); } catch { /* nada que borrar */ } }

function empezarEspera() {
  $("boton").disabled = true;
  $("ahorro").classList.remove("visible");
  $("barra").classList.add("visible");
  pintarAvance(0);
}
function pintarAvance(porcentaje) {
  $("barra").firstElementChild.style.width = porcentaje + "%";
  $("barra").setAttribute("aria-valuenow", porcentaje);
  $("porcentaje").textContent = porcentaje + " %";
}
async function conEspera(tarea) {
  try {
    await tarea();
  } catch (err) {
    mostrar(err.message, true);
  } finally {
    $("boton").disabled = !archivo;
    $("barra").classList.remove("visible");
    $("porcentaje").textContent = "";
  }
}

async function seguir(id) {
  let fallos = 0;
  for (;;) {
    let r;
    try {
      r = await fetch(`/resumir/${id}`, { cache: "no-store" });
    } catch {
      // Se cortó internet un momento: se sigue preguntando, el servidor no se detiene.
      if (++fallos > 60) throw new Error("Se perdió la conexión con el servidor. Recarga la página para retomar.");
      mostrar("Sin conexión con el servidor. Reintentando…", true);
      await esperar(2000);
      continue;
    }
    fallos = 0;
    const e = await r.json().catch(() => ({}));
    if (!r.ok || e.fase === "error") {
      olvidarTrabajo();
      throw new Error(e.error || "No se pudo crear el resumen. Inténtalo otra vez.");
    }
    pintarAvance(e.porcentaje);
    mostrar(e.paso);
    if (e.fase === "listo") break;
    await esperar(800);
  }
  await descargar(id);
}

async function descargar(id) {
  const r = await fetch(`/resumir/${id}/pdf`);
  if (!r.ok) {
    olvidarTrabajo();
    throw new Error("El resumen ya no está disponible. Vuelve a crearlo.");
  }
  const nombre = /filename="?([^";]+)"?/.exec(r.headers.get("Content-Disposition") || "");
  const url = URL.createObjectURL(await r.blob());
  const a = document.createElement("a");
  a.href = url; a.download = nombre ? decodeURIComponent(nombre[1]) : "resumen.pdf"; a.click();
  setTimeout(() => URL.revokeObjectURL(url), 5000);

  $("ahorro-texto").textContent = `El documento tenía ${r.headers.get("X-Paginas")} páginas. Tiempo de lectura:`;
  $("antes").textContent = `${r.headers.get("X-Min-Original")} min`;
  $("ahora").textContent = `${r.headers.get("X-Min-Resumen")} min`;
  $("ahorro").classList.add("visible");
  mostrar("Resumen creado.");
  $("aviso").textContent = decodeURIComponent(r.headers.get("X-Aviso") || "");
  olvidarTrabajo();
}

// Al abrir la página: si quedó un resumen a medio hacer (se recargó o se cerró), se retoma.
const pendiente = leerTrabajo();
if (pendiente && pendiente.id) {
  empezarEspera();
  mostrar("Retomando tu resumen…");
  conEspera(() => seguir(pendiente.id));
}
