"""Modelo: pide el resumen a la API gratis de Gemini.

Gemini recibe el PDF completo (no solo su texto): así lee también lo que está dentro de las
imágenes, diagramas, tablas, gráficos y páginas escaneadas o sacadas con el celular.
Si Gemini no puede abrir el PDF y el documento tiene texto, se resume solo el texto.
Después hay un segundo repaso: Gemini compara el resumen con el documento entero y completa las
secciones o cifras que hayan quedado afuera.
"""
import base64
import json
import time

import requests

from configuracion import (CONCEPTOS, GEMINI_API_KEY, GEMINI_MODELO, NIVELES,
                           PREGUNTAS, PUNTOS_CLAVE, RAMAS_MAPA, TEMAS_MAXIMO, TEMAS_MINIMO)

BASE = "https://generativelanguage.googleapis.com"
URL = f"{BASE}/v1beta/models/{GEMINI_MODELO}:generateContent"
SUBIDA = f"{BASE}/upload/v1beta/files"
# Hasta este tamaño el PDF va dentro del mismo pedido (Gemini acepta pedidos de hasta 20 MB y
# el PDF crece un tercio al pasarlo a base64). Si es más grande, se sube aparte.
MAXIMO_EN_PEDIDO = 14 * 1024 * 1024


class ErrorGemini(Exception):
    """Error con un mensaje listo para mostrar al usuario."""


class RespuestaRota(ErrorGemini):
    """Gemini contestó, pero con un JSON cortado o mal formado: vale la pena pedirlo otra vez."""


PROMPT = """Resume el documento {origen} en español para {nivel}.

{como_leer}

Responde SOLO con un JSON con esta forma:
{{
  "titulo": "título corto del documento",
  "resumen_general": "1 o 2 párrafos",
  "puntos_clave": ["{n_puntos} ideas principales"],
  "temas": [{{"subtitulo": "nombre del tema", "texto": "resumen del tema en 1 a 3 párrafos"}}],
  "mapa": {{"centro": "idea central en 2-4 palabras", "ramas": ["{n_ramas} ideas de 1-4 palabras"]}},
  "dato_destacado": {{"valor": "cifra corta, ej. 97 %", "texto": "qué significa, en una frase"}},
  "graficos": [{{"titulo": "...", "tipo": "barras o torta", "etiquetas": ["..."], "valores": [numeros], "tema": 1}}],
  "imagenes_ia": [{{"prompt_en": "descripción en inglés para generar la imagen", "descripcion": "pie de foto corto en español", "tema": 1}}],
  "imagenes_pdf": [{{"numero": 1, "pie": "pie de foto corto en español", "tema": 1}}],
  "imagen_portada": 0,
  "conceptos": [{{"termino": "...", "definicion": "..."}}],
  "preguntas": [{{"pregunta": "...", "respuesta": "respuesta corta"}}]
}}

Reglas:
- "temas": un tema por cada parte importante del documento, en su orden: entre {temas_min} y
  {temas_max}. Es un resumen: NO dejes afuera ninguna parte importante (datos, decisiones, plazos,
  costos, conclusiones). Antes de escribir, haz la lista de TODAS las secciones con título del
  documento (de principio a fin, incluidas las del final como recepción, ventas, premios o
  resultados) y comprueba al terminar que cada una está en algún tema. Un documento largo con
  muchas secciones necesita más temas: usa hasta {temas_max}. Si hay más secciones que temas,
  junta solo las más cortas y parecidas, y nombra cada sección juntada dentro del texto.
  No juntes en un solo tema cosas que en el documento son partes distintas.
  Tampoco repitas ideas ni inventes secciones que no sean contenido real (por ejemplo, un "tema"
  que hable de las preguntas o del mapa conceptual).
- Cifras: copia los números EXACTOS del documento (cantidades, fechas, porcentajes, precios,
  totales). Nunca los cambies por aproximaciones como «más de cien» o «miles» cuando el documento
  da la cifra. Cada tema lleva las cifras, fechas y nombres clave de su sección.
- "puntos_clave": las ideas más importantes de TODO el documento, no solo del principio, con sus cifras exactas.
- "dato_destacado": la cifra real más importante del documento (porcentaje, cantidad, año) con lo que
  significa. Si el documento no tiene ninguna cifra importante, null. Nunca inventes números.
- "graficos": {regla_graficos}
- "imagenes_ia": {regla_imagenes}
- "imagenes_pdf": {regla_imagenes_pdf}
- "imagen_portada": {regla_portada}
- En "graficos", "imagenes_ia" e "imagenes_pdf", "tema" es el número (1, 2, 3...) del elemento de
  "temas" con el que más tiene que ver, para ponerlo al lado de ese tema.
- Hasta {n_conceptos} conceptos y {n_preguntas} preguntas.
{documento}"""

