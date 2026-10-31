# Control Assistivo de ordenador sin el uso de las manos

Este proyecto es una aplicación asistiva desarrollada en **Python** que permite controlar el ordenador mediante la webcam. La solución está diseñada de forma accesible y modular, adaptada para personas con movilidad reducida.

## Funcionamiento del Sistema

El sistema captura el flujo de vídeo de la webcam y procesa cada fotograma en tiempo real mediante los módulos `main.py` (bucle de captura y flujo principal) y `gestures.py` (lógica de visión clásica):

1. **Control del Cursor (Joystick Facial):**

   * Se localiza el centroide del rostro en el fotograma.

   * Se calcula el vector de desplazamiento respecto al centro de la cámara.

   * Se aplica una **zona muerta (Deadzone)** para mantener el cursor estático en posición neutra.

   * El cursor se desplaza fluidamente mediante `PyAutoGUI`, manteniendo **márgenes de seguridad** para evitar que se oculte fuera de los límites de la pantalla.

2. **Acciones de Clic por Guiño (Asimetría Ocular):**

   * Se extrae la Región de Interés (ROI) de la mitad superior del rostro y se aplica ecualización de histograma para corregir sombras.

   * Se detectan los ojos mediante clasificadores Haar.

   * **Guiño Izquierdo:** Al cerrar solo el ojo izquierdo durante $N$ fotogramas consecutivos, se ejecuta un **clic izquierdo**.

   * **Guiño Derecho:** Al cerrar solo el ojo derecho, se ejecuta un **clic derecho**.

3. **Efecto Visual con Protección por Mutex:**

   * Cada clic genera una animación transparente de onda expansiva en la posición del cursor mediante un hilo secundario en `Tkinter`.

   * Para evitar cierres inesperados (*crashes*) por concurrencia en `Tkinter`, el renderizado está protegido por una sección crítica con un **Mutex (`threading.Lock`)** no bloqueante.

4. **Scroll por Bordes (Edge Scrolling):**

   * Al llevar el cursor al borde superior o inferior de la pantalla y mantenerlo durante un tiempo determinado, se activa un desplazamiento vertical automático de página (`pyautogui.scroll`).

5. **Doble Apertura de Boca (Teclado Virtual):**

   * Se aísla el ROI inferior de la boca y se binariza mediante umbralización (`cv2.threshold`).

   * Se realiza un recuento de píxeles oscuros (`cv2.countNonZero`). Al detectar una **doble apertura rápida**, el sistema lanza el teclado en pantalla nativo de Windows (`osk.exe`).

6. **Modo Emoji (Detección de Sonrisa):**

   * Se analiza el ROI de la boca con un clasificador Haar de sonrisa (`haarcascade_smile.xml`).

   * Una sonrisa sostenida ejecuta la combinación de teclas `Win + .` para desplegar el panel de emojis.

## Librerías Utilizadas y Justificación

| Librería | Propósito y Justificación | 
| ----- | ----- | 
| **`opencv-python` (`cv2`)** | Captura de vídeo, procesamiento de matrices de imagen, conversión de espacios de color, clasificadores Haar clásicos y filtrado. | 
| **`numpy`** | Operaciones matemáticas sobre matrices de píxeles, cálculo de desplazamientos vectores, signos y delimitación de bordes (*clamping*). | 
| **`pyautogui`** | Automatización gráfica del sistema: control posicional del ratón, simulación de clics, scroll y combinaciones de teclas. | 
| **`winsound`** | Reproducción asíncrona de efectos de audio nativos (`click.wav`) y notificaciones sonoras en Windows. | 
| **`threading`** | Ejecución asíncrona de efectos visuales flotantes sin bloquear el bucle principal de captura de vídeo. | 
| **`tkinter`** | Renderizado de ventanas flotantes sin bordes y con canal alfa para mostrar la onda expansiva del clic. | 
| **`os` / `sys`** | Interacción con el sistema operativo (ejecución de `osk` para el teclado virtual y comprobación de plataforma). | 

## Funciones de OpenCV (`cv2`) y Aplicación en el Proyecto

Todas las funciones utilizadas pertenecen al catálogo de procesamiento de imágenes clásico:

| Función de OpenCV | Acción en el Proyecto | 
| ----- | ----- | 
| `cv2.VideoCapture()` | Inicialización y adquisición del flujo de vídeo de la webcam. | 
| `cv2.flip(frame, 1)` | Inversión horizontal de la imagen para crear el efecto espejo intuitivo. | 
| `cv2.cvtColor()` | Conversión de la imagen BGR a escala de grises (`COLOR_BGR2GRAY`) para el procesamiento matricial. | 
| `cv2.CascadeClassifier()` | Carga de los modelos XML clásicos de Viola-Jones (`frontalface`, `eye`, `smile`). | 
| `detectMultiScale()` | Detección multiescala de rostros, ojos y sonrisas dentro de las Regiones de Interés (ROI). | 
| `cv2.equalizeHist()` | Ecualización del histograma en los ROI de ojos y boca para normalizar la iluminación y mejorar el contraste. | 
| `cv2.threshold()` | Binarización invertida (`THRESH_BINARY_INV`) del ROI de la boca para aislar la cavidad bucal. | 
| `cv2.countNonZero()` | Conteo de píxeles oscuros binarizados para medir cuantitativamente el área de apertura de la boca. | 
| `cv2.rectangle()` | Dibujado de cajas delimitadoras (*bounding boxes*) de la cara, ojos y boca sobre el frame visual. | 
| `cv2.putText()` | Renderizado del panel HUD en pantalla con contadores, alertas y estados de la aplicación. | 
| `cv2.imshow()` | Despliegue de la ventana gráfica con el fotograma procesado. | 
| `cv2.waitKey()` | Captura de eventos de teclado en tiempo real (ej. tecla `'q'` para salir). | 

## Instalación y Ejecución

### 1. Creación e Instalación del Entorno Virtual

Abre tu terminal en la carpeta del proyecto y ejecuta:

```
# Crear el entorno virtual
python -m venv venv

# Activar el entorno virtual (Windows)
.\venv\Scripts\activate

# Actualizar pip e instalar dependencias
python -m pip install --upgrade pip
pip install -r requirements.txt


```

### 2. Ejecución de la Aplicación

Con el entorno virtual activo `(venv)`, ejecuta:

```
python main.py


```

## 📁 Estructura del Proyecto

```
├── main.py              # Bucle principal de captura y control de ventana
├── gestures.py          # Módulo de procesamiento de visión clásica y gestos
├── requirements.txt     # Lista de dependencias del proyecto
├── haarcascades/        # Clasificadores XML clásicos de OpenCV
│   ├── haarcascade_frontalface_default.xml
│   ├── haarcascade_eye.xml
│   └── haarcascade_smile.xml
└── SoundEffects/        # Efectos de sonido de la interfaz
    └── click.wav


```