"""Modelo: crea imágenes con IA usando Pollinations (gratis).

Con clave (enter.pollinations.ai) se usan modelos de primera con los créditos gratis del día:
MAI Image 2.6 (fotos realistas muy detalladas) para secundaria y adultos, y FLUX 1.1 Pro
(ilustración colorida) para niños. Si un modelo falla o se acabaron los créditos gratis, se pasa
solo al siguiente, hasta el flux básico. Nunca se compra nada: sin créditos, simplemente no se usa.
"""
import io
import time
import urllib.parse

import requests
from PIL import Image

from configuracion import POLLINATIONS_KEY

URL_CON_CLAVE = "https://gen.pollinations.ai/image/{}"
URL_SIN_CLAVE = "https://image.pollinations.ai/prompt/{}"
MODELOS = {
    "ninos": ["black-forest-labs/flux.1.1-pro", "flux"],
    "secundaria": ["microsoft/mai-image-2.6", "black-forest-labs/flux.1.1-pro", "flux"],
    "adultos": ["microsoft/mai-image-2.6", "black-forest-labs/flux.1.1-pro", "flux"],
}
# El estilo va según la edad (antes era siempre «ilustración plana», y salían muy simples).
ESTILOS = {
    "ninos": "vibrant children's storybook illustration, painterly textures, friendly expressive characters, "
             "rich colorful details, warm soft lighting",
    "secundaria": "highly detailed digital illustration, semi-realistic, rich colors, depth of field, "
                  "natural cinematic lighting, detailed environment",
    "adultos": "photorealistic editorial photograph, natural light, sharp focus, 35mm lens, high detail",
}
# Los modelos tienden a escribir carteles: se pide que todas las superficies queden sin letras.
SIN_TEXTO = ("all objects and surfaces are blank with no labels, signs, logos or writing, "
             "no text, no letters, no words, no watermark")


def _pedir(url, modelo, semilla, con_clave):
    params = {"model": modelo, "width": 1280, "height": 800, "seed": semilla, "nologo": "true"}
    headers = {"Authorization": f"Bearer {POLLINATIONS_KEY}"} if con_clave else {}
    r = requests.get(url, params=params, headers=headers, timeout=180)
    r.raise_for_status()
    if "image" not in r.headers.get("content-type", ""):
        raise ValueError("no devolvió una imagen")
    return Image.open(io.BytesIO(r.content)).convert("RGB")


def crear_una(numero, pedido, nivel):
    """Una imagen: (JPEG, pie de foto) o None si ningún modelo pudo."""
    prompt = str(pedido.get("prompt_en", "")).strip().rstrip(".")
    if not prompt:
        return None
    completo = urllib.parse.quote(f"{prompt}. {ESTILOS.get(nivel, ESTILOS['secundaria'])}, {SIN_TEXTO}")
    intentos = [(URL_CON_CLAVE.format(completo), modelo, True) for modelo in MODELOS.get(nivel, MODELOS["secundaria"])] \
        if POLLINATIONS_KEY else []
    intentos.append((URL_SIN_CLAVE.format(completo), "flux", False))   # último recurso, gratis y sin clave
    # De a una: Pollinations rechaza varios pedidos juntos desde la misma conexión.
    for url, modelo, con_clave in intentos:
        try:
            imagen = _pedir(url, modelo, 40 + numero, con_clave)
        except Exception:
            time.sleep(1)
            continue
        salida = io.BytesIO()
        imagen.save(salida, format="JPEG", quality=88)
        return salida.getvalue(), "Imagen creada con IA: " + str(pedido.get("descripcion", ""))
    return None
