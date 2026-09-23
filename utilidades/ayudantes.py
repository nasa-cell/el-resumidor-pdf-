"""Funciones pequeñas que se usan en varias partes."""
import re

from configuracion import PALABRAS_POR_MINUTO


def entero_en_rango(valor, minimo, maximo):
    """Convierte a número y lo limita entre mínimo y máximo."""
    try:
        return max(minimo, min(maximo, int(valor)))
    except (TypeError, ValueError):
        return minimo


def minutos_de_lectura(texto):
    return max(1, round(len(str(texto).split()) / PALABRAS_POR_MINUTO))


def nombre_seguro(nombre_archivo):
    base = nombre_archivo.rsplit(".", 1)[0]
    return "resumen_" + re.sub(r"[^\w\-]", "_", base) + ".pdf"
