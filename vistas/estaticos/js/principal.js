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

$("boton").addEventListener("click", async () => {
  const datos = new FormData();
  datos.append("pdf", archivo);
  ["nivel", "color"].forEach(n => datos.append(n, document.querySelector(`input[name="${n}"]:checked`).value));
  ["estudiante", "curso", "docente", "autor"].forEach(n => datos.append(n, $(n).value));
  datos.append("con_imagenes", $("con_imagenes").checked ? "si" : "no");
  datos.append("con_graficos", $("con_graficos").checked ? "si" : "no");
  ["cant_imagenes", "origen_imagenes", "cant_graficos"].forEach(n =>
    datos.append(n, document.querySelector(`input[name="${n}"]:checked`).value));
  $("aviso").textContent = "";

  $("boton").disabled = true; $("barra").classList.add("visible"); $("ahorro").classList.remove("visible");
  mostrar("Leyendo el documento y preparando todo. Puede tardar 1 o 2 minutos.");
  try {
    const r = await fetch("/resumir", { method: "POST", body: datos });
    if (!r.ok) {
      const e = await r.json().catch(() => ({}));
      throw new Error(e.error || "No se pudo crear el resumen. Inténtalo otra vez.");
    }
    const blob = await r.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = "resumen_" + archivo.name; a.click();
    URL.revokeObjectURL(url);

    $("ahorro-texto").textContent = `El documento tenía ${r.headers.get("X-Paginas")} páginas. Tiempo de lectura:`;
    $("antes").textContent = `${r.headers.get("X-Min-Original")} min`;
    $("ahora").textContent = `${r.headers.get("X-Min-Resumen")} min`;
    $("ahorro").classList.add("visible");
    mostrar("Resumen creado.");
    $("aviso").textContent = decodeURIComponent(r.headers.get("X-Aviso") || "");
  } catch (err) {
    mostrar(err.message, true);
  } finally {
    $("boton").disabled = false; $("barra").classList.remove("visible");
  }
});
