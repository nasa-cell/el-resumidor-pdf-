"""Vista PDF: arma el documento completo, sección por sección.

Orden: portada · índice y «En pocas palabras» · lo más importante (con mapa) · tema por tema
(cada tema con sus imágenes y gráficos al lado) · palabras clave · preguntas · soluciones y notas.
Se arma dos veces: la primera sólo para saber en qué página cae cada sección (el índice y el
«3 / 7» del pie lo necesitan) y la segunda es la definitiva.
"""
import io
from xml.sax.saxutils import escape

from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (BaseDocTemplate, Frame, KeepTogether, NextPageTemplate, PageBreak,
                                PageTemplate, Paragraph, Spacer, Table, TableStyle)
from reportlab.platypus.doctemplate import ActionFlowable

from .componentes import (ChipNumero, ImagenEnMarco, LineasParaEscribir, Marcador, Tarjeta, TituloSeccion,
                          fila_de_tarjetas, parrafo)
from .graficos import crear_grafico
from .mapa_conceptual import crear_mapa
from .portada import dibujar_encabezado_y_pie, dibujar_portada
from .tema import (ACENTO, ALTO, ANCHO, CEJA, CIFRA, COLORES_ACENTO, CUADRICULA, CUERPO, ENTRADA, ETIQUETA,
                   FONDO, INDICE, INDICE_NUMERO, INDICE_PAGINA, LILA, LISTA, MARGEN, NOTA, NUMERO_TARJETA,
                   PAPEL, PIE_FOTO, PUNTEADO, RESPUESTA, SUBTITULO, TARJETA, TERMINO, TITULO_GRAFICO, UTIL,
                   color_resaltador)

ALTO_MAXIMO_IMAGEN = 88 * mm
ALTO_MAXIMO_PAREJA = 62 * mm
ESPACIO = 6 * mm


