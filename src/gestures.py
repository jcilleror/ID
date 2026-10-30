import os
import cv2
import numpy as np
import pyautogui
import winsound
import threading
import tkinter as tk

# Seguridad de PyAutoGUI: si mueves el ratón a la esquina superior izquierda, se frena de emergencia
#pyautogui.FAILSAFE = True

# Cargar clasificadores clásicos usando la ruta interna nativa de OpenCV
face_cascade = cv2.CascadeClassifier('./haarcascades/haarcascade_frontalface_default.xml')
eye_cascade = cv2.CascadeClassifier('./haarcascades/haarcascade_eye.xml')
smile_cascade = cv2.CascadeClassifier('./haarcascades/haarcascade_smile.xml')

# Variables de control para evitar clics múltiples descontrolados
contador_ojo_izq = 0
contador_ojo_der = 0
UMBRAL_FRAMES = 6  # Fotogramas consecutivos necesarios para confirmar el guiño

# Variables de control para el scroll por bordes
contador_edge_scroll = 0
UMBRAL_EDGE_SCROLL = 20  # Fotogramas que se debe mantener el ratón en el borde para que salte el scroll

# Variables de control para la doble apertura de boca (Teclado)
contador_aperturas_boca = 0
boca_estaba_abierta = False
frames_desde_ultima_apertura = 0
UMBRAL_VENTANA_DOBLE = 45  # Fotogramas máximos permitidos entre la 1ª y la 2ª apertura
MARCA_BOCA_ABIERTA = 2200   # Umbral de píxeles oscuros para considerar la boca abierta

# Variables de control para el Modo Emoji (Sonrisa -> Panel Windows + .)
contador_sonrisa = 0
UMBRAL_SONRISA_FRAMES = 12  # Fotogramas consecutivos de sonrisa para confirmar
emoji_bloqueado = False     # Mecanismo de un solo uso hasta relajar la cara


