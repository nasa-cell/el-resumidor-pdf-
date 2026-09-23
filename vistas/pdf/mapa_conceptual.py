"""Vista PDF: mapa conceptual."""
from reportlab.graphics.shapes import Drawing, Line, Rect, String
from reportlab.lib.units import mm
from reportlab.lib.utils import simpleSplit

from .tema import ACENTO, GRAFITO, PAPEL, UTIL


def crear_mapa(mapa, resaltador):
    ramas = [r for r in mapa.get("ramas", []) if r][:6]
    alto = 72 * mm
    dibujo = Drawing(UTIL, alto)

    cx, cy = UTIL / 2, alto / 2
    ancho_caja, alto_caja = 36 * mm, 12 * mm
    mitad = (len(ramas) + 1) // 2
    cajas = []
    for fila, y in ((ramas[:mitad], alto - alto_caja - 2 * mm), (ramas[mitad:], 2 * mm)):
        for i, texto in enumerate(fila):
            cajas.append((UTIL * (i + 0.5) / len(fila) - ancho_caja / 2, y, texto))

    for x, y, _ in cajas:   # primero las líneas, para que queden detrás
        dibujo.add(Line(cx, cy, x + ancho_caja / 2, y + alto_caja / 2,
                        strokeColor=ACENTO, strokeWidth=0.9))
    for x, y, texto in cajas:
        dibujo.add(Rect(x, y, ancho_caja, alto_caja, rx=4, ry=4, fillColor=PAPEL,
                        strokeColor=ACENTO, strokeWidth=0.9))
        _texto_centrado(dibujo, x, y, ancho_caja, alto_caja, texto, "Pop-M", 8.5)

    ancho_centro, alto_centro = 56 * mm, 16 * mm
    dibujo.add(Rect(cx - ancho_centro / 2, cy - alto_centro / 2, ancho_centro, alto_centro,
                    rx=4, ry=4, fillColor=resaltador, strokeColor=None))
    _texto_centrado(dibujo, cx - ancho_centro / 2, cy - alto_centro / 2, ancho_centro, alto_centro,
                    mapa.get("centro", ""), "Fra-B", 12)
    return dibujo


def _texto_centrado(dibujo, x, y, ancho, alto, texto, fuente, tamano):
    lineas = simpleSplit(str(texto), fuente, tamano, ancho - 8)[:2]
    y0 = y + alto / 2 + (len(lineas) - 1) * tamano * 0.62 - tamano * 0.35
    for k, linea in enumerate(lineas):
        dibujo.add(String(x + ancho / 2, y0 - k * tamano * 1.24, linea, fontName=fuente,
                          fontSize=tamano, fillColor=GRAFITO, textAnchor="middle"))
