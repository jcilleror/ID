import cv2
import numpy as np
import pyautogui

# Seguridad de PyAutoGUI: si mueves el ratón a la esquina superior izquierda, se frena de emergencia
pyautogui.FAILSAFE = True

# Cargar clasificadores clásicos usando la ruta interna nativa de OpenCV
face_cascade = cv2.CascadeClassifier('./haarcascades/haarcascade_frontalface_default.xml')
eye_cascade = cv2.CascadeClassifier('./haarcascades/haarcascade_eye.xml')

# Variables de control para evitar clics múltiples descontrolados
contador_ojo_izq = 0
contador_ojo_der = 0
UMBRAL_FRAMES = 6  # Fotogramas consecutivos necesarios para confirmar el guiño

def procesar_gestos(frame):
    """
    Procesa el frame usando visión clásica para detectar guiños
    y ejecutar clics izquierdo y derecho con PyAutoGui.
    """
    global contador_ojo_izq, contador_ojo_der

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
        
        # Zonas muertas (Deadzone): Si el movimiento es muy pequeño, ignorarlo para que no tiemble en el centro
        ZONA_MUERTA_X = 30
        ZONA_MUERTA_Y = 20 
        
        vel_x = 0
        vel_y = 0
        
        if abs(desplazamiento_x) > ZONA_MUERTA_X:
            # Multiplicador de velocidad
            vel_x = int((desplazamiento_x - np.sign(desplazamiento_x) * ZONA_MUERTA_X) * 0.75)
            
        if abs(desplazamiento_y) > ZONA_MUERTA_Y:
            vel_y = int((desplazamiento_y - np.sign(desplazamiento_y) * ZONA_MUERTA_Y) * 0.75)
            
        # Mover el ratón de forma relativa (acumulando velocidad)
        if vel_x != 0 or vel_y != 0:
            pyautogui.moveRel(vel_x, vel_y, duration=0.0)
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
                    cv2.putText(frame, "¡CLICK IZQUIERDO EJECUTADO!", (50, 90), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                    contador_ojo_izq = 0

    return frame