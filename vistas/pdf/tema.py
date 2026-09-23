"""Vista PDF: fuentes, colores, medidas y estilos de texto."""
import os

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

CARPETA_FUENTES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fuentes")

# ---------- Fuentes ----------
for nombre, archivo in [("Pop", "Poppins-Regular.ttf"), ("Pop-M", "Poppins-Medium.ttf"),
                        ("Pop-B", "Poppins-Bold.ttf"), ("Pop-L", "Poppins-Light.ttf"),
                        ("Fra-B", "Fraunces-Bold.ttf")]:
    pdfmetrics.registerFont(TTFont(nombre, os.path.join(CARPETA_FUENTES, archivo)))
pdfmetrics.registerFontFamily("Pop", normal="Pop", bold="Pop-B", italic="Pop", boldItalic="Pop-B")

# ---------- Colores: mismo sistema de la web (violeta + resaltadores) ----------
GRAFITO = colors.HexColor("#17151F")      # tinta
ACENTO = colors.HexColor("#6D42F5")       # violeta de marca
PAPEL = colors.HexColor("#FFFFFF")
GRIS = colors.HexColor("#6B6675")
CUADRICULA = colors.HexColor("#EDE6D8")
RESALTADORES = {
    "amarillo": "#FFE45C", "verde": "#9BF0A8", "rosa": "#FFA8D4",
    "celeste": "#8FDDFF", "naranja": "#FFC46B",
}
COLORES_ACENTO = [colors.HexColor(h) for h in ("#FFE45C", "#4FC3F7", "#FF9F40", "#FF6FA5")]   # para numerar
NARANJA = colors.HexColor("#FF9F40")


def color_resaltador(nombre):
    return colors.HexColor(RESALTADORES.get(nombre, RESALTADORES["amarillo"]))


# ---------- Medidas ----------
ANCHO, ALTO = A4
MARGEN = 22 * mm
UTIL = ANCHO - 2 * MARGEN

# ---------- Estilos de texto ----------
CUERPO = ParagraphStyle("cuerpo", fontName="Pop", fontSize=10, leading=16.5,
                        textColor=GRAFITO, spaceAfter=7)
LISTA = ParagraphStyle("lista", parent=CUERPO, spaceAfter=0)
SUBTITULO = ParagraphStyle("subtitulo", fontName="Pop-B", fontSize=12.5, leading=17,
                           textColor=GRAFITO, spaceBefore=10, spaceAfter=5)
TITULO_SECCION = ParagraphStyle("titulo_seccion", fontName="Pop-B", fontSize=16.5, leading=20,
                                textColor=ACENTO, spaceBefore=4, spaceAfter=10)
TERMINO = ParagraphStyle("termino", fontName="Pop-B", fontSize=10.5, leading=15, textColor=ACENTO)
DEFINICION = ParagraphStyle("definicion", fontName="Pop", fontSize=9.5, leading=14.5, textColor=GRAFITO)
RESPUESTA = ParagraphStyle("respuesta", parent=LISTA, fontSize=9.5, leading=14.5, textColor=GRIS)
PIE_FOTO = ParagraphStyle("pie", fontName="Pop", fontSize=8.5, leading=12, textColor=GRIS)
ETIQUETA = ParagraphStyle("etiqueta", fontName="Pop-M", fontSize=9, leading=12, textColor=ACENTO)
