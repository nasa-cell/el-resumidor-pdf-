"""Vista PDF: arma el documento completo, sección por sección."""
import io

from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (Image, KeepTogether, PageBreak, SimpleDocTemplate, Spacer,
                                Table, TableStyle)

from .componentes import ChipNumero, Marcador, Vineta, parrafo
from .graficos import crear_grafico
from .mapa_conceptual import crear_mapa
from .portada import crear_encabezado, crear_portada
from .tema import (ACENTO, ALTO, ANCHO, COLORES_ACENTO, CUADRICULA, CUERPO, DEFINICION, ETIQUETA, GRAFITO,
                   LISTA, MARGEN, PIE_FOTO, RESPUESTA, SUBTITULO, TERMINO, TITULO_SECCION, UTIL,
                   color_resaltador)


class ArmadorPDF:
    def __init__(self, datos, color, imagenes, incluir_mapa=True):
        self.datos = datos
        self.color = color
        self.resaltador = color_resaltador(color)
        self.imagenes = imagenes or []
        self.incluir_mapa = incluir_mapa
        self.titulo = str(datos.get("titulo") or "Resumen")
        self.historia = [Spacer(1, 1), PageBreak()]   # la página 1 es la portada
        self._marcas = 0

    # ---------- piezas ----------
    def _clave_marca(self):
        self._marcas += 1
        return f"m{self._marcas}"

    def _seccion(self, texto, nivel=0):
        return [Spacer(1, 10), Marcador(texto, self._clave_marca(), nivel), parrafo(texto, TITULO_SECCION)]

    @staticmethod
    def _parrafos(texto, estilo):
        return [parrafo(x, estilo) for x in str(texto or "").split("\n") if x.strip()]

    # ---------- secciones ----------
    def resumen_general(self):
        self.historia += self._seccion("En pocas palabras")
        self.historia += self._parrafos(self.datos.get("resumen_general"), CUERPO)

    def puntos_clave(self):
        puntos = self.datos.get("puntos_clave") or []
        if not puntos:
            return
        self.historia += self._seccion("Lo más importante")
        for punto in puntos:
            fila = Table([[Vineta(self.resaltador), parrafo(punto, LISTA)]], colWidths=[14, UTIL - 14])
            fila.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                                      ("LEFTPADDING", (0, 0), (-1, -1), 0),
                                      ("TOPPADDING", (0, 0), (-1, -1), 0),
                                      ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
            self.historia.append(fila)

    def mapa_conceptual(self):
        if not self.incluir_mapa:
            return
        mapa = self.datos.get("mapa") or {}
        if isinstance(mapa, dict) and mapa.get("centro") and mapa.get("ramas"):
            self.historia.append(KeepTogether(self._seccion("Mapa conceptual") +
                                              [crear_mapa(mapa, self.resaltador)]))

    def temas(self):
        for n, tema in enumerate(t for t in (self.datos.get("temas") or []) if isinstance(t, dict)):
            nombre = tema.get("subtitulo", "") or "Tema"
            bloque = ([Marcador(nombre, self._clave_marca(), 1), parrafo(nombre, SUBTITULO)]
                      + self._parrafos(tema.get("texto"), CUERPO))
            inicio = self._seccion("Tema por tema") if n == 0 else []
            self.historia.append(KeepTogether(inicio + bloque[:3]))   # el título nunca queda solo
            self.historia += bloque[3:]

    def graficos(self):
        imagenes = [crear_grafico(g, self.color) for g in (self.datos.get("graficos") or [])
                    if isinstance(g, dict)]
        for n, imagen in enumerate(i for i in imagenes if i):
            inicio = self._seccion("Los números del documento") if n == 0 else [Spacer(1, 10)]
            self.historia.append(KeepTogether(inicio + [imagen]))

    def imagenes_documento(self):
        """Dos imágenes por fila: si van una debajo de otra, gastan el doble de hojas."""
        if not self.imagenes:
            return
        ancho_col = (UTIL - 8 * mm) / 2
        pares = [self.imagenes[i:i + 2] for i in range(0, len(self.imagenes), 2)]
        for n, par in enumerate(pares):
            celdas = [self._celda_imagen(datos_imagen, pie, ancho_col) for datos_imagen, pie in par]
            if len(celdas) == 1:
                celdas.append([Spacer(1, 1)])
            fila = Table([celdas], colWidths=[ancho_col, ancho_col])
            fila.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                                      ("LEFTPADDING", (0, 0), (-1, -1), 0),
                                      ("RIGHTPADDING", (0, 0), (0, -1), 8 * mm),
                                      ("TOPPADDING", (0, 0), (-1, -1), 0),
                                      ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
            bloque = [fila]
            if n == 0:
                bloque = self._seccion("Imágenes") + bloque   # el título nunca queda solo
            self.historia += [KeepTogether(bloque), Spacer(1, 14)]

    @staticmethod
    def _celda_imagen(datos_imagen, pie, ancho_col):
        ancho_px, alto_px = ImageReader(io.BytesIO(datos_imagen)).getSize()
        ancho = ancho_col
        alto = ancho * alto_px / ancho_px
        marco = Table([[Image(io.BytesIO(datos_imagen), width=ancho, height=alto)]])
        marco.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.9, GRAFITO),
                                   ("LEFTPADDING", (0, 0), (-1, -1), 5),
                                   ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                                   ("TOPPADDING", (0, 0), (-1, -1), 5),
                                   ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
        return [marco] + ([Spacer(1, 4), parrafo(pie, PIE_FOTO)] if pie else [])

    def conceptos(self):
        conceptos = [c for c in (self.datos.get("conceptos") or []) if isinstance(c, dict)]
        if not conceptos:
            return
        filas = [[parrafo(c.get("termino", ""), TERMINO),
                  parrafo(c.get("definicion", ""), DEFINICION)] for c in conceptos]
        tabla = Table(filas, colWidths=[UTIL * 0.3, UTIL * 0.7])
        tabla.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                                   ("LINEBELOW", (0, 0), (-1, -2), 0.4, CUADRICULA),
                                   ("TOPPADDING", (0, 0), (-1, -1), 8),
                                   ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                                   ("LEFTPADDING", (0, 0), (0, -1), 4)]))
        self.historia.append(KeepTogether(self._seccion("Palabras clave") + [tabla]))

    def preguntas(self):
        preguntas = [q for q in (self.datos.get("preguntas") or []) if isinstance(q, dict)]
        if not preguntas:
            return

        def tabla(campo, estilo):
            t = Table([[ChipNumero(i, COLORES_ACENTO[(i - 1) % len(COLORES_ACENTO)]),
                       parrafo(q.get(campo, ""), estilo)]
                       for i, q in enumerate(preguntas, 1)], colWidths=[13 * mm, UTIL - 13 * mm])
            t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                                   ("LEFTPADDING", (0, 0), (-1, -1), 0),
                                   ("BOTTOMPADDING", (0, 0), (-1, -1), 9)]))
            return t

        self.historia.append(KeepTogether(self._seccion("Ponte a prueba") + [tabla("pregunta", LISTA)]))
        corte = Table([[""]], colWidths=[UTIL], rowHeights=[1])
        corte.setStyle(TableStyle([("LINEABOVE", (0, 0), (-1, -1), 0.8, ACENTO, None, (3, 3))]))
        self.historia.append(KeepTogether([Spacer(1, 18), corte, Spacer(1, 6),
                                           parrafo("Respuestas: revísalas después de responder", ETIQUETA),
                                           Spacer(1, 8), tabla("respuesta", RESPUESTA)]))

    # ---------- todo junto ----------
    def construir(self):
        for seccion in (self.resumen_general, self.puntos_clave, self.mapa_conceptual, self.temas,
                        self.graficos, self.imagenes_documento, self.conceptos, self.preguntas):
            seccion()
        salida = io.BytesIO()
        doc = SimpleDocTemplate(salida, pagesize=(ANCHO, ALTO), leftMargin=MARGEN,
                                rightMargin=MARGEN, topMargin=22 * mm, bottomMargin=22 * mm,
                                title=self.titulo)
        doc.build(self.historia,
                  onFirstPage=crear_portada(self.titulo, self.datos.get("portada", {}), self.resaltador),
                  onLaterPages=crear_encabezado(self.titulo))
        return salida.getvalue()


def crear_pdf_resumen(datos, color="amarillo", imagenes=None, incluir_mapa=True):
    """Punto de entrada de la vista PDF."""
    return ArmadorPDF(datos, color, imagenes, incluir_mapa).construir()
