"""Modelo: lee el PDF original (texto, páginas e imágenes)."""
import io

from pypdf import PdfReader


class DocumentoPDF:
    def __init__(self, archivo):
        self._lector = PdfReader(archivo)
        self.paginas = len(self._lector.pages)
        self.texto = "\n".join((p.extract_text() or "") for p in self._lector.pages).strip()

    def tiene_texto(self):
        return len(self.texto) >= 100

    def imagenes(self, maximo):
        """Devuelve hasta 'maximo' imágenes grandes, sin repetir, como (bytes, pie)."""
        encontradas = []
        for pagina in self._lector.pages:
            try:
                for img in pagina.images:
                    ancho, alto = img.image.size
                    if ancho < 200 or alto < 150:      # ignora íconos y logos
                        continue
                    salida = io.BytesIO()
                    img.image.convert("RGB").save(salida, format="JPEG", quality=85)
                    datos = salida.getvalue()
                    if all(datos != e[1] for e in encontradas):
                        encontradas.append((ancho * alto, datos))
            except Exception:
                continue   # formatos de imagen raros se saltan
        encontradas.sort(key=lambda e: e[0], reverse=True)
        return [(datos, "") for _, datos in encontradas[:maximo]]
