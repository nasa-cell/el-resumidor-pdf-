"""Vista PDF: gráficos de barras o dona con matplotlib.

Tienen colores propios (los de la app, siempre los mismos), no el resaltador elegido. El
título, el número y la fuente se escriben en el PDF, no dentro de la imagen.
"""
import io
import os
import re

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from reportlab.platypus import Image

from .tema import CARPETA_FUENTES, PALETA_GRAFICOS

for _archivo in ("Poppins-Regular.ttf", "Poppins-Medium.ttf", "Poppins-Bold.ttf"):
    font_manager.fontManager.addfont(os.path.join(CARPETA_FUENTES, _archivo))

GRAFITO_HEX, GRIS_HEX, CUADRICULA_HEX = "#17151F", "#6B6675", "#EDE6D8"


def _numero(valor):
    """1234.5 → «1.234,5»; 12.0 → «12»."""
    texto = f"{valor:,.1f}" if abs(valor - round(valor)) > 1e-9 else f"{round(valor):,}"
    return texto.replace(",", "#").replace(".", ",").replace("#", ".")


def _son_periodos(etiquetas):
    """Años o períodos (2021, 2022…): van en columnas y en su orden, no ordenados por tamaño."""
    return all(re.fullmatch(r"\s*(1[5-9]|20)\d{2}\s*", str(e)) for e in etiquetas)


def crear_grafico(datos, ancho):
    """Devuelve la imagen del gráfico lista para el PDF, o None si los datos no sirven."""
    etiquetas, valores = datos.get("etiquetas") or [], datos.get("valores") or []
    try:
        valores = [float(v) for v in valores]
    except (TypeError, ValueError):
        return None
    etiquetas = [str(e) for e in etiquetas]
    if not etiquetas or len(etiquetas) != len(valores) or len(valores) > 12:
        return None

    plt.rcParams["font.family"] = "Poppins"
    if datos.get("tipo") == "torta" and all(v >= 0 for v in valores) and sum(valores) > 0 and len(valores) <= 6:
        figura = _dona(etiquetas, valores)
    elif _son_periodos(etiquetas):
        figura = _columnas(etiquetas, valores)
    else:
        figura = _barras(etiquetas, valores)
    ancho_in, alto_in = figura.get_size_inches()
    salida = io.BytesIO()
    figura.savefig(salida, format="png", dpi=200, transparent=True)
    plt.close(figura)
    salida.seek(0)
    return Image(salida, width=ancho, height=ancho * alto_in / ancho_in)


def _limpiar(ejes):
    for lado in ("top", "right", "left", "bottom"):
        ejes.spines[lado].set_visible(False)
    ejes.tick_params(length=0, colors=GRAFITO_HEX, labelsize=9)


def _barras(etiquetas, valores):
    """Barras horizontales de mayor a menor, cada una de un color, con su valor al final."""
    pares = sorted(zip(etiquetas, valores), key=lambda p: p[1])
    figura, ejes = plt.subplots(figsize=(7, max(1.7, 0.5 * len(pares) + 0.5)))
    colores = [PALETA_GRAFICOS[i % len(PALETA_GRAFICOS)] for i in range(len(pares))][::-1]
    barras = ejes.barh([p[0] for p in pares], [p[1] for p in pares], color=colores, height=0.62)
    tope = max(abs(v) for v in valores) or 1
    for barra, (_, valor) in zip(barras, pares):
        ejes.text(barra.get_width() + tope * 0.015, barra.get_y() + barra.get_height() / 2, _numero(valor),
                  va="center", fontsize=9.5, fontweight="bold", color=GRAFITO_HEX)
    ejes.set_xlim(min(0, min(valores)), tope * 1.15)
    ejes.set_xticks([])
    _limpiar(ejes)
    figura.tight_layout()
    return figura


def _columnas(etiquetas, valores):
    """Columnas para años o períodos, en orden; la más alta en violeta y el resto en celeste."""
    figura, ejes = plt.subplots(figsize=(7, 3))
    mayor = max(range(len(valores)), key=lambda i: valores[i])
    colores = [PALETA_GRAFICOS[0] if i == mayor else PALETA_GRAFICOS[1] for i in range(len(valores))]
    barras = ejes.bar(etiquetas, valores, color=colores, width=0.58)
    ejes.bar_label(barras, labels=[_numero(v) for v in valores], fontsize=9.5, fontweight="bold",
                   color=GRAFITO_HEX, padding=3)
    ejes.set_yticks([])
    ejes.axhline(0, color=CUADRICULA_HEX, linewidth=1.2)
    ejes.set_ylim(min(0, min(valores)), (max(valores) or 1) * 1.18)
    _limpiar(ejes)
    figura.tight_layout()
    return figura


def _dona(etiquetas, valores):
    """Dona con el porcentaje más grande en el centro y la leyenda al costado."""
    figura, ejes = plt.subplots(figsize=(7, 2.9))
    total = sum(valores)
    colores = PALETA_GRAFICOS[:len(valores)]
    porciones, _ = ejes.pie(valores, startangle=90, counterclock=False, colors=colores,
                            wedgeprops={"width": 0.36, "edgecolor": "white", "linewidth": 2})
    mayor = max(range(len(valores)), key=lambda i: valores[i])
    ejes.text(0, 0.1, f"{_numero(valores[mayor] / total * 100)} %", ha="center", va="center",
              fontsize=17, fontweight="bold", color=GRAFITO_HEX)
    ejes.text(0, -0.22, etiquetas[mayor][:18], ha="center", va="center", fontsize=8, color=GRIS_HEX)
    leyenda = [f"{e}   {_numero(v / total * 100)} %" for e, v in zip(etiquetas, valores)]
    ejes.legend(porciones, leyenda, loc="center left", bbox_to_anchor=(1.05, 0.5), frameon=False,
                fontsize=9.5, labelcolor=GRAFITO_HEX, handlelength=1, handleheight=1)
    ejes.axis("equal")
    figura.tight_layout()
    return figura
