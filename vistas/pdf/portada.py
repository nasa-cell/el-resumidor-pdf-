"""Vista PDF: dibujo de la portada y del encabezado de las demás páginas."""
from reportlab.lib.units import mm
from reportlab.lib.utils import simpleSplit
from reportlab.pdfbase import pdfmetrics

from .tema import ACENTO, ALTO, ANCHO, CUADRICULA, GRAFITO, GRIS, MARGEN, NARANJA, PAPEL, UTIL


def crear_portada(titulo, portada, resaltador):
    """Devuelve la función que dibuja la portada en la página 1."""

    def dibujar(c, doc):
        c.saveState()
        c.bookmarkPage("portada")
        c.addOutlineEntry(titulo, "portada", level=0, closed=True)
        c.setFillColor(ACENTO)
        c.rect(0, ALTO - 8 * mm, ANCHO, 8 * mm, stroke=0, fill=1)
        c.setFont("Pop-M", 11)
        c.setFillColor(ACENTO)
        c.drawString(MARGEN, ALTO - 26 * mm, "Resumen de estudio")

        y = _titulo(c, titulo, resaltador)
        _tiempo_de_lectura(c, portada, y - 14 * mm)
        _ficha_del_estudiante(c, portada)
        c.restoreState()

    return dibujar


def _titulo(c, titulo, resaltador):
    """Título limpio, sin marcador: un pequeño trazo de color como único acento."""
    tamano = 32 if len(titulo) < 60 else 25
    y = ALTO - 46 * mm
    c.setFillColor(resaltador)
    c.roundRect(MARGEN, y + tamano * 0.9, 26, 5, 2.5, stroke=0, fill=1)
    y -= 4 * mm
    for linea in simpleSplit(titulo, "Fra-B", tamano, UTIL - 10)[:4]:
        c.setFont("Fra-B", tamano)
        c.setFillColor(GRAFITO)
        c.drawString(MARGEN, y, linea)
        y -= tamano * 1.3
    return y


def _tiempo_de_lectura(c, portada, y):
    """Tiempo original tachado y tiempo nuevo en violeta, uno junto al otro."""
    c.setFont("Pop", 10)
    c.setFillColor(GRIS)
    c.drawString(MARGEN, y + 12 * mm, f"Documento original de {portada['paginas']} páginas")

    antes = f"{portada['min_original']} min"
    c.setFont("Pop-L", 26)
    c.drawString(MARGEN, y, antes)
    ancho_antes = pdfmetrics.stringWidth(antes, "Pop-L", 26)
    c.setStrokeColor(NARANJA)
    c.setLineWidth(2)
    c.line(MARGEN - 2, y + 8, MARGEN + ancho_antes + 2, y + 10)

    ahora = f"{portada['min_resumen']} min"
    x = MARGEN + ancho_antes + 14 * mm
    ancho_ahora = pdfmetrics.stringWidth(ahora, "Pop-B", 26)
    c.setFont("Pop-B", 26)
    c.setFillColor(ACENTO)
    c.drawString(x, y, ahora)
    c.setFont("Pop", 10)
    c.setFillColor(GRIS)
    c.drawString(x + ancho_ahora + 5 * mm, y + 3, "de lectura")


def _ficha_del_estudiante(c, portada):
    """Datos del estudiante en una tarjeta prolija, sin líneas de punteado."""
    filas = [("Estudiante", portada.get("estudiante")), ("Grado o curso", portada.get("curso")),
             ("Docente", portada.get("docente")), ("Autor del texto", portada.get("autor")),
             ("Nivel", portada.get("nivel")), ("Fecha", portada.get("fecha"))]
    filas = [f for f in filas if f[1]]
    if not filas:
        return
    alto_fila = 11.5 * mm
    alto_tarjeta = len(filas) * alto_fila + 8 * mm
    y0 = 22 * mm
    c.setFillColor(PAPEL)
    c.roundRect(MARGEN - 6 * mm, y0, UTIL + 12 * mm, alto_tarjeta, 5, stroke=0, fill=1)
    y = y0 + alto_tarjeta - 10 * mm
    for i, (etiqueta, valor) in enumerate(filas):
        if i:
            c.setStrokeColor(CUADRICULA)
            c.setLineWidth(0.6)
            c.line(MARGEN, y + 5 * mm, ANCHO - MARGEN, y + 5 * mm)
        c.setFont("Pop", 9)
        c.setFillColor(GRIS)
        c.drawString(MARGEN, y, etiqueta)
        c.setFont("Pop-M", 12.5)
        c.setFillColor(GRAFITO)
        c.drawString(MARGEN + 38 * mm, y, str(valor)[:55])
        y -= alto_fila


def crear_encabezado(titulo):
    """Devuelve la función que dibuja el título y el número de página en las páginas interiores."""

    def dibujar(c, doc):
        c.saveState()
        c.setFont("Pop", 8)
        c.setFillColor(GRIS)
        c.drawString(MARGEN, ALTO - 13 * mm, titulo[:80])
        c.setStrokeColor(CUADRICULA)
        c.setLineWidth(0.7)
        c.line(MARGEN, ALTO - 16 * mm, ANCHO - MARGEN, ALTO - 16 * mm)

        cx, cy, r = ANCHO / 2, 11 * mm, 4.2 * mm
        c.setFillColor(ACENTO)
        c.circle(cx, cy, r, stroke=0, fill=1)
        c.setFont("Pop-B", 9)
        c.setFillColor(PAPEL)
        c.drawCentredString(cx, cy - 3, str(doc.page))
        c.restoreState()

    return dibujar
