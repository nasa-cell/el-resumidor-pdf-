"""Modelo: pide el resumen a la API gratis de Gemini."""
import json
import time

import requests

from configuracion import (CONCEPTOS, GEMINI_API_KEY, GEMINI_MODELO, NIVELES,
                           PREGUNTAS, PUNTOS_CLAVE, RAMAS_MAPA, TEMAS)

URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODELO}:generateContent"


class ErrorGemini(Exception):
    """Error con un mensaje listo para mostrar al usuario."""


PROMPT = """Resume el siguiente documento en español para {nivel}.

Responde SOLO con un JSON con esta forma:
{{
  "titulo": "título corto del documento",
  "resumen_general": "1 o 2 párrafos",
  "puntos_clave": ["{n_puntos} ideas principales"],
  "temas": [{{"subtitulo": "nombre del tema", "texto": "resumen del tema en 1 o 2 párrafos"}}],
  "mapa": {{"centro": "idea central en 2-4 palabras", "ramas": ["{n_ramas} ideas de 1-4 palabras"]}},
  "graficos": [{{"titulo": "...", "tipo": "barras o torta", "etiquetas": ["..."], "valores": [numeros]}}],
  "imagenes_ia": [{{"prompt_en": "descripción en inglés para generar la imagen", "descripcion": "pie de foto corto en español"}}],
  "conceptos": [{{"termino": "...", "definicion": "..."}}],
  "preguntas": [{{"pregunta": "...", "respuesta": "respuesta corta"}}]
}}

Reglas:
- "temas": hasta {temas} elementos reales y distintos del documento, en su orden. Si el documento
  no tiene tantos temas separados, entrega menos: nunca repitas una idea ni inventes una sección
  que no sea contenido real (por ejemplo, no crees un "tema" que hable de las preguntas o del
  mapa conceptual).
- "graficos": {regla_graficos}
- "imagenes_ia": {regla_imagenes}
- Hasta {n_conceptos} conceptos y {n_preguntas} preguntas.

DOCUMENTO:
{texto}
"""


def _armar_prompt(texto, nivel, n_graficos, n_imagenes_ia):
    regla_graficos = (
        f"hasta {n_graficos} gráficos usando SOLO números reales que aparezcan en el documento "
        "(porcentajes, cantidades, años). Si no hay suficientes datos, entrega menos o una "
        "lista vacía. Nunca inventes números." if n_graficos else "lista vacía []")
    regla_imagenes = (
        f"exactamente {n_imagenes_ia} imágenes. Cada prompt_en describe una ilustración educativa, "
        "clara y sin texto escrito, de una idea distinta del documento, estilo ilustración plana "
        "a color." if n_imagenes_ia else "lista vacía []")
    return PROMPT.format(nivel=NIVELES[nivel][1], temas=TEMAS, n_puntos=PUNTOS_CLAVE, n_ramas=RAMAS_MAPA,
                         n_conceptos=CONCEPTOS, n_preguntas=PREGUNTAS, regla_graficos=regla_graficos,
                         regla_imagenes=regla_imagenes, texto=texto[:400000])


def resumir(texto, nivel, n_graficos=0, n_imagenes_ia=0):
    """Devuelve un diccionario con el resumen. Lanza ErrorGemini si algo falla."""
    cuerpo = {
        "contents": [{"parts": [{"text": _armar_prompt(texto, nivel, n_graficos, n_imagenes_ia)}]}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0.4},
    }
    for intento in range(3):
        try:
            r = requests.post(URL, json=cuerpo, timeout=300, headers={"x-goog-api-key": GEMINI_API_KEY})
        except requests.RequestException:
            raise ErrorGemini("No se pudo conectar con Gemini. Revisa tu internet e inténtalo otra vez.")
        if r.status_code != 503 or intento == 2:
            break
        time.sleep(3)

    if r.status_code == 429:
        raise ErrorGemini("Llegaste al límite gratis de Gemini. Espera un minuto o intenta mañana.")
    if r.status_code in (400, 401, 403):
        raise ErrorGemini("La clave de Gemini no es válida. Revisa GEMINI_API_KEY en configuracion.py.")
    if r.status_code == 404:
        raise ErrorGemini("El modelo de Gemini no existe. Cambia GEMINI_MODELO en configuracion.py.")
    if r.status_code == 503:
        raise ErrorGemini("Gemini está saturado en este momento. Espera un momento e inténtalo otra vez.")
    try:
        r.raise_for_status()
        texto_json = r.json()["candidates"][0]["content"]["parts"][0]["text"]
        return json.loads(texto_json)
    except (requests.RequestException, KeyError, IndexError, ValueError):
        raise ErrorGemini("Gemini respondió algo inesperado. Inténtalo otra vez.")
