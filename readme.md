# Sistema Asistivo de Control Facial por Visión Computacional Clásica

Desarrollado por **Víctor Serrano Pérez** y **Justo Cilleros Rodríguez**.

Este proyecto es una aplicación asistiva desarrollada en **Python** que permite controlar íntegramente el ordenador (movimiento del cursor, clics, arrastrar y soltar, teclado virtual, panel de emojis, scroll por bordes y modo reposo) mediante una cámara web estándar. Diseñada con técnicas exclusivas de visión computacional clásica y APIs nativas del sistema operativo, ofrece una solución accesible para personas con movilidad reducida.

---

## Características Principales y Funcionamiento del Sistema

El sistema captura el flujo de vídeo de la webcam y procesa los fotogramas en tiempo real mediante una arquitectura de dos módulos: `main.py` (bucle de captura, gestión de ventana y control de excepciones) y `gestures.py` (tubería de procesamiento de visión clásica y automatización gráfica):

1. **Joystick Facial (Movimiento del Cursor):**
   * Se aísla únicamente el rostro principal (el de mayor área detectada) para ignorar interferencias o personas en segundo plano.
   * Se calcula el vector de desplazamiento del centroide facial respecto al centro de la cámara.
   * Se aplica una **zona muerta (Deadzone)** para mantener el cursor estático en posición neutra.
   * El cursor se desplaza fluidamente mediante `PyAutoGUI`, manteniendo **márgenes de seguridad** para evitar que se oculte fuera de los límites de la pantalla.

2. **Acciones de Clic por Guiño (Asimetría Ocular):**
   * Se extrae la Región de Interés (ROI) de la mitad superior del rostro y se aplica ecualización de histograma para corregir sombras e iluminación.
   * Se evalúan las detecciones de ojos mediante clasificadores Haar.
   * **Guiño Izquierdo:** Al cerrar solo el ojo izquierdo durante $N$ fotogramas consecutivos, se ejecuta un **clic izquierdo**.
   * **Guiño Derecho:** Al cerrar solo el ojo derecho, se ejecuta un **clic derecho**.

3. **Efecto Visual con Protección por Mutex:**
   * Cada clic activa la reproducción asíncrona de un sonido (`click.wav`) y muestra una animación transparente de onda expansiva en la posición del cursor.
   * La interfaz del overlay se ejecuta en un hilo secundario en `Tkinter`, protegida por una sección crítica con un **Mutex (`threading.Lock`)** para evitar cierres por concurrencia.

4. **Ojos Cerrados Sostenidos (Modo Drag & Drop / Arrastre):**
   * Cerrar ambos ojos de forma sostenida alternar el estado del botón del ratón (`mouseDown` / `mouseUp`).
   * Mientras el modo de arrastre está activo, **se bloquean estrictamente las acciones secundarias** (clics, teclado, emojis, scroll) para evitar ejecuciones accidentales durante el desplazamiento.

5. **Doble Apertura de Boca (Teclado Virtual):**
   * Se aísla el ROI inferior de la boca, aplicando un suavizado Gaussian Blur y binarización invertida (`cv2.threshold`).
   * Mediante la extracción de contornos (`cv2.findContours`) y su rectángulo delimitador (`cv2.boundingRect`), se mide el ratio de apertura de la cavidad bucal. Una **doble apertura rápida** lanza el teclado en pantalla nativo del sistema operativo (`osk.exe` en Windows, Teclado de Accesibilidad en macOS).

6. **Sonrisa Sostenida (Panel de Emojis):**
   * Se analiza la zona inferior de la cara con un clasificador Haar de sonrisa (`haarcascade_smile.xml`).
   * Una sonrisa sostenida ejecuta el atajo nativo (`Win + .` en Windows, `Ctrl + Cmd + Espacio` en macOS).

7. **Boca Abierta Sostenida (Modo Reposo / Pausa):**
   * Mantener la boca abierta durante \~2 segundos conmuta el estado global de pausa del sistema, desactivando el seguimiento y el cursor hasta su reactivación.

---

## Librerías Utilizadas y Justificación