def mostrar_efecto_clic(x, y, tipo="left"):
    """
    Reproduce un sonido de clic y muestra una animación de onda expansiva 
    transparente en las coordenadas exactas (x, y) de la pantalla.
    """
    # 1. Reproducir sonido de clic de forma asíncrona
    try:
        winsound.PlaySound('./SoundEffects/click.wav', winsound.SND_FILENAME | winsound.SND_ASYNC)
    except Exception as e:
        pass  # Si falta el archivo de audio, el programa sigue funcionando

    # 2. Función interna para crear la animación de la onda expansiva
    def dibujar_circulo():
        try:
            root = tk.Tk()
            root.overrideredirect(True)  # Sin bordes ni barra de título
            root.attributes('-topmost', True)  # Siempre visible por encima de otras ventanas
            
            # Definir el color transparente (Croma Key)
            color_transparente = '#000001'
            root.config(bg=color_transparente)
            root.attributes('-transparentcolor', color_transparente)
            
            # Tamaño de la ventana flotante (100x100 píxeles para dar espacio a la expansión)
            tam = 100
            root.geometry(f"{tam}x{tam}+{int(x - tam/2)}+{int(y - tam/2)}")
            
            canvas = tk.Canvas(root, width=tam, height=tam, highlightthickness=0, bg=color_transparente)
            canvas.pack()

            # Color del anillo (Cian para izquierdo, Naranja para derecho)
            color_anillo = "#00E5FF" if tipo == "left" else "#FF6D00"
            cx, cy = tam // 2, tam // 2

            # Función recursiva para animar el crecimiento de las ondas
            def animar_onda(step=0):
                max_steps = 10  # Número total de fotogramas de la animación
                if step < max_steps:
                    canvas.delete("all")  # Limpiar el fotograma anterior
                    
                    # Radio de la onda principal (crece en cada paso)
                    r1 = 4 + step * 3.5
                    grosor = max(1, int(3 - step * 0.15))
                    canvas.create_oval(cx - r1, cy - r1, cx + r1, cy + r1, outline=color_anillo, width=grosor)
                    
                    # Segunda onda desfasada para dar efecto de ondas múltiples
                    if step >= 3:
                        r2 = 4 + (step - 3) * 3.5
                        canvas.create_oval(cx - r2, cy - r2, cx + r2, cy + r2, outline=color_anillo, width=1)
                        
                    # Programar el siguiente fotograma en 18 milisegundos
                    root.after(185 // max_steps, lambda: animar_onda(step + 1))
                else:
                    root.destroy()  # Cerrar la ventana al terminar la animación

            # Iniciar la animación
            animar_onda(0)
            root.mainloop()
        except Exception:
            pass

    # Lanzar el efecto visual en un hilo separado para que sea instantáneo y fluido
    threading.Thread(target=dibujar_circulo, daemon=True).start()



def procesar_gestos(frame):
    """
    Procesa el frame usando visión clásica para detectar guiños
    y ejecutar clics izquierdo y derecho con PyAutoGui.
    """
    global contador_ojo_izq, contador_ojo_der, contador_edge_scroll
    global contador_aperturas_boca, boca_estaba_abierta, frames_desde_ultima_apertura
    global contador_sonrisa, emoji_bloqueado

    # Aplicar efecto espejo para corregir la inversión de la cámara
    frame = cv2.flip(frame, 1)
    h_frame, w_frame, _ = frame.shape
    
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    # 1. Detección de Rostro (Clásico Haar Cascade)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.3, minNeighbors=5)
    
    for (x, y, w, h) in faces:
        # Dibujar rectángulo de la cara
        cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)


        # --- MOVIMIENTO DEL RATÓN BASADO EN EL CENTRO DE LA CARA/NARIZ (JOYSTICK) ---
        centro_x = x + w // 2
        centro_y = y + h // 2
        
        # Centro de la pantalla de la cámara (punto neutro)
        centro_frame_x = w_frame // 2
        centro_frame_y = h_frame // 2
        
        # Calcular la distancia (desplazamiento) respecto al centro neutro
        desplazamiento_x = centro_x - centro_frame_x
        desplazamiento_y = centro_y - centro_frame_y
        
        # Zonas muertas (Deadzone): Si el movimiento es muy pequeño, ignorarlo
        ZONA_MUERTA_X = 25
        ZONA_MUERTA_Y = 10 
        
        vel_x = 0
        vel_y = 0
        
        if abs(desplazamiento_x) > ZONA_MUERTA_X:
            vel_x = int((desplazamiento_x - np.sign(desplazamiento_x) * ZONA_MUERTA_X) * 1.25)
            
        if abs(desplazamiento_y) > ZONA_MUERTA_Y:
            vel_y = int((desplazamiento_y - np.sign(desplazamiento_y) * ZONA_MUERTA_Y) * 1.25)
            
        # Mover el ratón asegurando que nunca se salga de los límites de la pantalla
        if vel_x != 0 or vel_y != 0:
            screen_w, screen_h = pyautogui.size()
            curr_x, curr_y = pyautogui.position()
            
            # Margen de seguridad para que el ratón nunca llegue a 0 ni al máximo exacto
            MARGEN_LIMITE = 10
            
            nuevo_x = curr_x + vel_x
            nuevo_y = curr_y + vel_y
            
            # Restringir (Clamp) los valores para que no puedan salir del área segura de la pantalla
            nuevo_x = max(MARGEN_LIMITE, min(screen_w - MARGEN_LIMITE, nuevo_x))
            nuevo_y = max(MARGEN_LIMITE, min(screen_h - MARGEN_LIMITE, nuevo_y))
            
            # Mover de forma absoluta a la posición controlada
            pyautogui.moveTo(nuevo_x, nuevo_y, duration=0.0)
        # ----------------------------------------------------------------
        

        # Región de interés (ROI) para los ojos (mitad superior de la cara)
        roi_gray = gray[y:y + int(h/2), x:x + w]
        roi_color = frame[y:y + int(h/2), x:x + w]

        # Mejora: Ecualizar el histograma para mejorar el contraste lumínico
        roi_gray = cv2.equalizeHist(roi_gray)
        
        # 2. Detección de Ojos
        eyes = eye_cascade.detectMultiScale(roi_gray, scaleFactor=1.1, minNeighbors=4)
        
        # Ordenar los ojos detectados horizontalmente por su coordenada X (ex)
        eyes = sorted(eyes, key=lambda e: e[0])
        
        # Lógica basada en el número de ojos detectados
        if len(eyes) >= 2:
            # Si se detectan 2 ojos, se reinician los contadores (ojos abiertos)
            contador_ojo_izq = 0
            contador_ojo_der = 0
            for (ex, ey, ew, eh) in eyes:
                cv2.rectangle(roi_color, (ex, ey), (ex + ew, ey + eh), (0, 255, 0), 2)

        elif len(eyes) == 0:
            # Si no se ve ningún ojo (mirando hacia otro lado o parpadeo total), 
            # reseteamos contadores para evitar clics accidentales por giros
            contador_ojo_izq = 0
            contador_ojo_der = 0
            cv2.putText(frame, "Ojos no detectados", (50, 50), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (128, 128, 128), 2)

        elif len(eyes) == 1:
            # Solo se detecta un ojo, el otro está cerrado (potencial guiño)
            ex, ey, ew, eh = eyes[0]
            cv2.rectangle(roi_color, (ex, ey), (ex + ew, ey + eh), (0, 255, 255), 2)
            
            # Analizar en qué mitad de la cara está el ojo visible para saber cuál falta
            centro_ojo_x = ex + ew / 2
            ancho_mitad_cara = w / 2
            
            if centro_ojo_x < ancho_mitad_cara:
                # Falta el ojo derecho (desde la perspectiva de la cámara)
                contador_ojo_der += 1
                contador_ojo_izq = 0
                cv2.putText(frame, f"Guiño Derecho ({contador_ojo_der})", (50, 50), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)
                
                if contador_ojo_der == UMBRAL_FRAMES:
                    pyautogui.click(button='right')  # Clic derecho
                    
                    # Obtener una posición actual del cursor para mostrar el efecto visual del clic derecho
                    rx, ry = pyautogui.position()
                    mostrar_efecto_clic(rx, ry, tipo="right")
                    
                    cv2.putText(frame, "¡CLICK DERECHO EJECUTADO!", (50, 90), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                    contador_ojo_der = 0
            else:
                # Falta el ojo izquierdo
                contador_ojo_izq += 1
                contador_ojo_der = 0
                cv2.putText(frame, f"Guiño Izquierdo ({contador_ojo_izq})", (50, 50), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
                
                if contador_ojo_izq == UMBRAL_FRAMES:
                    pyautogui.click(button='left')   # Clic izquierdo

                    # Obtener una posición actual del cursor para mostrar el efecto visual del clic izquierdo
                    lx, ly = pyautogui.position()
                    mostrar_efecto_clic(lx, ly, tipo="left")

                    cv2.putText(frame, "¡CLICK IZQUIERDO EJECUTADO!", (50, 90), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                    contador_ojo_izq = 0


        # --- 3. SCROLL POR BORDES (EDGE SCROLLING) ---
        # Obtener dimensiones de la pantalla y posición actual del cursor global
        screen_w, screen_h = pyautogui.size()
        mouse_x, mouse_y = pyautogui.position()
        
        MARGEN_BORDE = 60  # Píxeles de tolerancia desde el borde superior/inferior
        
        if mouse_y < MARGEN_BORDE:
            # El ratón está tocando el borde superior de la pantalla
            contador_edge_scroll += 1
            cv2.putText(frame, f"Cargando Scroll Arriba ({contador_edge_scroll}/{UMBRAL_EDGE_SCROLL})", (50, 130), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            if contador_edge_scroll >= UMBRAL_EDGE_SCROLL:
                pyautogui.scroll(250)  # Positivo = Subir página
                cv2.putText(frame, "¡SCROLL ARRIBA EJECUTADO!", (50, 170), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                contador_edge_scroll = 0  # Reiniciar contador para permitir scroll continuo
                
        elif mouse_y > screen_h - MARGEN_BORDE:
            # El ratón está tocando el borde inferior de la pantalla
            contador_edge_scroll += 1
            cv2.putText(frame, f"Cargando Scroll Abajo ({contador_edge_scroll}/{UMBRAL_EDGE_SCROLL})", (50, 130), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            
            if contador_edge_scroll >= UMBRAL_EDGE_SCROLL:
                pyautogui.scroll(-250)  # Negativo = Bajar página
                cv2.putText(frame, "¡SCROLL ABAJO EJECUTADO!", (50, 170), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                contador_edge_scroll = 0
        else:
            # Si el ratón está en el centro o zona segura, reseteamos el contador
            contador_edge_scroll = 0



        # --- 4. DETECCIÓN DE DOBLE APERTURA DE BOCA (LANZAR TECLADO DE WINDOWS) ---
        boca_y1 = y + int(h * 0.65)
        boca_y2 = y + h
        boca_x1 = x + int(w * 0.25)
        boca_x2 = x + int(w * 0.75)
        
        roi_boca_gray = gray[boca_y1:boca_y2, boca_x1:boca_x2]
        roi_boca_color = frame[boca_y1:boca_y2, boca_x1:boca_x2]
        
        roi_boca_gray = cv2.equalizeHist(roi_boca_gray)
        _, thresh_boca = cv2.threshold(roi_boca_gray, 30, 255, cv2.THRESH_BINARY_INV)
        
        area_boca_abierta = cv2.countNonZero(thresh_boca)
        cv2.rectangle(frame, (boca_x1, boca_y1), (boca_x2, boca_y2), (0, 255, 255), 1)
        
        # Control de la ventana de tiempo entre aperturas
        if contador_aperturas_boca > 0:
            frames_desde_ultima_apertura += 1
            if frames_desde_ultima_apertura > UMBRAL_VENTANA_DOBLE:
                # Si pasa demasiado tiempo, se reinicia el contador de doble gesto
                contador_aperturas_boca = 0
                frames_desde_ultima_apertura = 0

        # Determinar si la boca está abierta en este fotograma exacto
        boca_actualmente_abierta = (area_boca_abierta > MARCA_BOCA_ABIERTA)
        
        # Detectar el "flanco de subida" (el momento exacto en que se abre la boca)
        if boca_actualmente_abierta and not boca_estaba_abierta:
            contador_aperturas_boca += 1
            frames_desde_ultima_apertura = 0
            
            cv2.putText(frame, f"Gesto Boca ({contador_aperturas_boca}/2)", (50, 130), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            
            if contador_aperturas_boca == 2:
                # ¡Doble apertura confirmada! Lanzar el teclado nativo de Windows (OSK)
                try:
                    os.system("start osk")
                except Exception:
                    pass
                
                cv2.putText(frame, "¡TECLADO DE WINDOWS ACTIVADO!", (50, 170), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                
                # Reiniciar contadores tras la acción
                contador_aperturas_boca = 0
                frames_desde_ultima_apertura = 0
                
        # Actualizar el estado anterior de la boca
        boca_estaba_abierta = boca_actualmente_abierta



        # --- 5. MODO EMOJI: ABRIR PANEL DE WINDOWS CON UNA SONRISA ---
        # Analizar la mitad inferior de la cara para detectar la sonrisa
        roi_gray_cara_inferior = gray[y + int(h*0.5):y + h, x:x + w]
        roi_color_cara_inferior = frame[y + int(h*0.5):y + h, x:x + w]
        
        smiles = smile_cascade.detectMultiScale(roi_gray_cara_inferior, scaleFactor=1.7, minNeighbors=22, minSize=(30, 30))
        
        if len(smiles) > 0:
            if not emoji_bloqueado:
                contador_sonrisa += 1
                cv2.putText(frame, f"Cargando Panel Emojis ({contador_sonrisa}/{UMBRAL_SONRISA_FRAMES})", (50, 210), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                
                if contador_sonrisa >= UMBRAL_SONRISA_FRAMES:
                    # ¡Sonrisa confirmada! Pulsar simultáneamente Windows + .
                    try:
                        pyautogui.hotkey('win', '.')
                    except Exception:
                        pass
                    
                    cv2.putText(frame, "¡PANEL DE EMOJIS ACTIVADO!", (50, 250), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                    
                    # Bloquear para que no se abra en bucle hasta que dejes de sonreír
                    emoji_bloqueado = True
                    contador_sonrisa = 0
        else:
            # Si el usuario relaja la cara, reseteamos el bloqueo para futuras aperturas
            contador_sonrisa = 0
            emoji_bloqueado = False

    return frame