# Segundo repaso: el modelo gratis a veces se saltea secciones del final o redondea cifras.
# Con el resumen ya hecho, vuelve a mirar el documento entero y completa lo que falte.
PROMPT_REVISION = """Este es un resumen, en JSON, del documento {origen}, escrito para {nivel}:
{resumen}

Revísalo contra el documento COMPLETO, sección por sección y de principio a fin (incluidas las
secciones del final, como recepción, ventas, premios, resultados o conclusiones). Corrígelo:
- Si falta una sección importante o un dato importante (cifras exactas, fechas, nombres,
  resultados, valoraciones, lugares), agrégalo: amplía el tema que corresponde o agrega un tema
  nuevo en el lugar que le toca según el orden del documento. Como máximo {temas_max} temas: si
  hacen falta más, junta las secciones cortas y parecidas y nombra cada una dentro del texto.
- Cambia toda cifra aproximada («más de cien», «miles») por la cifra exacta del documento.
- No quites nada que esté bien, no repitas ideas y no inventes nada. Mismo nivel de lenguaje.
Responde SOLO con un JSON:
{{"resumen_general": "1 o 2 párrafos", "puntos_clave": ["{n_puntos} ideas con sus cifras exactas"],
  "temas": [{{"subtitulo": "...", "texto": "1 a 3 párrafos"}}],
  "orden": [números]}}
"orden" tiene un número por cada tema del resumen original, en su orden: la posición (1, 2, 3...)
que ese tema tiene ahora en tu lista "temas".
{documento}"""

COMO_LEER_PDF = (
    "Lee TODO el PDF: el texto y también lo que muestran las imágenes, fotos, diagramas, esquemas,\n"
    "tablas y gráficos. Si hay páginas escaneadas o fotografiadas, lee el texto que aparece en ellas.\n"
    "Lo que solo está en una imagen o un diagrama es parte del contenido y va en el resumen.")
COMO_LEER_TEXTO = "Solo tienes el texto del documento (sin sus imágenes)."


