# Resumidor de PDF con IA (todo gratis) - Estructura MVC

## Estructura de carpetas

    resumidor-pdf-mvc/
    ├── app.py                      Arranque del programa
    ├── configuracion.py            Claves de API y opciones
    ├── requirements.txt            Librerías que se instalan
    │
    ├── modelos/                    MODELO: datos y conexión con las APIs
    │   ├── lector_pdf.py           Lee el PDF: páginas, texto e imágenes (sin fondos negros)
    │   ├── servicio_gemini.py      Manda el PDF entero a Gemini y pide el resumen
    │   ├── servicio_imagenes.py    Crea imágenes con IA (Pollinations)
    │   └── imagen_portada.py       Recorta la imagen de la portada
    │
    ├── controladores/              CONTROLADOR: recibe el pedido y coordina
    │   └── resumen_controlador.py  Rutas "/", "/crear", "/resumir" y su avance
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
    │       ├── componentes.py      Títulos numerados, tarjetas, marcos de imagen, renglones
    │       ├── portada.py          Portada con foto, encabezado y pie de las páginas
    │       ├── mapa_conceptual.py  Mapa conceptual
    │       ├── graficos.py         Gráficos de barras, columnas y dona (colores propios)
    │       ├── documento.py        Arma el PDF: índice, secciones, figuras y soluciones
    │       └── fuentes/            Letras Poppins y Fraunces
    │
    └── utilidades/
        ├── ayudantes.py            Funciones pequeñas (tiempo de lectura, etc.)
        └── trabajos.py             Resúmenes en segundo plano con su avance (barra de progreso)

## Cómo funciona (MVC)
1. El usuario llena la página (VISTA: index.html + estilos.css + principal.js).
2. El CONTROLADOR (resumen_controlador.py) recibe el PDF y las opciones.
3. Los MODELOS leen el PDF, piden el resumen a Gemini y crean las imágenes.
   Gemini recibe el PDF completo, no solo su texto: lee también imágenes, diagramas,
   tablas, gráficos y páginas escaneadas o fotografiadas (un PDF de puras imágenes
   también se resume). Los PDF de más de 14 MB se suben aparte a Gemini y se borran
   de allá apenas termina el resumen.
   La cantidad de temas depende del documento (de 2 a 8): no se deja afuera ninguna parte
   importante, tampoco en el resumen para niños (que usa oraciones cortas pero conserva cifras,
   fechas y nombres).
4. El CONTROLADOR pasa los datos a la VISTA del PDF (vistas/pdf/documento.py).
5. El usuario descarga el PDF.

El resumen se hace en segundo plano: la página muestra una barra con el porcentaje y el paso
real («Gemini está leyendo el PDF…», «Creando la imagen 2 de 3…», «Armando el PDF…»). Si se
recarga o se cierra la pestaña, al volver la barra sigue y el PDF se descarga igual. Los
resúmenes terminados quedan una hora en el servidor.

## El PDF que se descarga
- Portada con foto de borde a borde (la que sube el usuario, con vista previa y recorte; si no
  sube, la mejor imagen del PDF que elige Gemini) y el título sobre un rectángulo violeta.
- Índice con páginas, secciones numeradas (01, 02…) y subtemas (3.1, 3.2…), encabezado con la
  sección actual y pie con barra de avance y «3 / 7».
- Tarjetas de ideas clave, la cifra más importante del documento, mapa conceptual.
- Imágenes junto al tema que ilustran, numeradas («Figura 1 ·») y con pie de foto.
- Gráficos con colores propios (no dependen del resaltador) y sin cortarse entre páginas.
- Preguntas con renglones para responder y una hoja final de soluciones y notas.

## Imágenes con IA
Con `POLLINATIONS_KEY` se usan los créditos gratis del día de Pollinations: MAI Image 2.6
(fotos realistas) para secundaria y adultos, y FLUX 1.1 Pro (ilustración) para niños. Si un
modelo falla o se acaban los créditos, se pasa solo al flux básico. Nunca se compra nada.
Nano Banana (las imágenes de Gemini) no se usa: por la API no tiene plan gratis.

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

Comando de arranque (ya viene en el `Procfile`): `gunicorn app:app --workers 1 --threads 8 --timeout 120`.
Tiene que ser **un solo worker**: el avance de cada resumen vive en la memoria de ese proceso
(con varios, la página podría preguntar a otro que no lo conoce).

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
