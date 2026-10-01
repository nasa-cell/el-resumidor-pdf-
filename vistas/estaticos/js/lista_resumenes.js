// Lista de tus resúmenes guardada en el navegador, la misma en todas las páginas: los que se están
// creando y los terminados (con «bajado» si ya se descargaron). La usan «Crear resumen» y la campana
// del menú. Los resúmenes quedan una hora en el servidor; después se borran solos de la lista.
const ListaResumenes = (() => {
  const CLAVE = "resumidor_trabajos";

  function leer() {
    let lista = [];
    try {
      lista = JSON.parse(localStorage.getItem(CLAVE)) || [];
      const viejo = JSON.parse(localStorage.getItem("resumidor_trabajo"));   // de la versión de un solo PDF
      if (viejo && viejo.id) {
        lista.push(viejo);
        localStorage.removeItem("resumidor_trabajo");
        localStorage.setItem(CLAVE, JSON.stringify(lista));
      }
    } catch { /* navegador sin almacenamiento */ }
    return Array.isArray(lista) ? lista.filter(t => t && t.id) : [];
  }
  function guardar(lista) {
    try { localStorage.setItem(CLAVE, JSON.stringify(lista)); } catch { /* navegador sin almacenamiento */ }
  }
  function cambiar(id, cambios) {
    const lista = leer();
    const t = lista.find(x => x.id === id);
    if (t) { Object.assign(t, cambios); guardar(lista); }
  }
  function quitar(ids) {
    guardar(leer().filter(t => !ids.includes(t.id)));
  }
  async function estados(ids) {
    const r = await fetch(`/estados?ids=${ids.join(",")}`, { cache: "no-store" });
    return r.json();
  }
  // Baja el PDF terminado. Devuelve true si se pudo.
  async function bajar(id) {
    let r = null;
    try { r = await fetch(`/resumir/${id}/pdf`); } catch { /* sin conexión */ }
    if (!r || !r.ok) return false;
    const nombre = /filename="?([^";]+)"?/.exec(r.headers.get("Content-Disposition") || "");
    const url = URL.createObjectURL(await r.blob());
    const a = document.createElement("a");
    a.href = url; a.download = nombre ? decodeURIComponent(nombre[1]) : "resumen.pdf";
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 5000);
    cambiar(id, { bajado: true });
    return true;
  }
  return { leer, guardar, cambiar, quitar, estados, bajar };
})();