def _armar_prompt(nivel, n_graficos, n_imagenes_ia, n_imagenes_pdf=0, n_candidatas=0, texto=None, portada=False):
    regla_graficos = (
        f"{n_graficos} gráficos, cada uno con un grupo distinto de números reales del documento "
        "(por ejemplo: cifras que cambian a lo largo de los años, porcentajes o puntajes de "
        "valoración, cantidades por categoría, partes de un total). Busca en TODO el documento, "
        "también en sus tablas, notas y gráficos, antes de decidir que no hay datos. Cada gráfico "
        "tiene al menos 2 valores, todos con la misma unidad. Solo si de verdad no hay suficientes "
        "grupos de números reales, entrega menos o una lista vacía. Nunca inventes números."
        if n_graficos else "lista vacía []")
    regla_imagenes = (
        f"exactamente {n_imagenes_ia} imágenes, cada una de una idea importante y distinta del documento. "
        "Cada prompt_en tiene de 40 a 70 palabras en inglés y describe UNA escena concreta y rica en "
        "detalles de ese contenido (no algo genérico): qué hay en primer plano y en el fondo, el lugar, "
        "las personas u objetos con sus detalles (materiales, ropa, colores), la acción, la luz y la hora "
        "del día. Nada de texto, letras, carteles ni etiquetas escritas en la escena (no describas qué "
        "dice un cartel o una etiqueta). Los generadores de imágenes no saben escribir: NUNCA pongas en la "
        "escena libros, revistas, mangas, cómics, lomos de libros, periódicos, carteles, letreros, pantallas, "
        "mapas con nombres ni piedras con inscripciones. Si el tema trata de eso (por ejemplo, ventas de "
        "libros o una escritura antigua), muestra a las personas, el lugar, los personajes o un objeto "
        "sin escritura que lo represente. No indiques el estilo de "
        "dibujo: eso se agrega aparte según la edad." if n_imagenes_ia else "lista vacía []")
    regla_imagenes_pdf = (
        f"elige hasta {n_imagenes_pdf} de las {n_candidatas} imágenes numeradas que van antes de este "
        "pedido (sacadas del PDF). Elige solo las que ayudan a entender el contenido: diagramas, "
        "esquemas, gráficos, tablas, mapas o fotos del tema. NO elijas las decorativas: portadas, "
        "fondos, texturas, marcas de agua, logos, sellos ni fotos que no tengan que ver con el tema. "
        "Si ninguna sirve, lista vacía. Ordénalas de la más útil a la menos útil. \"pie\" explica en "
        "una frase qué muestra la imagen y qué tiene que ver con el tema."
        if n_imagenes_pdf and n_candidatas else "lista vacía []")
    regla_portada = (
        f"el número (1 a {n_candidatas}) de la imagen numerada que mejor sirve de foto de portada: "
        "representativa del tema y atractiva (una foto o ilustración, mejor que un diagrama lleno de "
        "texto). No elijas logos, sellos, fondos ni marcas de agua. Si ninguna sirve, 0."
        if portada and n_candidatas else "0")
    return PROMPT.format(
        origen="adjunto" if texto is None else "de abajo",
        como_leer=COMO_LEER_PDF if texto is None else COMO_LEER_TEXTO,
        nivel=NIVELES[nivel][1], temas_min=TEMAS_MINIMO, temas_max=TEMAS_MAXIMO, n_puntos=PUNTOS_CLAVE, n_ramas=RAMAS_MAPA,
        n_conceptos=CONCEPTOS, n_preguntas=PREGUNTAS, regla_graficos=regla_graficos,
        regla_imagenes=regla_imagenes, regla_imagenes_pdf=regla_imagenes_pdf, regla_portada=regla_portada,
        documento="" if texto is None else "\nDOCUMENTO:\n" + texto[:400000] + "\n")


def _cabeceras(extra=None):
    return {"x-goog-api-key": GEMINI_API_KEY, **(extra or {})}


def _subir_pdf(pdf):
    """Sube un PDF grande a Gemini (File API) y espera que lo termine de preparar. Devuelve (nombre, uri)."""
    try:
        inicio = requests.post(SUBIDA, timeout=60, json={"file": {"display_name": "documento.pdf"}}, headers=_cabeceras({
            "X-Goog-Upload-Protocol": "resumable",
            "X-Goog-Upload-Command": "start",
            "X-Goog-Upload-Header-Content-Length": str(len(pdf)),
            "X-Goog-Upload-Header-Content-Type": "application/pdf",
        }))
        inicio.raise_for_status()
        r = requests.post(inicio.headers["x-goog-upload-url"], data=pdf, timeout=600, headers={
            "X-Goog-Upload-Offset": "0",
            "X-Goog-Upload-Command": "upload, finalize",
        })
        r.raise_for_status()
        archivo = r.json()["file"]
        for _ in range(90):   # hasta 3 minutos para que Gemini prepare el PDF
            if archivo.get("state") == "ACTIVE":
                return archivo["name"], archivo["uri"]
            if archivo.get("state") == "FAILED":
                break
            time.sleep(2)
            archivo = requests.get(f"{BASE}/v1beta/{archivo['name']}", headers=_cabeceras(), timeout=30).json()
    except (requests.RequestException, KeyError, ValueError):
        pass
    raise ErrorGemini("No se pudo subir el PDF a Gemini. Inténtalo otra vez o prueba con un PDF más liviano.")


def _borrar_subido(nombre):
    # Gemini lo borra solo a las 48 horas; se borra antes para no dejar el documento allá.
    try:
        requests.delete(f"{BASE}/v1beta/{nombre}", headers=_cabeceras(), timeout=30)
    except requests.RequestException:
        pass


