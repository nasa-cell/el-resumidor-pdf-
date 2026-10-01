// En las páginas que no son "Crear resumen": si hay un resumen creándose (se empezó y la persona
// se fue a otra página), muestra un aviso flotante con el avance y, cuando termina, un botón para
// volver a "Crear resumen", donde se descarga solo. El resumen nunca se detiene al cambiar de página.
(() => {
  const CLAVE_TRABAJO = "resumidor_trabajo";
  let pendiente = null;
  try { pendiente = JSON.parse(localStorage.getItem(CLAVE_TRABAJO)); } catch { /* sin almacenamiento */ }
  if (!pendiente || !pendiente.id) return;

  const aviso = document.createElement("a");
  aviso.className = "aviso-trabajo";
  aviso.href = "/crear";
  aviso.setAttribute("role", "status");
  document.body.appendChild(aviso);

  function pintar(texto, listo = false, error = false) {
    aviso.classList.toggle("listo", listo);
    aviso.classList.toggle("error", error);
    aviso.innerHTML = "";
    if (!listo && !error) {
      const giro = document.createElement("span");
      giro.className = "aviso-trabajo-giro";
      aviso.appendChild(giro);
    }
    const t = document.createElement("span");
    t.textContent = texto;
    aviso.appendChild(t);
  }

  async function preguntar() {
    let e;
    try {
      const r = await fetch(`/resumir/${pendiente.id}`, { cache: "no-store" });
      e = await r.json().catch(() => ({}));
      if (!r.ok) {
        // Recién empezado y el servidor no lo conoce: la subida se cortó al cambiar de página.
        const reciente = pendiente.inicio && Date.now() - pendiente.inicio < 120000;
        e = { fase: "error", error: reciente
          ? "la subida del PDF se interrumpió. Vuelve a «Crear resumen» y súbelo otra vez."
          : (e.error || "el resumen ya no está disponible.") };
      }
    } catch {
      pintar("Sin conexión con el servidor. Reintentando…");
      return setTimeout(preguntar, 3000);
    }
    if (e.fase === "error") {
      try { localStorage.removeItem(CLAVE_TRABAJO); } catch { /* nada que borrar */ }
      pintar(`No se pudo crear el resumen: ${e.error || "inténtalo otra vez"}`, false, true);
      return;
    }
    if (e.fase === "listo") {
      pintar("✓ Tu resumen está listo. Toca aquí para descargarlo", true);
      return;
    }
    pintar(`Creando tu resumen… ${e.porcentaje || 0} % · Ver`);
    setTimeout(preguntar, 1500);
  }
  pintar("Creando tu resumen…");
  preguntar();
})();
