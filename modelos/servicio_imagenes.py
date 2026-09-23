"""Modelo: crea imágenes con IA usando Pollinations (gratis)."""
import io
import time
import urllib.parse

import requests
from PIL import Image

from configuracion import POLLINATIONS_KEY

URL = "https://image.pollinations.ai/prompt/{}?width=1024&height=640&nologo=true&seed={}"


def _crear_una(numero, pedido):
    prompt = str(pedido.get("prompt_en", "")).strip()
    if not prompt:
        return None
    url = URL.format(urllib.parse.quote(prompt + ", educational flat illustration, no text"), 40 + numero)
    headers = {"Authorization": f"Bearer {POLLINATIONS_KEY}"} if POLLINATIONS_KEY else {}
    # Pollinations solo deja 1 pedido a la vez por IP: si le mandamos varios juntos, rechaza el resto.
    for intento in range(3):
        try:
            r = requests.get(url, timeout=90, headers=headers)
            r.raise_for_status()
            imagen = Image.open(io.BytesIO(r.content)).convert("RGB")
            salida = io.BytesIO()
            imagen.save(salida, format="JPEG", quality=88)
            return salida.getvalue(), "Imagen creada con IA: " + str(pedido.get("descripcion", ""))
        except Exception:
            if intento == 2:
                return None
            time.sleep(2)


def crear_imagenes(pedidos, cantidad):
    """Crea las imágenes de a una, en orden. Devuelve solo las que salieron bien."""
    pedidos = [p for p in (pedidos or []) if isinstance(p, dict)][:cantidad]
    resultados = [_crear_una(i, p) for i, p in enumerate(pedidos)]
    return [r for r in resultados if r]