class DocResumen(BaseDocTemplate):
    """Documento con dos tipos de hoja: la portada y las interiores (con encabezado y pie)."""

    def __init__(self, salida, armador, total):
        super().__init__(salida, pagesize=(ANCHO, ALTO), leftMargin=MARGEN, rightMargin=MARGEN,
                         topMargin=24 * mm, bottomMargin=22 * mm, title=armador.titulo, author="Resumidor de PDF")
        marco = Frame(self.leftMargin, self.bottomMargin, self.width, self.height, id="texto",
                      leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
        self.addPageTemplates([
            PageTemplate("portada", [marco], onPage=lambda c, d: armador.dibujar_portada(c)),
            PageTemplate("interior", [marco], onPage=self._al_empezar_hoja, onPageEnd=self._al_terminar_hoja),
        ])
        self.armador, self.total = armador, total
        self.paginas_de = {}            # clave de la sección → página donde empieza
        self._seccion = None            # la última sección que empezó
        self._seccion_al_empezar = None
        self._primera_en_hoja = None    # sección que abre la hoja (si la hoja empieza con su título)
        self._primera_vista = None      # primera sección que aparece en la hoja
        self._hay_contenido = False

    def _al_empezar_hoja(self, c, doc):
        self._seccion_al_empezar, self._primera_en_hoja, self._hay_contenido = self._seccion, None, False
        self._primera_vista = None

    def afterFlowable(self, pieza):
        if isinstance(pieza, TituloSeccion):
            self.paginas_de.setdefault(pieza.clave, self.page)
            if not self._hay_contenido and self._primera_en_hoja is None:
                self._primera_en_hoja = pieza
            self._primera_vista = self._primera_vista or pieza
            self._seccion = pieza
        elif not isinstance(pieza, (Spacer, ActionFlowable, PageBreak)):
            self._hay_contenido = True

    def _al_terminar_hoja(self, c, doc):
        # El encabezado nombra la sección que se está leyendo al empezar la hoja (o la primera que aparece).
        seccion = self._primera_en_hoja or self._seccion_al_empezar or self._primera_vista
        dibujar_encabezado_y_pie(c, self.armador.titulo, seccion, self.page, self.total, self.armador.nivel)


class ArmadorPDF:
    def __init__(self, datos, color, imagenes, incluir_mapa=True, imagen_portada=None, al_avanzar=None):
        self.datos = datos
        self.al_avanzar = al_avanzar   # avisa cuando termina la primera vuelta
        self.resaltador = color_resaltador(color)
        self.imagenes = [i for i in (imagenes or []) if i.get("datos")]
        self.incluir_mapa = incluir_mapa
        self.imagen_portada = imagen_portada
        self.titulo = str(datos.get("titulo") or "Resumen")
        self.nivel = (datos.get("portada") or {}).get("nivel", "")
        self.temas_validos = [t for t in (datos.get("temas") or []) if isinstance(t, dict)]
        self.graficos_validos = [g for g in (datos.get("graficos") or []) if isinstance(g, dict)]
        self.conceptos_validos = [c for c in (datos.get("conceptos") or []) if isinstance(c, dict)]
        self.preguntas_validas = [q for q in (datos.get("preguntas") or []) if isinstance(q, dict)]
        self.dato = self._dato_destacado()

    def dibujar_portada(self, c):
        dibujar_portada(c, self.titulo, self.datos.get("portada", {}), self.resaltador, self.imagen_portada)

    # ---------- qué secciones hay ----------
    def _dato_destacado(self):
        dato = self.datos.get("dato_destacado")
        if isinstance(dato, dict) and str(dato.get("valor") or "").strip() and str(dato.get("texto") or "").strip():
            return {"valor": str(dato["valor"]).strip()[:18], "texto": str(dato["texto"]).strip()}
        return None

    def _mapa(self):
        mapa = self.datos.get("mapa") or {}
        return mapa if self.incluir_mapa and isinstance(mapa, dict) and mapa.get("centro") and mapa.get("ramas") else None

    def _plan(self):
        """Nombres de las secciones que van a salir, en orden (para numerarlas y para el índice)."""
        plan = []
        if self.datos.get("resumen_general"):
            plan.append("En pocas palabras")
        if self.datos.get("puntos_clave") or self.dato or self._mapa():
            plan.append("Lo más importante")
        if self.temas_validos or self.imagenes or self.graficos_validos:
            plan.append("Tema por tema")
        if self.conceptos_validos:
            plan.append("Palabras clave")
        if self.preguntas_validas:
            plan += ["Ponte a prueba", "Soluciones y notas"]
        return plan

    def _titulo(self, nombre):
        numero = self.plan.index(nombre) + 1
        return TituloSeccion(numero, nombre, f"s{numero}")

    def _subtitulo(self, numero, texto):
        self._marcas += 1
        numero = f'<font name="Pop-B" size="10.5" color="#6D42F5">{numero}</font>&nbsp;&nbsp;' if numero else ""
        return [Marcador(texto, f"t{self._marcas}", 1), Paragraph(numero + escape(str(texto)), SUBTITULO)]

    @staticmethod
    def _parrafos(texto, estilo):
        return [parrafo(x, estilo) for x in str(texto or "").split("\n") if x.strip()]

    # ---------- secciones ----------
    def indice(self, paginas):
        filas = [[Paragraph(str(n), INDICE_NUMERO), parrafo(nombre, INDICE),
                  Paragraph(str(paginas.get(f"s{n}", "")) if paginas else "00", INDICE_PAGINA)]
                 for n, nombre in enumerate(self.plan, 1)]
        tabla = Table(filas, colWidths=[10 * mm, UTIL - 26 * mm, 16 * mm])
        tabla.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
                                   ("LINEBELOW", (0, 0), (-1, -1), 0.6, PUNTEADO, None, (1, 2.4)),
                                   ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                                   ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
        return [Paragraph("CONTENIDO", CEJA), Spacer(1, 4), tabla, Spacer(1, 16 * mm)]

    def en_pocas_palabras(self):
        parrafos = self._parrafos(self.datos.get("resumen_general"), ENTRADA)
        if not parrafos:
            return []
        return [KeepTogether([self._titulo("En pocas palabras"), parrafos[0]])] + parrafos[1:]

    def lo_mas_importante(self):
        if "Lo más importante" not in self.plan:
            return []
        piezas = [self._titulo("Lo más importante")]
        puntos = [str(p) for p in (self.datos.get("puntos_clave") or []) if str(p).strip()]
        if puntos:
            tarjetas = [Tarjeta([Paragraph(str(i), NUMERO_TARJETA), parrafo(p, TARJETA)], borde=CUADRICULA)
                        for i, p in enumerate(puntos, 1)]
            columnas = 2 if len(puntos) in (2, 4) else min(3, len(puntos))
            piezas.append(fila_de_tarjetas(tarjetas, columnas, UTIL))
        if self.dato:
            # La cifra nunca se corta a mitad de palabra: si es larga («48 toneladas»), se achica.
            tamano = 30
            while tamano > 18 and pdfmetrics.stringWidth(self.dato["valor"], "Fra-B", tamano) > 70 * mm:
                tamano -= 2
            ancho_cifra = min(pdfmetrics.stringWidth(self.dato["valor"], "Fra-B", tamano) + 16, 80 * mm)   # +10 del relleno de la celda
            estilo = ParagraphStyle("cifra_ajustada", parent=CIFRA, fontSize=tamano, leading=tamano * 1.08)
            fila = Table([[Paragraph(escape(self.dato["valor"]), estilo), parrafo(self.dato["texto"], ENTRADA)]],
                         colWidths=[max(ancho_cifra, 30 * mm), UTIL - 24 - max(ancho_cifra, 30 * mm)])
            fila.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                                      ("RIGHTPADDING", (0, 0), (0, 0), 10), ("TOPPADDING", (0, 0), (-1, -1), 0),
                                      ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
            piezas.append(Tarjeta([Paragraph("EL DATO", CEJA), fila], fondo=LILA, relleno=12))
        bloque = [KeepTogether(piezas[:2])] + piezas[2:]
        mapa = self._mapa()
        if mapa:
            numero = self.plan.index("Lo más importante") + 1
            bloque.append(KeepTogether([Spacer(1, 4)] + self._subtitulo(f"{numero}.1", "Mapa conceptual")
                                       + [crear_mapa(mapa, self.resaltador)]))
        return bloque

    def tema_por_tema(self):
        if "Tema por tema" not in self.plan:
            return []
        numero = self.plan.index("Tema por tema") + 1
        n_temas = len(self.temas_validos)

        def de_tema(elemento, k):
            try:
                return int(elemento.get("tema")) == k
            except (TypeError, ValueError):
                return False

        def sin_tema(elemento):
            return not any(de_tema(elemento, k) for k in range(1, n_temas + 1))

        piezas = []
        for k, tema in enumerate(self.temas_validos, 1):
            cabeza = self._subtitulo(f"{numero}.{k}", tema.get("subtitulo") or "Tema")
            texto = self._parrafos(tema.get("texto"), CUERPO)
            inicio = ([self._titulo("Tema por tema")] if k == 1 else [])
            piezas.append(KeepTogether(inicio + cabeza + texto[:1]))   # el título nunca queda solo
            piezas += texto[1:]
            piezas += self._figuras([i for i in self.imagenes if de_tema(i, k)])
            piezas += self._graficos([g for g in self.graficos_validos if de_tema(g, k)])
        # Lo que Gemini no ubicó en ningún tema va al final de la sección.
        resto = self._figuras([i for i in self.imagenes if sin_tema(i)]) + \
            self._graficos([g for g in self.graficos_validos if sin_tema(g)])
        if not self.temas_validos and resto:
            resto[0] = KeepTogether([self._titulo("Tema por tema"), resto[0]])
        return piezas + resto

    def _figuras(self, imagenes):
        """Una imagen: ancho completo. Dos: pareja con marcos del mismo tamaño. Más: de a pares."""
        piezas = []
        for i in range(0, len(imagenes), 2):
            par = imagenes[i:i + 2]
            numeros = []
            for _ in par:
                self.n_figura += 1
                numeros.append(self.n_figura)
            pies = [Paragraph(f'<font name="Pop-B" color="#6D42F5">Figura {n} ·</font> {escape(str(im.get("pie") or ""))}',
                              PIE_FOTO) for n, im in zip(numeros, par)]
            if len(par) == 1:
                ancho_px, alto_px = ImageReader(io.BytesIO(par[0]["datos"])).getSize()
                alto = min(UTIL * alto_px / ancho_px, ALTO_MAXIMO_IMAGEN)
                bloque = [ImagenEnMarco(par[0]["datos"], UTIL, alto), Spacer(1, 4), pies[0]]
            else:
                ancho = (UTIL - ESPACIO) / 2
                naturales = []
                for im in par:
                    ancho_px, alto_px = ImageReader(io.BytesIO(im["datos"])).getSize()
                    naturales.append(ancho * alto_px / ancho_px)
                alto = max(38 * mm, min(max(naturales), ALTO_MAXIMO_PAREJA))
                tabla = Table([[ImagenEnMarco(im["datos"], ancho, alto) for im in par], pies],
                              colWidths=[ancho + ESPACIO, ancho])
                tabla.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                                           ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                                           ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, 0), 4),
                                           ("RIGHTPADDING", (0, 0), (0, -1), ESPACIO)]))
                bloque = [tabla]
            piezas.append(KeepTogether([Spacer(1, 8)] + bloque + [Spacer(1, 10)]))
        return piezas

    def _graficos(self, graficos):
        piezas = []
        for g in graficos:
            imagen = crear_grafico(g, UTIL)
            if not imagen:
                continue
            self.n_grafico += 1
            piezas.append(KeepTogether([
                Spacer(1, 8), Paragraph(f"GRÁFICO {self.n_grafico}", CEJA), parrafo(g.get("titulo") or "", TITULO_GRAFICO),
                imagen, Paragraph("Datos tomados del documento original.", NOTA), Spacer(1, 10)]))
        return piezas

    def palabras_clave(self):
        if not self.conceptos_validos:
            return []
        tarjetas = [Tarjeta([parrafo(c.get("termino", ""), TERMINO), parrafo(c.get("definicion", ""), TARJETA)],
                            fondo=FONDO, separacion=2) for c in self.conceptos_validos]
        return [Spacer(1, 6), KeepTogether([self._titulo("Palabras clave"), fila_de_tarjetas(tarjetas, 2, UTIL)])]

    def _filas_numeradas(self, campo, estilo, con_lineas):
        filas = []
        for i, q in enumerate(self.preguntas_validas, 1):
            texto = [parrafo(q.get(campo, ""), estilo)] + ([Spacer(1, 2), LineasParaEscribir(4)] if con_lineas else [])
            tabla = Table([[ChipNumero(i, COLORES_ACENTO[(i - 1) % len(COLORES_ACENTO)], 18), texto]],
                          colWidths=[11 * mm, UTIL - 11 * mm])
            tabla.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                                       ("RIGHTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 0),
                                       ("BOTTOMPADDING", (0, 0), (-1, -1), 12)]))
            filas.append(tabla)
        return filas

    def ponte_a_prueba(self):
        if not self.preguntas_validas:
            return []
        filas = self._filas_numeradas("pregunta", LISTA, True)
        return [Spacer(1, 6), KeepTogether([self._titulo("Ponte a prueba"), Spacer(1, 2), filas[0]])] + filas[1:]

    def soluciones(self):
        if not self.preguntas_validas:
            return []
        corte = Table([[""]], colWidths=[UTIL], rowHeights=[1])
        corte.setStyle(TableStyle([("LINEABOVE", (0, 0), (-1, -1), 0.9, ACENTO, None, (3, 3))]))
        return [PageBreak(), self._titulo("Soluciones y notas"), corte, Spacer(1, 4),
                Paragraph("Revisa las respuestas después de responder.", ETIQUETA), Spacer(1, 10)] + \
            self._filas_numeradas("respuesta", RESPUESTA, False) + \
            [Spacer(1, 6)] + self._subtitulo(None, "Mis notas") + [LineasParaEscribir(llenar=True)]

    # ---------- todo junto ----------
    def _historia(self, paginas):
        self.plan = self._plan()
        self._marcas = self.n_figura = self.n_grafico = 0
        historia = [Spacer(1, 1), NextPageTemplate("interior"), PageBreak()]
        historia += self.indice(paginas)
        for seccion in (self.en_pocas_palabras, self.lo_mas_importante, self.tema_por_tema,
                        self.palabras_clave, self.ponte_a_prueba, self.soluciones):
            historia += seccion()
        return historia

    def construir(self):
        # 1.ª vuelta: saber las páginas de cada sección y cuántas hay en total.
        borrador = DocResumen(io.BytesIO(), self, total=None)
        borrador.build(self._historia(None))
        if self.al_avanzar:
            self.al_avanzar()
        salida = io.BytesIO()
        final = DocResumen(salida, self, total=borrador.page)
        final.build(self._historia(borrador.paginas_de))
        return salida.getvalue()


def crear_pdf_resumen(datos, color="amarillo", imagenes=None, incluir_mapa=True, imagen_portada=None,
                      al_avanzar=None):
    """Punto de entrada de la vista PDF. 'imagenes': [{"datos", "pie", "tema"}]."""
    return ArmadorPDF(datos, color, imagenes, incluir_mapa, imagen_portada, al_avanzar).construir()