| Librería | Propósito y Justificación |
| :--- | :--- |
| **`opencv-python` (`cv2`)** | Captura de vídeo, operaciones matriciales sobre imágenes, conversión de espacios de color, clasificadores Haar clásicos y umbralizado. |
| **`numpy`** | Operaciones matemáticas sobre matrices de píxeles, cálculo de desplazamientos vectoriales, signos y delimitación de bordes (*clamping*). |
| **`pyautogui`** | Automatización gráfica del sistema: control posicional del ratón, simulación de clics, scroll y atajos de teclado. |
| **`winsound`** | Reproducción asíncrona de efectos de audio nativos (`click.wav`) y tonos de estado en Windows. |
| **`threading`** | Ejecución asíncrona del motor de Tkinter para los efectos visuales flotantes sin bloquear el bucle principal de visión. |
| **`tkinter`** | Renderizado de overlays transparentes sin bordes para mostrar la onda expansiva del clic. |
| **`os` / `platform`** | Detección de la plataforma (Windows / macOS) y ejecución de herramientas nativas del sistema operativo. |

---

## Referencia de Funciones de OpenCV (`cv2`)

| Función de OpenCV | Aplicación en el Proyecto |
| :--- | :--- |
| `cv2.VideoCapture()` | Inicialización y adquisición del flujo de vídeo de la cámara web. |
| `cv2.flip(frame, 1)` | Inversión horizontal de la imagen para lograr un efecto espejo intuitivo. |
| `cv2.cvtColor()` | Conversión del fotograma BGR a escala de grises (`COLOR_BGR2GRAY`) para la extracción de características. |
| `cv2.CascadeClassifier()` | Carga de los modelos XML clásicos de Viola-Jones (`frontalface`, `eye`, `smile`). |
| `detectMultiScale()` | Detección multiescala de rostros, ojos y sonrisas dentro de las Regiones de Interés (ROI). |
| `cv2.equalizeHist()` | Normalización del contraste e iluminación en las regiones oculares. |
| `cv2.GaussianBlur()` | Suavizado del ROI de la boca para eliminar ruido de alta frecuencia previo al umbralizado. |
| `cv2.threshold()` | Binarización invertida (`THRESH_BINARY_INV`) para aislar visualmente la cavidad bucal. |
| `cv2.findContours()` | Extracción de contornos externos sobre la máscara binaria de la boca. |
| `cv2.boundingRect()` | Cálculo del rectángulo delimitador para medir cuantitativamente la altura vertical de la apertura bucal. |
| `cv2.rectangle()` | Dibujado de cajas delimitadoras con colores dinámicos según el estado del sistema (Normal, Pausa, Arrastre). |
| `cv2.putText()` | Renderizado del panel HUD en pantalla con contadores, estados e información en tiempo real. |
| `cv2.imshow()` | Despliegue de la ventana gráfica con el fotograma procesado. |
| `cv2.waitKey()` | Captura de eventos de teclado en tiempo real (ej. tecla `'q'` para salir). |

---

## Retos y Limitaciones Conocidas

1. **Sensibilidad a la Iluminación Ambiental:** Al estar basado en clasificadores Haar clásicos, cambios bruscos en la luz de la habitación o sombras intensas en el rostro pueden reducir temporalmente la precisión en la detección de ojos o guiños.
2. **Límites de Privilegios del Sistema (UIPI en Windows):** La simulación de eventos de ratón sobre ventanas protegidas del sistema (como el teclado virtual `osk.exe`) requiere ejecutar la terminal o el entorno de desarrollo con **permisos de Administrador**.

---

## Instalación y Configuración

### 1. Creación e Instalación del Entorno Virtual

```bash
# Crear el entorno virtual
python -m venv venv

# Activar el entorno virtual (Windows)
.\venv\Scripts\activate

# Activar el entorno virtual (macOS/Linux)
source venv/bin/activate

# Actualizar pip e instalar dependencias
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 2. Ejecución de la Aplicación

Ejecuta `main.py` (recuerda hacerlo con privilegios de Administrador para habilitar la interacción total con herramientas del sistema):

```bash
python main.py
```

---

## Estructura del Repositorio

```text
├── main.py              # Bucle principal de captura y control de ventana
├── gestures.py          # Módulo de procesamiento de visión clásica y lógica de gestos
├── requirements.txt     # Manifiesto de dependencias optimizado
├── README.md            # Documentación técnica del proyecto
├── haarcascades/        # Clasificadores XML preentrenados de OpenCV
│   ├── haarcascade_frontalface_default.xml
│   ├── haarcascade_eye.xml
│   └── haarcascade_smile.xml
└── SoundEffects/        # Recursos de audio para la interfaz
    └── click.wav
```