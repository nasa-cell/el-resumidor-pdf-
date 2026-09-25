"""Modelo: lee el PDF original (bytes, texto, páginas e imágenes)."""
import io

from PIL import Image, ImageStat
from pypdf import PdfReader

# Una imagen casi de un solo color (fondo, mancha, capa de relleno) no sirve para el resumen.
VARIACION_MINIMA = 8


def _a_rgb(imagen):
    """Pasa la imagen a RGB sin que lo transparente quede negro.

    En las imágenes con transparencia (logos, diagramas, dibujos exportados en PNG) la parte
    transparente guarda color negro: al quitarle la transparencia sin más, el fondo salía negro.
    Se pone sobre fondo blanco, como se ve en el PDF.
    """
    if imagen.mode == "P" and "transparency" in imagen.info:
        imagen = imagen.convert("RGBA")
    if imagen.mode in ("RGBA", "LA", "PA"):
        imagen = imagen.convert("RGBA")
        fondo = Image.new("RGB", imagen.size, "white")
        fondo.paste(imagen, mask=imagen.getchannel("A"))
        return fondo
    return imagen.convert("RGB")


def _es_lisa(imagen):
    """True si es casi de un solo color (toda negra, toda blanca, un relleno)."""
    variacion = ImageStat.Stat(imagen.convert("L").resize((64, 64))).stddev[0]
    return variacion < VARIACION_MINIMA


class DocumentoPDF:
    def __init__(self, archivo):
        # El PDF entero se guarda para mandárselo a Gemini (lee también imágenes y escaneos).
        self.bytes = archivo.read()
        self._lector = PdfReader(io.BytesIO(self.bytes))
        self.paginas = len(self._lector.pages)
        self.texto = "\n".join((p.extract_text() or "") for p in self._lector.pages).strip()

    def tiene_texto(self):
        """False en un PDF escaneado o de fotos: ahí el texto está dentro de las imágenes."""
        return len(self.texto) >= 100

    def candidatas(self, maximo):
        """Imágenes que podrían ir en el resumen, en el orden del PDF: las más grandes, sin
        repetir. Cada una es {"datos": JPEG completo, "miniatura": JPEG chico para Gemini}."""
        encontradas = []
        for pagina in self._lector.pages:
            try:
                imagenes_pagina = list(pagina.images)
            except Exception:
                continue
            for img in imagenes_pagina:
                # De a una: si una imagen tiene un formato raro, se salta sólo esa, no la página entera.
                try:
                    ancho, alto = img.image.size
                    if ancho < 200 or alto < 150:      # ignora íconos y logos chicos
                        continue
                    rgb = _a_rgb(img.image)
                    if _es_lisa(rgb):
                        continue
                    salida = io.BytesIO()
                    rgb.save(salida, format="JPEG", quality=85)
                    datos = salida.getvalue()
                    if any(datos == e["datos"] for e in encontradas):
                        continue
                    rgb.thumbnail((512, 512))
                    chica = io.BytesIO()
                    rgb.save(chica, format="JPEG", quality=75)
                    encontradas.append({"datos": datos, "miniatura": chica.getvalue(),
                                        "area": ancho * alto, "orden": len(encontradas)})
                except Exception:
                    continue
        mayores = sorted(encontradas, key=lambda e: e["area"], reverse=True)[:maximo]
        return sorted(mayores, key=lambda e: e["orden"])
