"""Controlador: recibe lo que elige el usuario, usa los modelos y devuelve el PDF."""
import io
import json
import urllib.parse
from datetime import date

from flask import Blueprint, jsonify, render_template, request, send_file

from configuracion import (COLORES, MAX_CANDIDATAS, MAX_GRAFICOS, MAX_IMAGENES, NIVELES,
                           PALABRAS_POR_MINUTO, PALABRAS_POR_PAGINA)
from modelos import imagen_portada, servicio_gemini, servicio_imagenes
from modelos.lector_pdf import DocumentoPDF
from utilidades import trabajos
from utilidades.ayudantes import entero_en_rango, minutos_de_lectura, nombre_seguro
from vistas.pdf.documento import crear_pdf_resumen

resumen_bp = Blueprint("resumen", __name__)


@resumen_bp.route("/")
def inicio():
    return render_template("inicio.html", pagina="inicio")


@resumen_bp.route("/crear")
def crear_pagina():
    return render_template("crear.html", pagina="crear")


def _leer_opciones(formulario):
    """Lee y valida las opciones del formulario."""
    con_imagenes = formulario.get("con_imagenes") == "si"
    con_graficos = formulario.get("con_graficos") == "si"
    return {
        "nivel": formulario.get("nivel", "secundaria"),
        "color": formulario.get("color", "amarillo"),
        "con_mapa": formulario.get("con_mapa", "si") == "si",
        "n_imagenes": entero_en_rango(formulario.get("cant_imagenes"), 1, MAX_IMAGENES) if con_imagenes else 0,
        "origen": "pdf" if formulario.get("origen_imagenes") == "pdf" else "ia",
        "n_graficos": entero_en_rango(formulario.get("cant_graficos"), 1, MAX_GRAFICOS) if con_graficos else 0,
    }


def _elegidas_por_gemini(datos, candidatas, cantidad):
    """Las imágenes del PDF que Gemini eligió (en su orden de utilidad), con su pie de foto y el
    tema al que acompañan: [{"datos", "pie", "tema"}]."""
    elegidas, usadas = [], set()
    for pedido in datos.get("imagenes_pdf") or []:
        if not isinstance(pedido, dict):
            continue
        try:
            numero = int(pedido.get("numero"))
        except (TypeError, ValueError):
            continue
        if 1 <= numero <= len(candidatas) and numero not in usadas:
            usadas.add(numero)
            elegidas.append({"datos": candidatas[numero - 1]["datos"],
                             "pie": str(pedido.get("pie") or "").strip(), "tema": pedido.get("tema")})
    return elegidas[:cantidad]


def _portada_del_pdf(datos, candidatas):
    """La imagen del PDF que Gemini eligió para la portada, ya recortada, o None."""
    try:
        numero = int(datos.get("imagen_portada") or 0)
    except (TypeError, ValueError):
        return None
    if not 1 <= numero <= len(candidatas):
        return None
    try:
        return imagen_portada.preparar(candidatas[numero - 1]["datos"])[0]
    except imagen_portada.ErrorPortada:
        return None


@resumen_bp.route("/resumir", methods=["POST"])
def resumir():
    """Revisa lo que llegó y empieza el resumen en segundo plano. Devuelve el número de trabajo;
    la página pregunta el avance en /resumir/<id> y baja el PDF de /resumir/<id>/pdf."""
    archivo = request.files.get("pdf")
    if not archivo or not archivo.filename.lower().endswith(".pdf"):
        return jsonify(error="Sube un archivo en formato PDF."), 400

    op = _leer_opciones(request.form)
    if op["nivel"] not in NIVELES or op["color"] not in COLORES:
        return jsonify(error="Opción no válida."), 400

    try:
        documento = DocumentoPDF(archivo)
    except Exception:
        return jsonify(error="No se pudo abrir el PDF. Puede estar dañado o protegido."), 400

    # La imagen de la portada se revisa ya, así un error se ve al toque y no al final.
    avisos = []
    foto_portada = None
    subida = request.files.get("portada")
    if subida and subida.filename:
        try:
            foto_portada, aviso = imagen_portada.preparar(subida.read(), request.form.get("foco_x"),
                                                          request.form.get("foco_y"))
        except imagen_portada.ErrorPortada as error:
            return jsonify(error=str(error)), 400
        if aviso:
            avisos.append(aviso)
    # Sin imagen subida, Gemini puede elegir una del PDF para la portada.
    portada_del_pdf = foto_portada is None and request.form.get("portada_respaldo", "pdf") == "pdf"

    formulario = {c: request.form.get(c, "").strip() for c in ("estudiante", "curso", "docente", "autor")}
    trabajo = trabajos.empezar(_procesar, documento, op, formulario, archivo.filename, foto_portada,
                               portada_del_pdf, avisos)
    return jsonify(trabajo.estado()), 202


