// Movimiento con el mouse (sin 3D): botones magnéticos y mascotas que giran hacia el cursor.
(function () {
  const puedeMover = matchMedia("(hover: hover) and (pointer: fine)").matches
    && !matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (!puedeMover) return;

  document.querySelectorAll(".magnetico").forEach(boton => {
    // la animación de entrada usa "forwards": si no se libera, sigue reteniendo el
    // transform del botón para siempre y el movimiento del mouse no se nota.
    boton.addEventListener("animationend", () => boton.classList.remove("aparece"), { once: true });
    boton.addEventListener("mousemove", e => {
      const r = boton.getBoundingClientRect();
      const x = e.clientX - r.left - r.width / 2;
      const y = e.clientY - r.top - r.height / 2;
      boton.style.transform = `translate(${x * 0.18}px, ${y * 0.35}px)`;
    });
    boton.addEventListener("mousedown", () => { boton.style.transform = ""; });
    boton.addEventListener("mouseleave", () => { boton.style.transform = ""; });
  });

  const hero = document.querySelector(".hero");
  const mascotas = document.querySelectorAll(".mascota");
  if (hero && mascotas.length) {
    hero.addEventListener("mousemove", e => {
      const r = hero.getBoundingClientRect();
      const x = (e.clientX - r.left) / r.width - 0.5;
      const y = (e.clientY - r.top) / r.height - 0.5;
      mascotas.forEach(m => { m.style.setProperty("--mx", x); m.style.setProperty("--my", y); });
    });
    hero.addEventListener("mouseleave", () => {
      mascotas.forEach(m => { m.style.removeProperty("--mx"); m.style.removeProperty("--my"); });
    });
  }
})();
