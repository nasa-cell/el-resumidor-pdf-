"""Turnos justos entre varios resúmenes que se hacen a la vez.

Es como una fila: cada pedido espera en orden de llegada. Quien termina y vuelve a pedir se pone al
final, así ningún resumen se adelanta a los demás y todos avanzan parejo (por ejemplo, con las
imágenes con IA: una del primer PDF, una del segundo, una del tercero… y vuelve a empezar).
"""
import collections
import threading


class TurnoJusto:
    def __init__(self, cupos):
        self._cupos = cupos
        self._fila = collections.deque()
        self._condicion = threading.Condition()

    def ocupado(self):
        """True si un pedido nuevo tendría que esperar."""
        with self._condicion:
            return self._cupos == 0 or bool(self._fila)

    def __enter__(self):
        with self._condicion:
            yo = object()
            self._fila.append(yo)
            self._condicion.wait_for(lambda: self._cupos > 0 and self._fila[0] is yo)
            self._fila.popleft()
            self._cupos -= 1
            self._condicion.notify_all()   # si queda otro cupo, el siguiente de la fila también pasa
        return self

    def __exit__(self, *error):
        with self._condicion:
            self._cupos += 1
            self._condicion.notify_all()
