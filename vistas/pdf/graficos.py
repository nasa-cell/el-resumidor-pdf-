"""Vista PDF: gráficos de barras o torta con matplotlib."""
import io
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from reportlab.platypus import Image

from .tema import CARPETA_FUENTES, RESALTADORES, UTIL

for _archivo in ("Poppins-Regular.ttf", "Poppins-Bold.ttf"):
    font_manager.fontManager.addfont(os.path.join(CARPETA_FUENTES, _archivo))

GRAFITO_HEX, ACENTO_HEX, GRIS_HEX = "#17151F", "#6D42F5", "#6B6675"


def crear_grafico(datos, nombre_color):
    """Devuelve una imagen del gráfico o None si los datos no sirven."""
    etiquetas, valores = datos.get("etiquetas") or [], datos.get("valores") or []
    try:
        valores = [float(v) for v in valores]
    except (TypeError, ValueError):
        return None
    if not etiquetas or len(etiquetas) != len(valores):
        return None

    color = RESALTADORES.get(nombre_color, RESALTADORES["amarillo"])
    plt.rcParams["font.family"] = "Poppins"
    figura, ejes = plt.subplots(figsize=(7, 3.3), dpi=160)
    if datos.get("tipo") == "torta" and all(v >= 0 for v in valores):
        _torta(ejes, etiquetas, valores, color)
    else:
        _barras(ejes, etiquetas, valores, color)
    ejes.set_title(datos.get("titulo", ""), fontsize=10, color=GRIS_HEX, loc="left")
    figura.tight_layout()

    salida = io.BytesIO()
    figura.savefig(salida, format="png")
    plt.close(figura)
    salida.seek(0)
    return Image(salida, width=UTIL, height=UTIL * 3.3 / 7)


def _torta(ejes, etiquetas, valores, color):
    tonos = [color, ACENTO_HEX, "#F2ECDD", "#C9BFA4", "#E4D8BD", GRAFITO_HEX]
    total = sum(valores) or 1
    porciones, _ = ejes.pie(valores, startangle=90, colors=tonos[:len(valores)],
                            wedgeprops={"linewidth": 1.2, "edgecolor": GRAFITO_HEX})
    # leyenda al costado: así las porciones pequeñas no se amontonan
    leyenda = [f"{e}  {v / total * 100:.1f}%".replace(".", ",") for e, v in zip(etiquetas, valores)]
    ejes.legend(porciones, leyenda, loc="center left", bbox_to_anchor=(1.0, 0.5),
                frameon=False, fontsize=9, labelcolor=GRAFITO_HEX)
    ejes.axis("equal")


def _barras(ejes, etiquetas, valores, color):
    barras = ejes.bar(etiquetas, valores, color=color, edgecolor=GRAFITO_HEX, linewidth=1.1, width=0.55)
    ejes.bar_label(barras, fontsize=9, color=ACENTO_HEX, fontweight="bold", padding=3)
    for lado in ("top", "right", "left"):
        ejes.spines[lado].set_visible(False)
    ejes.spines["bottom"].set_color(GRAFITO_HEX)
    ejes.set_yticks([])
    ejes.tick_params(labelsize=8.5, colors=GRAFITO_HEX, length=0)
    if len(etiquetas) > 4:
        ejes.tick_params(axis="x", labelrotation=12)
