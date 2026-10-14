// Botón «Video» del inicio: abre la guía en grande y la reproduce. Se cierra con «Cerrar», con Esc
// o tocando fuera del video; al cerrar se pausa. Sin este archivo el botón igual abre el video solo.
(() => {
  const boton = document.getElementById("abrir-video");
  const ventana = document.getElementById("video-ventana");
  const video = document.getElementById("video-guia");
  if (!boton || !ventana || !video) return;

  const cerrar = () => { video.pause(); ventana.hidden = true; boton.focus(); };
  boton.addEventListener("click", e => {
    e.preventDefault();
    ventana.hidden = false;
    video.play().catch(() => {});
  });
  document.getElementById("video-cerrar").addEventListener("click", cerrar);
  ventana.addEventListener("click", e => { if (e.target === ventana) cerrar(); });
  document.addEventListener("keydown", e => { if (e.key === "Escape" && !ventana.hidden) cerrar(); });
})();
