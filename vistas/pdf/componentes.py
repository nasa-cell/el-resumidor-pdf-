"""Vista PDF: piezas de dibujo reutilizables (títulos numerados, tarjetas, imágenes, líneas)."""
import io
import random
from xml.sax.saxutils import escape

from reportlab.lib.utils import ImageReader, simpleSplit
from reportlab.pdfbase import pdfmetrics
from reportlab.platypus import Flowable, Paragraph, Table, TableStyle

from .tema import ACENTO, CUADRICULA, FONDO_SUAVE, GRAFITO, PAPEL


def parrafo(texto, estilo):
    return Paragraph(escape(str(texto)), estilo)


def trazo_resaltador(c, x, y, ancho, alto, color, semilla=0):
    """Dibuja un trazo de resaltador con bordes un poco irregulares."""
    r = random.Random(semilla)
    mover = lambda: r.uniform(-1.2, 1.2)
    c.saveState()
    c.setFillColor(color, alpha=0.9)
    p = c.beginPath()
    p.moveTo(x + mover(), y + mover())
    p.lineTo(x + ancho * 0.5, y + mover() * 0.6)
    p.lineTo(x + ancho + r.uniform(0, 3), y + mover())
    p.lineTo(x + ancho + r.uniform(-2, 1), y + alto + mover())
    p.lineTo(x + ancho * 0.5, y + alto + mover() * 0.6)
    p.lineTo(x + r.uniform(-2, 1), y + alto + mover())
    p.close()
    c.drawPath(p, stroke=0, fill=1)
    c.restoreState()


class Marcador(Flowable):
    """Flowable invisible: agrega una entrada al índice/marcadores del PDF."""

    def __init__(self, titulo, clave, nivel=0):
        super().__init__()
        self.titulo, self.clave, self.nivel = titulo, clave, nivel

    def wrap(self, *args):
        return 0, 0

    def draw(self):
        self.canv.bookmarkPage(self.clave)
        self.canv.addOutlineEntry(self.titulo, self.clave, level=self.nivel, closed=True)


class TituloSeccion(Flowable):
    """Número grande calado en violeta («03») y el título de la sección en Fraunces.

    También deja la entrada en los marcadores del PDF; el documento lo usa para el índice
    y para el nombre de la sección en el encabezado de cada página.
    """
    TAM_NUMERO, TAM_TITULO = 34, 20

    def __init__(self, numero, texto, clave):
        super().__init__()
        self.numero, self.texto, self.clave = numero, str(texto), clave

    def wrap(self, ancho, alto):
        self.ancho_numero = pdfmetrics.stringWidth(f"{self.numero:02d}", "Fra-B", self.TAM_NUMERO) + 12
        self.lineas = simpleSplit(self.texto, "Fra-B", self.TAM_TITULO, ancho - self.ancho_numero) or [""]
        self.alto = max(self.TAM_NUMERO, len(self.lineas) * self.TAM_TITULO * 1.18) + 12
        return ancho, self.alto

    def draw(self):
        c = self.canv
        c.bookmarkPage(self.clave)
        c.addOutlineEntry(self.texto, self.clave, level=0, closed=True)
        base = self.alto - self.TAM_NUMERO * 0.82 - 4
        # El modo «solo contorno» queda activo hasta restaurar el estado: por eso va aparte del título.
        c.saveState()
        c.setStrokeColor(ACENTO)
        c.setLineWidth(0.9)
        numero = c.beginText(0, base)
        numero.setTextRenderMode(1)       # solo el contorno: número «calado»
        numero.setFont("Fra-B", self.TAM_NUMERO)
        numero.textOut(f"{self.numero:02d}")
        c.drawText(numero)
        c.restoreState()
        # El título se centra en la altura del número si es de una línea.
        c.saveState()
        c.setFillColor(GRAFITO)
        c.setFont("Fra-B", self.TAM_TITULO)
        y = base + (self.TAM_NUMERO - self.TAM_TITULO) * 0.28 + (len(self.lineas) - 1) * self.TAM_TITULO * 1.18
        for linea in self.lineas:
            c.drawString(self.ancho_numero, y, linea)
            y -= self.TAM_TITULO * 1.18
        c.restoreState()