def _pedir(partes):
    """Manda el pedido (reintenta si Gemini está saturado). Devuelve la respuesta HTTP."""
    cuerpo = {
        "contents": [{"parts": partes}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0.4},
    }
    for intento in range(3):
        try:
            r = requests.post(URL, json=cuerpo, timeout=300, headers=_cabeceras())
        except requests.RequestException:
            raise ErrorGemini("No se pudo conectar con Gemini. Revisa tu internet e inténtalo otra vez.")
        if r.status_code != 503 or intento == 2:
            return r
        time.sleep(3)


def _mensaje_de(r):
    try:
        return str(r.json()["error"]["message"])
    except (ValueError, KeyError, TypeError):
        return ""


def _interpretar(r):
    """Convierte la respuesta de Gemini en el diccionario del resumen, o lanza ErrorGemini."""
    if r.status_code == 429:
        raise ErrorGemini("Llegaste al límite gratis de Gemini. Espera un minuto o intenta mañana.")
    if r.status_code in (401, 403) or (r.status_code == 400 and "API key" in _mensaje_de(r)):
        raise ErrorGemini("La clave de Gemini no es válida. Revisa GEMINI_API_KEY en configuracion.py.")
    if r.status_code == 404:
        raise ErrorGemini("El modelo de Gemini no existe. Cambia GEMINI_MODELO en configuracion.py.")
    if r.status_code == 503:
        raise ErrorGemini("Gemini está saturado en este momento. Espera un momento e inténtalo otra vez.")
    try:
        r.raise_for_status()
        texto_json = r.json()["candidates"][0]["content"]["parts"][0]["text"]
        datos = _leer_json(texto_json)
    except (requests.RequestException, KeyError, IndexError, ValueError):
        raise RespuestaRota("Gemini respondió algo inesperado. Inténtalo otra vez.")
    # A veces Gemini devuelve el resumen metido en una lista: [{...}].
    if isinstance(datos, list) and datos and isinstance(datos[0], dict):
        datos = datos[0]
    if not isinstance(datos, dict):
        raise RespuestaRota("Gemini respondió algo inesperado. Inténtalo otra vez.")
    return datos


def _leer_json(texto):
    """El JSON de Gemini; si viene con algo alrededor (como ```json ... ```), se rescata lo de adentro."""
    try:
        return json.loads(texto)
    except ValueError:
        inicio, fin = texto.find("{"), texto.rfind("}")
        if inicio == -1 or fin <= inicio:
            raise
        return json.loads(texto[inicio:fin + 1])


def _pedir_resumen(partes):
    """Pide y lee la respuesta; si llega rota (pasa de vez en cuando con el modelo gratis), la pide
    una vez más antes de avisar del error."""
    for intento in range(2):
        r = _pedir(partes)
        if r.status_code == 400 and "API key" not in _mensaje_de(r):
            return r, None   # Gemini no pudo abrir el PDF: lo resuelve quien llama
        try:
            return r, _interpretar(r)
        except RespuestaRota:
            if intento == 1:
                raise
            time.sleep(2)


