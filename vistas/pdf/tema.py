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
VIOLETA_OSCURO = colors.HexColor("#5931D6")
LILA = colors.HexColor("#EFE9FF")           # fondo de chips y tarjetas de dato
FONDO = colors.HexColor("#F3EEE3")          # el fondo cálido de la web
FONDO_SUAVE = colors.HexColor("#FAF7F0")    # detrás de las imágenes que no llenan su marco
PUNTEADO = colors.HexColor("#C9BFA4")
# Gráficos: colores propios de la app, siempre los mismos, sin importar el resaltador elegido.
PALETA_GRAFICOS = ["#6D42F5", "#4FC3F7", "#FF9F40", "#FF6FA5", "#2FAE66", "#F2C230", "#5931D6", "#8FDDFF"]


def color_resaltador(nombre):
    return colors.HexColor(RESALTADORES.get(nombre, RESALTADORES["amarillo"]))


# ---------- Medidas ----------
ANCHO, ALTO = A4
MARGEN = 22 * mm
UTIL = ANCHO - 2 * MARGEN
ALTO_FOTO_PORTADA = ALTO * 0.56   # la foto de la portada: todo el ancho y el 56 % del alto

# ---------- Estilos de texto ----------
# Escala: sección 20 · subtema 13 · entrada 11,5 · texto 10 · tarjetas 9,5 · pies 8.
CUERPO = ParagraphStyle("cuerpo", fontName="Pop", fontSize=10, leading=16.5,
                        textColor=GRAFITO, spaceAfter=7)
ENTRADA = ParagraphStyle("entrada", fontName="Pop", fontSize=11.5, leading=19,
                         textColor=GRAFITO, spaceAfter=8)
TARJETA = ParagraphStyle("tarjeta", fontName="Pop", fontSize=9.5, leading=14.5, textColor=GRAFITO)
NUMERO_TARJETA = ParagraphStyle("numero_tarjeta", fontName="Fra-B", fontSize=17, leading=19, textColor=ACENTO)
CIFRA = ParagraphStyle("cifra", fontName="Fra-B", fontSize=30, leading=32, textColor=ACENTO)
TITULO_GRAFICO = ParagraphStyle("titulo_grafico", fontName="Fra-B", fontSize=12.5, leading=16,
                                textColor=GRAFITO, spaceAfter=4)
CEJA = ParagraphStyle("ceja", fontName="Pop-M", fontSize=7.5, leading=10, textColor=ACENTO, spaceAfter=2)
NOTA = ParagraphStyle("nota", fontName="Pop", fontSize=7.5, leading=10, textColor=GRIS)
INDICE = ParagraphStyle("indice", fontName="Pop", fontSize=10.5, leading=14, textColor=GRAFITO)
INDICE_NUMERO = ParagraphStyle("indice_numero", fontName="Fra-B", fontSize=12, leading=14, textColor=ACENTO)
INDICE_PAGINA = ParagraphStyle("indice_pagina", fontName="Pop-M", fontSize=10.5, leading=14,
                               textColor=ACENTO, alignment=2)
LISTA = ParagraphStyle("lista", parent=CUERPO, spaceAfter=0)
SUBTITULO = ParagraphStyle("subtitulo", fontName="Fra-B", fontSize=13, leading=18,
                           textColor=GRAFITO, spaceBefore=12, spaceAfter=5)
TERMINO = ParagraphStyle("termino", fontName="Pop-B", fontSize=10, leading=14, textColor=GRAFITO)
DEFINICION = ParagraphStyle("definicion", fontName="Pop", fontSize=9.5, leading=14.5, textColor=GRAFITO)
RESPUESTA = ParagraphStyle("respuesta", parent=LISTA, fontSize=9.5, leading=14.5, textColor=GRIS)
PIE_FOTO = ParagraphStyle("pie", fontName="Pop", fontSize=8.5, leading=12, textColor=GRIS)
ETIQUETA = ParagraphStyle("etiqueta", fontName="Pop-M", fontSize=9, leading=12, textColor=ACENTO)