class Tarjeta(Flowable):
    """Bloque con fondo y esquinas redondeadas que contiene párrafos u otras piezas."""

    def __init__(self, contenido, fondo=PAPEL, borde=None, relleno=10, radio=7, separacion=4, alto_minimo=0):
        super().__init__()
        self.contenido, self.fondo, self.borde = contenido, fondo, borde
        self.relleno, self.radio, self.separacion, self.alto_minimo = relleno, radio, separacion, alto_minimo

    def wrap(self, ancho, alto):
        interior = ancho - 2 * self.relleno
        self.altos = [f.wrap(interior, alto)[1] for f in self.contenido]
        natural = sum(self.altos) + self.separacion * (len(self.altos) - 1) + 2 * self.relleno
        self.ancho, self.alto = ancho, max(natural, self.alto_minimo)
        return ancho, self.alto

    def draw(self):
        c = self.canv
        c.saveState()
        c.setFillColor(self.fondo)
        if self.borde is not None:
            c.setStrokeColor(self.borde)
            c.setLineWidth(0.9)
        c.roundRect(0, 0, self.ancho, self.alto, self.radio, stroke=1 if self.borde is not None else 0, fill=1)
        c.restoreState()
        y = self.alto - self.relleno
        for pieza, alto in zip(self.contenido, self.altos):
            y -= alto
            pieza.drawOn(c, self.relleno, y)
            y -= self.separacion


def fila_de_tarjetas(tarjetas, columnas, ancho_total, espacio=8):
    """Reparte las tarjetas en filas de 'columnas', todas del mismo alto dentro de cada fila."""
    ancho = (ancho_total - espacio * (columnas - 1)) / columnas
    filas = []
    for i in range(0, len(tarjetas), columnas):
        grupo = tarjetas[i:i + columnas]
        alto = max(t.wrap(ancho, 10000)[1] for t in grupo)
        for t in grupo:
            t.alto_minimo = alto
        celdas = []
        for k in range(columnas):
            if k:
                celdas.append("")
            celdas.append(grupo[k] if k < len(grupo) else "")
        filas.append(celdas)
    anchos = []
    for k in range(columnas):
        if k:
            anchos.append(espacio)
        anchos.append(ancho)
    tabla = Table(filas, colWidths=anchos)
    tabla.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                               ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                               ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), espacio)]))
    return tabla


class ImagenEnMarco(Flowable):
    """Imagen entera (sin recortar) dentro de un marco de esquinas redondeadas y borde fino."""

    def __init__(self, datos, ancho, alto):
        super().__init__()
        self.datos, self.ancho, self.alto = datos, ancho, alto

    def wrap(self, *args):
        return self.ancho, self.alto

    def draw(self):
        c = self.canv
        lector = ImageReader(io.BytesIO(self.datos))
        ancho_px, alto_px = lector.getSize()
        escala = min(self.ancho / ancho_px, self.alto / alto_px)
        w, h = ancho_px * escala, alto_px * escala
        c.saveState()
        camino = c.beginPath()
        camino.roundRect(0, 0, self.ancho, self.alto, 8)
        c.clipPath(camino, stroke=0, fill=0)
        c.setFillColor(FONDO_SUAVE)
        c.rect(0, 0, self.ancho, self.alto, stroke=0, fill=1)
        c.drawImage(lector, (self.ancho - w) / 2, (self.alto - h) / 2, w, h, mask="auto")
        c.restoreState()
        c.saveState()
        c.setStrokeColor(CUADRICULA)
        c.setLineWidth(0.8)
        c.roundRect(0, 0, self.ancho, self.alto, 8, stroke=1, fill=0)
        c.restoreState()


class LineasParaEscribir(Flowable):
    """Renglones negros para responder a mano (bien visibles, también impresos en blanco y negro).
    Con 'llenar', ocupan el resto de la hoja."""

    def __init__(self, cantidad=2, separacion=17, llenar=False):
        super().__init__()
        self.cantidad, self.separacion, self.llenar = cantidad, separacion, llenar

    def wrap(self, ancho, alto):
        if self.llenar:
            self.cantidad = max(4, int((alto - 6) // self.separacion))
        self.ancho = ancho
        return ancho, self.cantidad * self.separacion

    def draw(self):
        c = self.canv
        c.saveState()
        c.setStrokeColor(GRAFITO)
        c.setLineWidth(0.6)
        for i in range(self.cantidad):
            y = i * self.separacion + 2
            c.line(0, y, self.ancho, y)
        c.restoreState()


class ChipNumero(Flowable):
    """Círculo de color con un número adentro, como los pasos de la web."""

    def __init__(self, numero, color, diametro=16):
        super().__init__()
        self.numero, self.color, self.diametro = str(numero), color, diametro

    def wrap(self, *args):
        return self.diametro, self.diametro

    def draw(self):
        c, d = self.canv, self.diametro
        c.saveState()
        c.setFillColor(self.color)
        c.circle(d / 2, d / 2, d / 2, stroke=0, fill=1)
        c.setFont("Pop-B", d * 0.42)
        c.setFillColor(GRAFITO)
        c.drawCentredString(d / 2, d / 2 - d * 0.15, self.numero)
        c.restoreState()
