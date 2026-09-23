"""
Resumidor de PDF con IA gratis
Punto de arranque: python app.py  ->  http://localhost:5000
"""
from flask import Flask

from controladores.resumen_controlador import resumen_bp


def crear_app():
    app = Flask(__name__,
                template_folder="vistas/plantillas",
                static_folder="vistas/estaticos",
                static_url_path="/estaticos")
    app.register_blueprint(resumen_bp)
    return app


app = crear_app()

if __name__ == "__main__":
    app.run(debug=True, port=5000)
