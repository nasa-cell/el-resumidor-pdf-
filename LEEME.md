# Resumidor de PDF con IA (todo gratis) - Estructura MVC

## Estructura de carpetas

    resumidor-pdf-mvc/
    ├── app.py                      Arranque del programa
    ├── configuracion.py            Claves de API y opciones
    ├── requirements.txt            Librerías que se instalan
    │
    ├── modelos/                    MODELO: datos y conexión con las APIs
    │   ├── lector_pdf.py           Lee texto e imágenes del PDF
    │   ├── servicio_gemini.py      Pide el resumen a Gemini
    │   └── servicio_imagenes.py    Crea imágenes con IA (Pollinations)
    │
    ├── controladores/              CONTROLADOR: recibe el pedido y coordina
    │   └── resumen_controlador.py  Rutas "/", "/crear" y "/resumir"
    │
    ├── vistas/                     VISTA: lo que ve el usuario
    │   ├── plantillas/
    │   │   ├── base.html           Estructura común (cabecera, menú)
    │   │   ├── _nav.html           Menú Inicio / Crear resumen
    │   │   ├── inicio.html         Página "/": explica la herramienta
    │   │   └── crear.html          Página "/crear": el formulario
    │   ├── estaticos/
    │   │   ├── css/estilos.css     Diseño de la página (solo CSS)
    │   │   └── js/principal.js     Funcionamiento de la página (solo JavaScript)
    │   └── pdf/                    Diseño del PDF que se descarga
    │       ├── tema.py             Colores, letras y medidas
    │       ├── componentes.py      Resaltador, cuadrícula y viñetas
    │       ├── portada.py          Portada y encabezado de páginas
    │       ├── mapa_conceptual.py  Mapa conceptual
    │       ├── graficos.py         Gráficos de barras y torta
    │       ├── documento.py        Arma el PDF sección por sección
    │       └── fuentes/            Letra Poppins
    │
    └── utilidades/
        └── ayudantes.py            Funciones pequeñas (tiempo de lectura, etc.)

## Cómo funciona (MVC)
1. El usuario llena la página (VISTA: index.html + estilos.css + principal.js).
2. El CONTROLADOR (resumen_controlador.py) recibe el PDF y las opciones.
3. Los MODELOS leen el PDF, piden el resumen a Gemini y crean las imágenes.
4. El CONTROLADOR pasa los datos a la VISTA del PDF (vistas/pdf/documento.py).
5. El usuario descarga el PDF.

## Instalar y ejecutar en tu PC
    pip install -r requirements.txt
Creá un archivo `configuracion_local.py` (no se sube a GitHub) con tus claves:

    GEMINI_API_KEY = "tu-clave-de-gemini"
    POLLINATIONS_KEY = "tu-clave-de-pollinations"

Después:

    python app.py
Abre en el navegador: http://localhost:5000

## Publicar en Render (o cualquier hosting)
El código nunca lleva las claves escritas adentro (por eso `configuracion_local.py`
está en `.gitignore` y es seguro subir este repo, incluso público). En el panel de
Render, en la sección "Environment", agregá dos variables:

    GEMINI_API_KEY = tu-clave-de-gemini
    POLLINATIONS_KEY = tu-clave-de-pollinations

Comando de arranque (ya viene en el `Procfile`): `gunicorn app:app`

## APIs gratis
- Gemini: mantené el "Nivel gratuito" en AI Studio y no uses "Configurar la facturación".
- Pollinations (imágenes con IA): funciona sin clave, pero con clave gratis es mucho
  más confiable (ver más abajo).

## Si sale un aviso o error
- "clave no válida": crea otra en https://aistudio.google.com/apikey y cambiala en
  `configuracion_local.py` (o en las variables de entorno si está en Render)
- "límite gratis": espera un minuto; el plan gratis tiene un límite de usos por día
- "el modelo no existe": Google retiró ese modelo. Entra a https://aistudio.google.com/apikey
  y revisa qué modelos gratis siguen activos, o prueba con "gemini-flash-latest" en configuracion.py
- "Gemini está saturado": espera unos segundos y prueba de nuevo (la app ya reintenta sola 2 veces)
- "Se crearon 0 de N imágenes": Pollinations no respondió. Crea una clave gratis en
  https://enter.pollinations.ai y pégala en POLLINATIONS_KEY, o elige "Sacadas del PDF".

## Importante
Nunca escribas tus claves reales directo en `configuracion.py` ni las subas a un repo
público: usá `configuracion_local.py` (local) o variables de entorno (en el hosting).
No subas documentos con datos personales (DNI, notas con nombres): el plan gratis
de Gemini puede usar lo que envías para mejorar sus productos.
