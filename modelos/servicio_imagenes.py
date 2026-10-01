"""Modelo: crea imágenes con IA, gratis.

Orden: 1) Pollinations con clave (enter.pollinations.ai), modelos de primera con los créditos
gratis del día: MAI Image 2.6 (fotos realistas) para secundaria y adultos y FLUX 1.1 Pro
(ilustración colorida) para niños. 2) Si falla, Cloudflare Workers AI (FLUX schnell), la
alternativa: rápida, sin esperas ni marca de agua, con un cupo gratis de unas 170 imágenes al
día. 3) Si tampoco, el flux de Pollinations sin clave. Nunca se compra nada: sin créditos o sin
cupo, ese servicio simplemente no se usa.

El flux sin clave es gratis pero deja hacer una imagen cada medio minuto más o menos: si se pide
otra antes, responde 402. Por eso se deja un espacio entre imágenes y, si igual la rechaza, se
espera y se vuelve a intentar, para entregar siempre la cantidad de imágenes que se pidió.
"""
import base64
import io
import threading
import time
import urllib.parse

import requests
from PIL import Image

from configuracion import CLOUDFLARE_ACCOUNT_ID, CLOUDFLARE_API_TOKEN, POLLINATIONS_KEY

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

# Respuestas que significan «ahora no» (sin créditos o demasiado seguido), no «nunca».
OCUPADO = {402, 429, 503}
# Medido el 30/09/2026: sin clave, una segunda imagen a los 15 s da 402 y a los 45 s ya funciona.
ESPACIO_SIN_CLAVE = 25          # segundos mínimos entre dos imágenes sin clave
ESPERAS_SIN_CLAVE = [20, 25, 30, 40, 50, 60]   # reintentos si igual la rechaza (unos 4 minutos en total)
PAUSA_CLAVE_SIN_CREDITOS = 3600  # si la clave no tiene créditos, no se vuelve a probar en una hora

URL_CLOUDFLARE = "https://api.cloudflare.com/client/v4/accounts/{}/ai/run/@cf/black-forest-labs/flux-1-schnell"
PAUSA_CLOUDFLARE_SIN_CUPO = 1800   # si se acabó el cupo del día, no se vuelve a probar en media hora

_candado = threading.Lock()
_estado = {"ultima_sin_clave": 0.0, "clave_sin_creditos_hasta": 0.0, "cloudflare_sin_cupo_hasta": 0.0}


def _a_formato_resumen(imagen):
    """Recorta al centro a 16:10, el mismo formato que las demás imágenes del resumen."""
    ancho, alto = imagen.size
    if ancho / alto > 1.6:
        nuevo = round(alto * 1.6)
        return imagen.crop(((ancho - nuevo) // 2, 0, (ancho - nuevo) // 2 + nuevo, alto))
    nuevo = round(ancho / 1.6)
    return imagen.crop((0, (alto - nuevo) // 2, ancho, (alto - nuevo) // 2 + nuevo))


def _con_cloudflare(prompt_completo):
    """FLUX schnell en Cloudflare Workers AI; None si no está configurado o no pudo."""
    if not (CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN) or time.time() < _estado["cloudflare_sin_cupo_hasta"]:
        return None
    for intento in range(2):
        try:
            r = requests.post(URL_CLOUDFLARE.format(CLOUDFLARE_ACCOUNT_ID),
                              headers={"Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}"},
                              json={"prompt": prompt_completo[:2000], "steps": 6}, timeout=120)
            if r.status_code == 429 or (r.status_code >= 400 and "neuron" in r.text.lower()):
                _estado["cloudflare_sin_cupo_hasta"] = time.time() + PAUSA_CLOUDFLARE_SIN_CUPO
                return None
            r.raise_for_status()
            datos = base64.b64decode(r.json()["result"]["image"])
            return _a_formato_resumen(Image.open(io.BytesIO(datos)).convert("RGB"))
        except Exception:
            time.sleep(2 + 3 * intento)
    return None


def _pedir(url, modelo, semilla, con_clave):
    params = {"model": modelo, "width": 1280, "height": 800, "seed": semilla, "nologo": "true"}
    headers = {"Authorization": f"Bearer {POLLINATIONS_KEY}"} if con_clave else {}
    r = requests.get(url, params=params, headers=headers, timeout=180)
    r.raise_for_status()
    if "image" not in r.headers.get("content-type", ""):
        raise ValueError("no devolvió una imagen")
    return Image.open(io.BytesIO(r.content)).convert("RGB")


def _codigo(error):
    respuesta = getattr(error, "response", None)
    return getattr(respuesta, "status_code", None)


def _con_clave(completo, nivel, semilla):
    """Prueba los modelos de primera con la clave; None si ninguno pudo."""
    if not POLLINATIONS_KEY or time.time() < _estado["clave_sin_creditos_hasta"]:
        return None
    url = URL_CON_CLAVE.format(completo)
    for modelo in MODELOS.get(nivel, MODELOS["secundaria"]):
        try:
            return _pedir(url, modelo, semilla, True)
        except Exception as error:
            if _codigo(error) == 402:
                # Los créditos son de la cuenta, no del modelo: ningún otro modelo con clave va a andar.
                _estado["clave_sin_creditos_hasta"] = time.time() + PAUSA_CLAVE_SIN_CREDITOS
                return None
            time.sleep(1)
    return None


def _sin_clave(completo, semilla, al_esperar):
    """flux gratis sin clave, respetando su ritmo: espera y reintenta hasta lograrlo."""
    url = URL_SIN_CLAVE.format(completo)
    for numero_intento, espera_si_falla in enumerate([*ESPERAS_SIN_CLAVE, None]):
        with _candado:
            falta = ESPACIO_SIN_CLAVE - (time.time() - _estado["ultima_sin_clave"])
            if falta > 0:
                if al_esperar:
                    al_esperar(int(falta) + 1)
                time.sleep(falta)
            _estado["ultima_sin_clave"] = time.time()
        try:
            return _pedir(url, "flux", semilla + numero_intento, False)
        except Exception as error:
            if espera_si_falla is None:
                return None
            if al_esperar:
                al_esperar(espera_si_falla)
            # Si la rechazó por ir muy seguido, la próxima espera ya cuenta desde ahora.
            time.sleep(espera_si_falla if _codigo(error) in OCUPADO else 3)
    return None


def crear_una(numero, pedido, nivel, al_esperar=None):
    """Una imagen: (JPEG, pie de foto) o None si de verdad no se pudo.
    'al_esperar(segundos)' avisa cuando hay que esperar al servicio gratis."""
    prompt = str(pedido.get("prompt_en", "")).strip().rstrip(".")
    if not prompt:
        return None
    texto = f"{prompt}. {ESTILOS.get(nivel, ESTILOS['secundaria'])}, {SIN_TEXTO}"
    completo = urllib.parse.quote(texto)
    semilla = 40 + numero
    # De a una: Pollinations rechaza varios pedidos juntos desde la misma conexión.
    imagen = (_con_clave(completo, nivel, semilla) or _con_cloudflare(texto)
              or _sin_clave(completo, semilla, al_esperar))
    if imagen is None:
        return None
    salida = io.BytesIO()
    imagen.save(salida, format="JPEG", quality=88)
    return salida.getvalue(), "Imagen creada con IA: " + str(pedido.get("descripcion", ""))
