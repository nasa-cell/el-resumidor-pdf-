"""Controlador: recibe lo que elige el usuario, usa los modelos y devuelve el PDF."""
import io
import json
import urllib.parse
from datetime import date

from flask import Blueprint, jsonify, render_template, request, send_file

from configuracion import COLORES, MAX_GRAFICOS, MAX_IMAGENES, NIVELES
from modelos import servicio_gemini, servicio_imagenes
from modelos.lector_pdf import DocumentoPDF
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


@resumen_bp.route("/resumir", methods=["POST"])
def resumir():
    archivo = request.files.get("pdf")
    if not archivo or not archivo.filename.lower().endswith(".pdf"):
        return jsonify(error="Sube un archivo en formato PDF."), 400

    op = _leer_opciones(request.form)
    if op["nivel"] not in NIVELES or op["color"] not in COLORES:
        return jsonify(error="Opción no válida."), 400

    # 1. Leer el PDF
    try:
        documento = DocumentoPDF(archivo)
    except Exception:
        return jsonify(error="No se pudo abrir el PDF. Puede estar dañado o protegido."), 400
    if not documento.tiene_texto():
        return jsonify(error="El PDF no tiene texto seleccionable (puede ser un escaneo)."), 400

    # 2. Pedir el resumen a Gemini
    n_img_ia = op["n_imagenes"] if op["origen"] == "ia" else 0
    try:
        datos = servicio_gemini.resumir(documento.texto, op["nivel"], op["n_graficos"], n_img_ia)
    except servicio_gemini.ErrorGemini as error:
        return jsonify(error=str(error)), 502

    # 3. Imágenes y gráficos según lo que eligió el usuario
    avisos = []
    if op["n_imagenes"] and op["origen"] == "ia":
        imagenes = servicio_imagenes.crear_imagenes(datos.get("imagenes_ia"), op["n_imagenes"])
        if len(imagenes) < op["n_imagenes"]:
            avisos.append(f"Se crearon {len(imagenes)} de {op['n_imagenes']} imágenes con IA.")
    elif op["n_imagenes"]:
        imagenes = documento.imagenes(op["n_imagenes"])
        if len(imagenes) < op["n_imagenes"]:
            avisos.append(f"El PDF solo tenía {len(imagenes)} imágenes útiles.")
    else:
        imagenes = []

    graficos = [g for g in (datos.get("graficos") or []) if isinstance(g, dict)][:op["n_graficos"]]
    datos["graficos"] = graficos
    if op["n_graficos"] and len(graficos) < op["n_graficos"]:
        avisos.append(f"El documento solo tenía datos para {len(graficos)} de {op['n_graficos']} "
                      "gráficos (no se inventan números).")

    # 4. Datos de la portada
    min_original = minutos_de_lectura(documento.texto)
    min_resumen = minutos_de_lectura(json.dumps(datos, ensure_ascii=False))
    f = request.form
    datos["portada"] = {
        "estudiante": f.get("estudiante", "").strip(),
        "curso": f.get("curso", "").strip(),
        "docente": f.get("docente", "").strip(),
        "autor": f.get("autor", "").strip(),
        "nivel": NIVELES[op["nivel"]][0],
        "fecha": date.today().strftime("%d/%m/%Y"),
        "archivo": archivo.filename,
        "paginas": documento.paginas,
        "min_original": min_original,
        "min_resumen": min_resumen,
    }

    # 5. Crear el PDF (vista) y enviarlo
    pdf = crear_pdf_resumen(datos, color=op["color"], imagenes=imagenes, incluir_mapa=op["con_mapa"])
    respuesta = send_file(io.BytesIO(pdf), mimetype="application/pdf", as_attachment=True,
                          download_name=nombre_seguro(archivo.filename))
    respuesta.headers["X-Paginas"] = str(documento.paginas)
    respuesta.headers["X-Min-Original"] = str(min_original)
    respuesta.headers["X-Min-Resumen"] = str(min_resumen)
    respuesta.headers["X-Aviso"] = urllib.parse.quote(" ".join(avisos))
    return respuesta
