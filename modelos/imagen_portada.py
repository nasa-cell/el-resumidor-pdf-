"""Modelo: prepara la imagen principal de la portada (la que sube el usuario o una del PDF)."""
import io

from PIL import Image, ImageOps, UnidentifiedImageError

from modelos.lector_pdf import _a_rgb

# La foto ocupa todo el ancho de la hoja A4 y el 56 % de su alto: esa es su proporción.
PROPORCION = 210 / (297 * 0.56)
ANCHO_FINAL = 1800           # suficiente para imprimir nítido sin que el PDF pese de más
ANCHO_MINIMO_NITIDO = 1200   # por debajo de esto se avisa que puede verse borrosa
MAXIMO_BYTES = 8 * 1024 * 1024
TIPOS = {"JPEG", "PNG", "WEBP"}


class ErrorPortada(Exception):
    """Error con un mensaje listo para mostrar al usuario."""


def _recortar(imagen, foco_x, foco_y):
    """Recorta a la proporción de la portada. 'foco' funciona igual que object-position en la
    vista previa de la página (0 = pegado a la izquierda/arriba, 1 = a la derecha/abajo), así el
    recorte del PDF es exactamente el que el usuario vio."""
    ancho, alto = imagen.size
    if ancho / alto > PROPORCION:        # sobra ancho
        nuevo_ancho = round(alto * PROPORCION)
        x = round(foco_x * (ancho - nuevo_ancho))
        caja = (x, 0, x + nuevo_ancho, alto)
    else:                                # sobra alto
        nuevo_alto = round(ancho / PROPORCION)
        y = round(foco_y * (alto - nuevo_alto))
        caja = (0, y, ancho, y + nuevo_alto)
    return imagen.crop(caja)


def _numero_entre_0_y_1(valor, por_defecto=0.5):
    try:
        return min(max(float(valor), 0.0), 1.0)
    except (TypeError, ValueError):
        return por_defecto


def preparar(datos, foco_x=0.5, foco_y=0.5):
    """Devuelve (JPEG listo para la portada, aviso o None). Lanza ErrorPortada si no sirve."""
    if len(datos) > MAXIMO_BYTES:
        raise ErrorPortada("La imagen de la portada pesa más de 8 MB. Elige una más liviana.")
    try:
        imagen = Image.open(io.BytesIO(datos))
        if imagen.format not in TIPOS:
            raise ErrorPortada("La imagen de la portada tiene que ser JPG, PNG o WebP.")
        imagen.load()
    except (UnidentifiedImageError, OSError):
        raise ErrorPortada("No se pudo abrir la imagen de la portada. Prueba con otra en JPG o PNG.")
    # Las fotos del celular guardan el giro aparte: se aplica para que no salgan de costado.
    imagen = _a_rgb(ImageOps.exif_transpose(imagen))
    aviso = None
    if imagen.width < ANCHO_MINIMO_NITIDO:
        aviso = "La imagen de la portada es chica: puede verse borrosa al imprimir."
    imagen = _recortar(imagen, _numero_entre_0_y_1(foco_x), _numero_entre_0_y_1(foco_y))
    if imagen.width > ANCHO_FINAL:
        imagen = imagen.resize((ANCHO_FINAL, round(ANCHO_FINAL / PROPORCION)), Image.LANCZOS)
    salida = io.BytesIO()
    imagen.save(salida, format="JPEG", quality=86, optimize=True)
    return salida.getvalue(), aviso