def _procesar(trabajo, documento, op, formulario, nombre_archivo, foto_portada, portada_del_pdf, avisos):
    """Todo el resumen, paso a paso, moviendo la barra de avance."""
    trabajo.avanzar(4, f"Leyendo el PDF ({documento.paginas} páginas)…")
    n_img_ia = op["n_imagenes"] if op["origen"] == "ia" else 0
    n_img_pdf = op["n_imagenes"] if op["origen"] == "pdf" else 0
    candidatas = []
    if n_img_pdf or portada_del_pdf:
        trabajo.avanzar(7, "Buscando las imágenes del PDF…")
        candidatas = documento.candidatas(MAX_CANDIDATAS)

    # 1. Gemini lee el PDF entero (texto, imágenes, diagramas y escaneos) y arma el resumen.
    # No avisa cuánto le falta: la barra avanza según lo que suele tardar un PDF de ese tamaño.
    hasta = 60 if n_img_ia else 82
    esperado = min(90, 12 + 2 * documento.paginas + 2 * len(candidatas))
    try:
        datos, leyo_todo = trabajo.mientras(
            10, hasta, esperado, "Gemini está leyendo el PDF y escribiendo el resumen…",
            lambda: servicio_gemini.resumir(
                documento.bytes, documento.texto, op["nivel"], op["n_graficos"], n_img_ia,
                miniaturas=[c["miniatura"] for c in candidatas], n_imagenes_pdf=n_img_pdf, portada=portada_del_pdf))
    except servicio_gemini.ErrorGemini as error:
        raise trabajos.ErrorParaElUsuario(str(error))
    if portada_del_pdf:
        foto_portada = _portada_del_pdf(datos, candidatas)
    if not leyo_todo:
        avisos.append("Gemini no pudo abrir el PDF completo: el resumen se hizo solo con el texto, sin las imágenes.")

    # 2. Imágenes: creadas con IA (de a una; la barra avanza con cada una) o elegidas del PDF.
    if n_img_ia:
        pedidos = [p for p in (datos.get("imagenes_ia") or []) if isinstance(p, dict)][:n_img_ia]
        imagenes = []
        tramo = (85 - hasta) / max(1, len(pedidos))
        for i, pedido in enumerate(pedidos):
            hecha = trabajo.mientras(hasta + i * tramo, hasta + (i + 1) * tramo, 25,
                                     f"Creando la imagen {i + 1} de {len(pedidos)} con IA…",
                                     lambda i=i, pedido=pedido: servicio_imagenes.crear_una(i, pedido, op["nivel"]))
            if hecha:
                imagenes.append({"datos": hecha[0], "pie": hecha[1], "tema": pedido.get("tema")})
        if len(imagenes) < n_img_ia:
            avisos.append(f"Se crearon {len(imagenes)} de {n_img_ia} imágenes con IA.")
    elif n_img_pdf:
        imagenes = _elegidas_por_gemini(datos, candidatas, n_img_pdf)
        if not candidatas:
            avisos.append("El PDF no tiene imágenes para agregar.")
        elif len(imagenes) < n_img_pdf:
            avisos.append(f"Solo {len(imagenes)} de las imágenes del PDF explican el tema; "
                          "las demás eran decorativas (portada, fondos, logos) y no se agregaron.")
    else:
        imagenes = []

    trabajo.avanzar(86, "Preparando los gráficos y la portada…")
    graficos = [g for g in (datos.get("graficos") or []) if isinstance(g, dict)][:op["n_graficos"]]
    datos["graficos"] = graficos
    if op["n_graficos"] and len(graficos) < op["n_graficos"]:
        avisos.append(f"El documento solo tenía datos para {len(graficos)} de {op['n_graficos']} "
                      "gráficos (no se inventan números).")

    # 3. Datos de la portada
    if documento.tiene_texto():
        min_original = minutos_de_lectura(documento.texto)
    else:   # escaneado: no se pueden contar las palabras, se estiman por página
        min_original = max(1, round(documento.paginas * PALABRAS_POR_PAGINA / PALABRAS_POR_MINUTO))
    min_resumen = minutos_de_lectura(json.dumps(datos, ensure_ascii=False))
    datos["portada"] = {
        **formulario,
        "nivel": NIVELES[op["nivel"]][0],
        "fecha": date.today().strftime("%d/%m/%Y"),
        "archivo": nombre_archivo,
        "paginas": documento.paginas,
        "min_original": min_original,
        "min_resumen": min_resumen,
    }

    # 4. Armar el PDF (dos vueltas: la primera cuenta las páginas para el índice)
    trabajo.avanzar(90, "Armando el PDF: páginas, índice y gráficos…")
    pdf = crear_pdf_resumen(datos, color=op["color"], imagenes=imagenes, incluir_mapa=op["con_mapa"],
                            imagen_portada=foto_portada,
                            al_avanzar=lambda: trabajo.avanzar(95, "Dando los últimos toques…"))
    trabajo.terminar(pdf, {
        "nombre": nombre_seguro(nombre_archivo),
        "X-Paginas": str(documento.paginas),
        "X-Min-Original": str(min_original),
        "X-Min-Resumen": str(min_resumen),
        "X-Aviso": urllib.parse.quote(" ".join(avisos)),
    })


@resumen_bp.route("/resumir/<identificador>")
def estado(identificador):
    trabajo = trabajos.buscar(identificador)
    if not trabajo:
        return jsonify(error="Ese resumen ya no está: pasó más de una hora o el servidor se reinició. "
                             "Vuelve a crearlo."), 404
    return jsonify(trabajo.estado())


@resumen_bp.route("/resumir/<identificador>/pdf")
def descargar(identificador):
    trabajo = trabajos.buscar(identificador)
    if not trabajo or trabajo.fase != "listo":
        return jsonify(error="El resumen todavía no está listo o ya no existe."), 404
    respuesta = send_file(io.BytesIO(trabajo.pdf), mimetype="application/pdf", as_attachment=True,
                          download_name=trabajo.cabeceras["nombre"])
    for clave, valor in trabajo.cabeceras.items():
        if clave.startswith("X-"):
            respuesta.headers[clave] = valor
    return respuesta
