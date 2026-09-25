"""Vista PDF: la portada («foto a sangre») y el encabezado y pie de las demás páginas."""
import io

from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader, simpleSplit
from reportlab.pdfbase import pdfmetrics

from .tema import (ACENTO, ALTO, ALTO_FOTO_PORTADA, ANCHO, CUADRICULA, GRAFITO, GRIS, LILA, MARGEN, NARANJA,
                   PAPEL, UTIL, VIOLETA_OSCURO)


def dibujar_portada(c, titulo, portada, resaltador, imagen=None):
    """Foto arriba de borde a borde, título blanco sobre la foto y los datos debajo."""
    c.saveState()
    c.bookmarkPage("portada")
    c.addOutlineEntry(titulo, "portada", level=0, closed=True)
    y_foto = ALTO - ALTO_FOTO_PORTADA
    if imagen:
        c.drawImage(ImageReader(io.BytesIO(imagen)), 0, y_foto, ANCHO, ALTO_FOTO_PORTADA)
        _velo(c, y_foto)
    else:
        _fondo_sin_foto(c, y_foto, resaltador)
    _etiqueta(c)
    _titulo(c, titulo, y_foto, resaltador)
    y = _chips(c, portada, y_foto - 13 * mm)
    y = _tiempo_de_lectura(c, portada, y - 15 * mm)
    _ficha(c, portada, y - 11 * mm)
    c.restoreState()


def _fondo_sin_foto(c, y_foto, resaltador):
    """Sin imagen: el mismo espacio en violeta con círculos del color del resaltador."""
    c.setFillColor(ACENTO)
    c.rect(0, y_foto, ANCHO, ALTO_FOTO_PORTADA, stroke=0, fill=1)
    c.saveState()
    camino = c.beginPath()
    camino.rect(0, y_foto, ANCHO, ALTO_FOTO_PORTADA)
    c.clipPath(camino, stroke=0, fill=0)
    c.setFillColor(resaltador)
    c.circle(ANCHO - 38 * mm, ALTO - 55 * mm, 58 * mm, stroke=0, fill=1)
    c.setFillColor(VIOLETA_OSCURO)
    c.circle(ANCHO - 95 * mm, ALTO - 20 * mm, 30 * mm, stroke=0, fill=1)
    c.setFillColor(PAPEL, alpha=0.18)
    for fila in range(6):
        for col in range(8):
            c.circle(MARGEN + col * 7 * mm, ALTO - 30 * mm - fila * 7 * mm, 0.8 * mm, stroke=0, fill=1)
    c.restoreState()


def _velo(c, y_foto):
    """Degradado violeta suave al pie de la foto: une la foto con el resto de la portada."""
    alto = ALTO_FOTO_PORTADA * 0.35
    franjas = 50
    for i in range(franjas):
        opacidad = 0.55 * (1 - i / franjas) ** 1.6
        c.setFillColor(VIOLETA_OSCURO, alpha=opacidad)
        c.rect(0, y_foto + i * alto / franjas, ANCHO, alto / franjas + 0.6, stroke=0, fill=1)


def _etiqueta(c):
    texto = "Resumen de estudio"
    ancho = pdfmetrics.stringWidth(texto, "Pop-M", 9) + 9 * mm
    y = ALTO - 20 * mm
    c.setFillColor(PAPEL)
    c.roundRect(MARGEN, y, ancho, 7.5 * mm, 3.75 * mm, stroke=0, fill=1)
    c.setFillColor(ACENTO)
    c.setFont("Pop-M", 9)
    c.drawString(MARGEN + 4.5 * mm, y + 2.5 * mm, texto)


def _titulo(c, titulo, y_foto, resaltador):
    """Título en Fraunces blanca, desde abajo de la foto hacia arriba; la última palabra subrayada."""
    tamano = 36 if len(titulo) <= 40 else 29 if len(titulo) <= 80 else 23
    lineas = simpleSplit(titulo, "Fra-B", tamano, UTIL)
    if len(lineas) > 4:
        lineas = lineas[:4]
        lineas[-1] = lineas[-1].rstrip(" .,;:") + "…"
    interlinea = tamano * 1.08
    y = y_foto + 13 * mm
    # Rectángulo violeta detrás del título: se lee igual sobre fotos claras, oscuras o muy cargadas.
    relleno = 5 * mm
    ancho_caja = max(pdfmetrics.stringWidth(l, "Fra-B", tamano) for l in lineas) + 2 * relleno
    alto_caja = interlinea * (len(lineas) - 1) + tamano * 0.95 + 2 * relleno + tamano * 0.1
    c.setFillColor(VIOLETA_OSCURO, alpha=0.9)
    c.roundRect(MARGEN - relleno, y - tamano * 0.25 - relleno, ancho_caja, alto_caja, 3 * mm, stroke=0, fill=1)
    ultima = lineas[-1]
    palabra = ultima.split(" ")[-1]
    x_palabra = MARGEN + pdfmetrics.stringWidth(ultima[: len(ultima) - len(palabra)], "Fra-B", tamano)
    c.setFillColor(resaltador)
    c.roundRect(x_palabra, y - tamano * 0.2, pdfmetrics.stringWidth(palabra, "Fra-B", tamano), tamano * 0.14,
                tamano * 0.07, stroke=0, fill=1)
    c.setFillColor(PAPEL)
    c.setFont("Fra-B", tamano)
    for linea in reversed(lineas):
        c.drawString(MARGEN, y, linea)
        y += interlinea


