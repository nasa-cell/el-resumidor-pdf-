"""Vista PDF: piezas de dibujo reutilizables (resaltador, viñeta, chip de número)."""
import random
from xml.sax.saxutils import escape

from reportlab.platypus import Flowable, Paragraph

from .tema import GRAFITO


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


class Vineta(Flowable):
    """Pequeño trazo de resaltador que sirve de viñeta."""

    def __init__(self, color):
        super().__init__()
        self.color = color

    def wrap(self, *args):
        return 9, 12

    def draw(self):
        trazo_resaltador(self.canv, 0, 3.2, 7, 5.5, self.color, 7)


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
