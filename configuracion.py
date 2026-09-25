"""Configuración general del proyecto: claves y opciones."""
import os

# Las claves reales viven en configuracion_local.py (no se sube a GitHub).
# Si ese archivo no existe (por ejemplo, recién clonado el repo), quedan vacías
# y la app avisa con un error claro en vez de fallar sin explicación.
try:
    from configuracion_local import GEMINI_API_KEY as _GEMINI_LOCAL
except ImportError:
    _GEMINI_LOCAL = ""
try:
    from configuracion_local import POLLINATIONS_KEY as _POLLINATIONS_LOCAL
except ImportError:
    _POLLINATIONS_LOCAL = ""

# Clave gratis de Gemini: https://aistudio.google.com/apikey
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", _GEMINI_LOCAL)
GEMINI_MODELO = "gemini-flash-lite-latest"   # si da error 404, prueba otro modelo gratis de AI Studio

# Pollinations (imágenes con IA), clave gratis creada en https://enter.pollinations.ai
POLLINATIONS_KEY = os.environ.get("POLLINATIONS_KEY", _POLLINATIONS_LOCAL)

# Opciones que puede elegir el usuario
NIVELES = {
    "ninos": ("Niños (6-11 años)",
              "niños de 6 a 11 años: oraciones cortas (de 12 palabras como máximo), palabras sencillas "
              "y ejemplos de la vida diaria. Simplifica cómo se dice, pero no quites nada importante: "
              "conserva las cifras, fechas y nombres clave (de lugares, programas o grupos) y explícalos "
              "con palabras simples, por ejemplo «48 toneladas de basura al día, como 8 camiones llenos»"),
    "secundaria": ("Secundaria (12-17 años)",
                   "adolescentes de 12 a 17 años: lenguaje claro, con términos técnicos explicados"),
    "adultos": ("Adultos", "adultos o universitarios: lenguaje formal y técnico"),
}
# Largo del resumen: la cantidad de temas depende del documento (uno por cada parte importante),
# así no se deja nada importante afuera ni se inventan temas en documentos cortos.
TEMAS_MINIMO, TEMAS_MAXIMO = 2, 8
PUNTOS_CLAVE = "3 a 5"
RAMAS_MAPA = 4
CONCEPTOS = 4
PREGUNTAS = 3
COLORES = ["amarillo", "verde", "rosa", "celeste", "naranja"]
MAX_IMAGENES = 4
MAX_GRAFICOS = 3
MAX_CANDIDATAS = 12   # imágenes del PDF que se le muestran a Gemini para que elija las útiles
PALABRAS_POR_MINUTO = 230
PALABRAS_POR_PAGINA = 300    # para estimar el tiempo de lectura de un PDF escaneado
