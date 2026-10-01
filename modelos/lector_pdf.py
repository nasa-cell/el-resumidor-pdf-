"""Modelo: lee el PDF original (bytes, texto, páginas e imágenes)."""
import collections
import io
import re
import unicodedata

from PIL import Image, ImageStat
from pypdf import PdfReader

# Una imagen casi de un solo color (fondo, mancha, capa de relleno) no sirve para el resumen.
VARIACION_MINIMA = 8
# Secciones que no son contenido: no hace falta que estén en el resumen.
SECCIONES_SIN_CONTENIDO = {"notas", "referencias", "vease tambien", "enlaces externos", "bibliografia",
                           "fuentes", "indice", "contenido", "contenidos", "tabla de contenidos", "notas y referencias"}


def _sin_tildes(texto):
    texto = unicodedata.normalize("NFKD", texto.lower())
    return "".join(c for c in texto if not unicodedata.combining(c))


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

    def titulos(self, maximo=45):
        """Títulos y subtítulos del documento, en orden, reconocidos porque su letra es más grande
        que la del texto normal. Sirven para comprobar que el resumen no deja afuera ninguna
        sección. En un PDF escaneado (sin texto) devuelve una lista vacía."""
        trozos = []
        try:
            for numero, pagina in enumerate(self._lector.pages):
                def visitar(texto, cm, tm, fuente, tamano, numero=numero):
                    texto = " ".join(str(texto).split())
                    if texto and tamano:
                        escala = (tm[0] ** 2 + tm[1] ** 2) ** 0.5 if tm else 1
                        trozos.append((round(float(tamano) * (escala or 1), 1), texto, numero))
                pagina.extract_text(visitor_text=visitar)
        except Exception:
            return []
        conteo = collections.Counter()
        for tamano, texto, _ in trozos:
            conteo[tamano] += len(texto)
        if not conteo:
            return []
        cuerpo = conteo.most_common(1)[0][0]
        # Un pedazo que sigue la frase del anterior (mismo tamaño y página, empieza en minúscula) es
        # parte del mismo título: «Artbooks» + «y guías». Si empieza en mayúscula es otro título.
        unidos = []
        for tamano, texto, numero in trozos:
            if tamano < cuerpo * 1.12:
                unidos.append(None)
                continue
            if unidos and unidos[-1] and unidos[-1][0] == tamano and unidos[-1][2] == numero and texto[:1].islower():
                unidos[-1] = (tamano, unidos[-1][1] + " " + texto, numero)
            else:
                unidos.append((tamano, texto, numero))
        candidatos = [u for u in unidos if u and 3 <= len(u[1]) <= 90 and re.search(r"[A-Za-zÁÉÍÓÚÑáéíóúñ]{3}", u[1])]
        if not candidatos:
            return []
        mayor = max(t for t, _, _ in candidatos)
        titulos, vistos = [], set()
        for tamano, texto, _ in candidatos:
            clave = _sin_tildes(texto).strip(" .:")
            if tamano == mayor and not titulos and not vistos:   # el título del documento entero
                vistos.add(clave)
                continue
            if clave in vistos or clave in SECCIONES_SIN_CONTENIDO:
                continue
            vistos.add(clave)
            titulos.append(texto.strip(" .:"))
        return titulos[:maximo]

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
