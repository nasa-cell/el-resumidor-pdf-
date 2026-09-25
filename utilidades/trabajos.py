"""Resúmenes en segundo plano con su avance, para la barra de progreso de la página.

La página manda el PDF, recibe un número de trabajo y pregunta cada segundo cómo va. Si el
usuario recarga o cierra la pestaña, el trabajo sigue: al volver, la página retoma la barra con
el mismo número. Los trabajos viven en memoria (una hora); si el servidor se reinicia, se pierden.
"""
import math
import threading
import time
import uuid

GUARDAR_SEGUNDOS = 60 * 60

_trabajos = {}
_candado = threading.Lock()


class ErrorParaElUsuario(Exception):
    """Error con un mensaje listo para mostrar en la página."""


class Trabajo:
    def __init__(self):
        self.id = uuid.uuid4().hex
        self.porcentaje = 0
        self.paso = "Recibido. Empezando…"
        self.fase = "procesando"          # procesando | listo | error
        self.error = None
        self.pdf = None
        self.cabeceras = {}
        self.actualizado = time.time()

    def avanzar(self, porcentaje, paso=None):
        """La barra nunca retrocede y no llega a 100 hasta que el PDF está listo."""
        with _candado:
            self.porcentaje = max(self.porcentaje, min(99, int(porcentaje)))
            if paso:
                self.paso = paso
            self.actualizado = time.time()

    def mientras(self, desde, hasta, segundos_esperados, paso, tarea):
        """Hace 'tarea' (que no avisa cuánto le falta, como el pedido a Gemini) y mientras tanto
        mueve la barra de 'desde' hacia 'hasta', cada vez más lento, sin llegar nunca a 'hasta'."""
        self.avanzar(desde, paso)
        terminado = threading.Event()

        def mover():
            inicio = time.time()
            while not terminado.wait(0.5):
                t = time.time() - inicio
                self.avanzar(desde + (hasta - desde) * 0.95 * (1 - math.exp(-t / segundos_esperados)))

        hilo = threading.Thread(target=mover, daemon=True)
        hilo.start()
        try:
            return tarea()
        finally:
            terminado.set()
            hilo.join()

    def terminar(self, pdf, cabeceras):
        with _candado:
            self.pdf, self.cabeceras = pdf, cabeceras
            self.porcentaje, self.fase, self.paso = 100, "listo", "¡Listo! Descargando tu resumen…"
            self.actualizado = time.time()

    def fallar(self, mensaje):
        with _candado:
            self.fase, self.error, self.paso = "error", mensaje, "No se pudo terminar."
            self.actualizado = time.time()

    def estado(self):
        with _candado:
            return {"id": self.id, "fase": self.fase, "porcentaje": self.porcentaje, "paso": self.paso,
                    "error": self.error}


def _limpiar():
    limite = time.time() - GUARDAR_SEGUNDOS
    with _candado:
        for clave in [c for c, t in _trabajos.items() if t.actualizado < limite]:
            del _trabajos[clave]


def empezar(funcion, *argumentos):
    """Crea el trabajo y hace funcion(trabajo, *argumentos) en otro hilo. Devuelve el trabajo."""
    _limpiar()
    trabajo = Trabajo()
    with _candado:
        _trabajos[trabajo.id] = trabajo

    def correr():
        try:
            funcion(trabajo, *argumentos)
        except ErrorParaElUsuario as error:
            trabajo.fallar(str(error))
        except Exception:
            import traceback
            traceback.print_exc()
            trabajo.fallar("Algo falló al crear el resumen. Inténtalo otra vez.")

    threading.Thread(target=correr, daemon=True).start()
    return trabajo


def buscar(identificador):
    with _candado:
        return _trabajos.get(identificador)