def _chips(c, portada, y):
    """Nivel, largo del documento y fecha en píldoras lilas. Devuelve la y de abajo."""
    textos = [portada.get("nivel"), f"Documento de {portada.get('paginas')} páginas", portada.get("fecha")]
    x = MARGEN
    c.setFont("Pop-M", 8.5)
    for texto in (t for t in textos if t):
        ancho = pdfmetrics.stringWidth(texto, "Pop-M", 8.5) + 7 * mm
        c.setFillColor(LILA)
        c.roundRect(x, y, ancho, 6.6 * mm, 3.3 * mm, stroke=0, fill=1)
        c.setFillColor(VIOLETA_OSCURO)
        c.drawString(x + 3.5 * mm, y + 2.2 * mm, texto)
        x += ancho + 2.5 * mm
    return y


def _tiempo_de_lectura(c, portada, y):
    """Tiempo original tachado en naranja y el nuevo en violeta."""
    antes = f"{portada['min_original']} min"
    c.setFillColor(GRIS)
    c.setFont("Pop-L", 24)
    c.drawString(MARGEN, y, antes)
    ancho_antes = pdfmetrics.stringWidth(antes, "Pop-L", 24)
    c.setStrokeColor(NARANJA)
    c.setLineWidth(2)
    c.line(MARGEN - 2, y + 7, MARGEN + ancho_antes + 2, y + 9)

    ahora = f"{portada['min_resumen']} min"
    x = MARGEN + ancho_antes + 10 * mm
    c.setFont("Pop-B", 30)
    c.setFillColor(ACENTO)
    c.drawString(x, y, ahora)
    c.setFont("Pop", 10)
    c.setFillColor(GRIS)
    c.drawString(x + pdfmetrics.stringWidth(ahora, "Pop-B", 30) + 4 * mm, y + 3, "de lectura")
    return y


def _ficha(c, portada, y_arriba):
    """Datos del estudiante en dos columnas, sin cajas: etiqueta gris y dato en tinta."""
    filas = [("Estudiante", portada.get("estudiante")), ("Grado o curso", portada.get("curso")),
             ("Docente", portada.get("docente")), ("Autor del texto", portada.get("autor"))]
    filas = [f for f in filas if f[1]]
    if not filas:
        return
    c.setStrokeColor(CUADRICULA)
    c.setLineWidth(0.8)
    c.line(MARGEN, y_arriba, ANCHO - MARGEN, y_arriba)
    ancho_col = UTIL / 2
    for i, (etiqueta, valor) in enumerate(filas):
        x = MARGEN + (i % 2) * ancho_col
        y = y_arriba - 9 * mm - (i // 2) * 14 * mm
        c.setFont("Pop", 8)
        c.setFillColor(GRIS)
        c.drawString(x, y + 5 * mm, etiqueta)
        c.setFont("Pop-M", 11.5)
        c.setFillColor(GRAFITO)
        texto = simpleSplit(str(valor), "Pop-M", 11.5, ancho_col - 6 * mm)[0]
        c.drawString(x, y, texto)


def dibujar_encabezado_y_pie(c, titulo, seccion, pagina, total, nivel):
    """Arriba: título del resumen y la sección de la página. Abajo: nivel, avance y «3 / 7»."""
    c.saveState()
    y = ALTO - 13 * mm
    c.setFillColor(ACENTO)
    c.roundRect(MARGEN, y - 0.2 * mm, 2.4 * mm, 2.4 * mm, 0.5 * mm, stroke=0, fill=1)
    c.setFont("Pop", 8)
    c.setFillColor(GRIS)
    derecha = f"{seccion.numero} · {seccion.texto}" if seccion else ""
    ancho_derecha = pdfmetrics.stringWidth(derecha, "Pop", 8)
    espacio = UTIL - 5 * mm - ancho_derecha - 10 * mm
    texto_titulo = simpleSplit(titulo, "Pop", 8, espacio)[0] if titulo else ""
    c.drawString(MARGEN + 4.5 * mm, y, texto_titulo)
    c.drawRightString(ANCHO - MARGEN, y, derecha)
    c.setStrokeColor(CUADRICULA)
    c.setLineWidth(0.7)
    c.line(MARGEN, y - 3 * mm, ANCHO - MARGEN, y - 3 * mm)

    y = 12 * mm
    c.setFont("Pop", 7.5)
    c.drawString(MARGEN, y, f"Resumen de estudio · {nivel}" if nivel else "Resumen de estudio")
    c.setFont("Pop-B", 9)
    c.setFillColor(GRAFITO)
    numero = f"{pagina} / {total}" if total else str(pagina)
    c.drawRightString(ANCHO - MARGEN, y, numero)
    if total:
        _avance(c, pagina, total, ANCHO - MARGEN - pdfmetrics.stringWidth(numero, "Pop-B", 9) - 6 * mm, y + 1)
    c.restoreState()


def _avance(c, pagina, total, x_derecha, y):
    """Barra de avance: un tramo por página (o una barra continua si son muchas)."""
    ancho_total = 34 * mm
    x = x_derecha - ancho_total
    if total <= 14:
        hueco = 1.2 * mm
        tramo = (ancho_total - hueco * (total - 1)) / total
        for i in range(total):
            c.setFillColor(ACENTO if i < pagina else CUADRICULA)
            c.roundRect(x + i * (tramo + hueco), y, tramo, 1.3 * mm, 0.65 * mm, stroke=0, fill=1)
    else:
        c.setFillColor(CUADRICULA)
        c.roundRect(x, y, ancho_total, 1.3 * mm, 0.65 * mm, stroke=0, fill=1)
        c.setFillColor(ACENTO)
        c.roundRect(x, y, ancho_total * pagina / total, 1.3 * mm, 0.65 * mm, stroke=0, fill=1)