def _partes_de_imagenes(miniaturas):
    """Las imágenes candidatas del PDF, numeradas, para que Gemini elija cuáles van al resumen."""
    partes = []
    for numero, miniatura in enumerate(miniaturas, start=1):
        partes.append({"text": f"Imagen {numero}:"})
        partes.append({"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(miniatura).decode("ascii")}})
    return partes


def _revisar(documento_partes, datos, nivel, texto=None):
    """Segundo repaso del resumen contra el documento. Si algo sale mal, se queda el resumen original."""
    resumen = {k: datos.get(k) for k in ("resumen_general", "puntos_clave", "temas")}
    prompt = PROMPT_REVISION.format(
        origen="adjunto" if texto is None else "de abajo", nivel=NIVELES[nivel][1],
        resumen=json.dumps(resumen, ensure_ascii=False), temas_max=TEMAS_MAXIMO, n_puntos=PUNTOS_CLAVE,
        documento="" if texto is None else "\nDOCUMENTO:\n" + texto[:400000] + "\n")
    try:
        _, revision = _pedir_resumen([*documento_partes, {"text": prompt}])
    except ErrorGemini:
        return datos
    if revision is None:
        return datos
    return _aplicar_revision(datos, revision)


def _aplicar_revision(datos, revision):
    """Toma los temas, puntos clave y resumen corregidos, y mueve los gráficos e imágenes al número
    de tema que les toca ahora. No acepta una revisión que pierda temas."""
    originales = [t for t in (datos.get("temas") or []) if isinstance(t, dict)]
    temas = [t for t in (revision.get("temas") or [])
             if isinstance(t, dict) and str(t.get("subtitulo", "")).strip() and str(t.get("texto", "")).strip()][:TEMAS_MAXIMO]
    if len(temas) < len(originales):
        return datos
    mapa = {}
    orden = revision.get("orden")
    if isinstance(orden, list) and len(orden) == len(originales):
        for anterior, nuevo in enumerate(orden, start=1):
            try:
                nuevo = int(nuevo)
            except (TypeError, ValueError):
                continue
            if 1 <= nuevo <= len(temas):
                mapa[anterior] = nuevo
    for clave in ("graficos", "imagenes_ia", "imagenes_pdf"):
        for elemento in datos.get(clave) or []:
            if not isinstance(elemento, dict):
                continue
            try:
                anterior = int(elemento.get("tema"))
            except (TypeError, ValueError):
                continue
            elemento["tema"] = mapa.get(anterior, anterior if anterior <= len(temas) else None)
    datos["temas"] = temas
    if isinstance(revision.get("puntos_clave"), list) and revision["puntos_clave"]:
        datos["puntos_clave"] = revision["puntos_clave"]
    if str(revision.get("resumen_general") or "").strip():
        datos["resumen_general"] = revision["resumen_general"]
    return datos


def resumir(pdf, texto, nivel, n_graficos=0, n_imagenes_ia=0, miniaturas=(), n_imagenes_pdf=0, portada=False):
    """Resume el PDF completo (bytes). 'texto' es el texto que se le pudo sacar, para usar si
    Gemini no puede abrir el PDF. 'miniaturas': imágenes del PDF entre las que Gemini elige
    hasta 'n_imagenes_pdf' (vuelven en "imagenes_pdf") y, si 'portada', la foto de la portada
    (vuelve en "imagen_portada"). Devuelve (resumen, si leyó el PDF entero)."""
    miniaturas = list(miniaturas) if (n_imagenes_pdf or portada) else []
    imagenes = _partes_de_imagenes(miniaturas)
    subido = None
    try:
        if len(pdf) <= MAXIMO_EN_PEDIDO:
            documento = {"inline_data": {"mime_type": "application/pdf", "data": base64.b64encode(pdf).decode("ascii")}}
        else:
            subido, uri = _subir_pdf(pdf)
            documento = {"file_data": {"mime_type": "application/pdf", "file_uri": uri}}
        _, datos = _pedir_resumen([documento, *imagenes,
                                   {"text": _armar_prompt(nivel, n_graficos, n_imagenes_ia, n_imagenes_pdf,
                                                          len(miniaturas), portada=portada)}])
        # Sin datos = 400 sin problema de clave: Gemini no pudo abrir este PDF (demasiadas páginas, formato raro).
        if datos is not None:
            return _revisar([documento], datos, nivel), True
    finally:
        if subido:
            _borrar_subido(subido)

    if len(texto) < 100:
        raise ErrorGemini("Gemini no pudo leer este PDF. Prueba guardarlo de nuevo como PDF o dividirlo en partes.")
    r, datos = _pedir_resumen([*imagenes, {"text": _armar_prompt(nivel, n_graficos, n_imagenes_ia, n_imagenes_pdf,
                                                                   len(miniaturas), texto=texto, portada=portada)}])
    if datos is None:
        raise ErrorGemini("Gemini no pudo leer este PDF. Prueba guardarlo de nuevo como PDF o dividirlo en partes.")
    return _revisar([], datos, nivel, texto=texto), False
