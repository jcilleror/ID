import os
import platform
import cv2
import numpy as np
import pyautogui
import winsound
import threading
import tkinter as tk

# ------------------------------------------
# CONFIGURATION & SAFETY SETTINGS
# ------------------------------------------
pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.0

# Mutex to protect critical sections in Tkinter animations and prevent concurrency crashes
click_effect_lock = threading.Lock()

# Single and permanent Tkinter thread to avoid multithreading errors
tk_root = None
tk_ready = threading.Event()

def initialize_tkinter_loop():
    global tk_root
    try:
        tk_root = tk.Tk()
        tk_root.withdraw()  # Hide the main root window
        tk_ready.set()
        tk_root.mainloop()
    except Exception:
        pass

# Start the Tkinter graphical engine in a dedicated background thread
threading.Thread(target=initialize_tkinter_loop, daemon=True).start()

# Load classical Haar Cascade classifiers for face, eye, and smile detection
face_cascade = cv2.CascadeClassifier('./haarcascades/haarcascade_frontalface_default.xml')
eye_cascade = cv2.CascadeClassifier('./haarcascades/haarcascade_eye.xml')
smile_cascade = cv2.CascadeClassifier('./haarcascades/haarcascade_smile.xml')

# ------------------------------------------
# CONTROL VARIABLES & THRESHOLDS
# ------------------------------------------
# Eye blink / click tracking variables
left_eye_counter = 0
right_eye_counter = 0
FRAME_THRESHOLD = 6  # Consecutive frames required to confirm a wink
ojo_izq_bloqueado = False
ojo_der_bloqueado = False

# Edge scrolling control variables
edge_scroll_counter = 0
EDGE_SCROLL_THRESHOLD = 8  # Consecutive frames at the screen edge to trigger scroll

# Double mouth opening control variables (Virtual Keyboard)
mouth_opening_counter = 0
mouth_was_open = False
frames_since_last_opening = 0
DOUBLE_OPEN_WINDOW_THRESHOLD = 45  # Max frames allowed between 1st and 2nd mouth opening

# Emoji panel control variables (Sustained smile)
smile_counter = 0
SMILE_FRAME_THRESHOLD = 25  # Consecutive frames of smiling to confirm
emoji_locked = False        # Single-use mechanism until face relaxes

# System pause / sleep control variables (Sustained open mouth)
system_paused = False
sustained_open_mouth_counter = 0
PAUSE_MOUTH_THRESHOLD = 60  # Consecutive frames with mouth open to toggle pause (~2 seconds)

# Drag & Drop control variables (Sustained closed eyes)
drag_active = False
drag_closed_eyes_counter = 0
DRAG_FRAME_THRESHOLD = 60  # Consecutive frames with eyes closed to toggle drag/drop (~1 second)


# ------------------------------------------
# GRAPHICAL FEEDBACK & UTILITIES
# ------------------------------------------
def show_click_effect(x, y, click_type="left"):
    """
    Plays a click sound and displays a transparent expanding ripple animation 
    at exact screen coordinates (x, y). Protected with a Mutex.
    """
    try:
        winsound.PlaySound('./SoundEffects/click.wav', winsound.SND_FILENAME | winsound.SND_ASYNC)
    except Exception:
        pass  

    if not tk_ready.is_set() or tk_root is None:
        return

    def create_overlay():
        if not click_effect_lock.acquire(blocking=False):
            return

        try:
            top = tk.Toplevel(tk_root)
            top.overrideredirect(True)        
            top.attributes('-topmost', True) 
            
            transparent_color = '#000001'
            top.config(bg=transparent_color)
            top.attributes('-transparentcolor', transparent_color)
            
            size = 100
            top.geometry(f"{size}x{size}+{int(x - size/2)}+{int(y - size/2)}")
            
            canvas = tk.Canvas(top, width=size, height=size, highlightthickness=0, bg=transparent_color)
            canvas.pack()

            ring_color = "#00E5FF" if click_type == "left" else "#FF6D00"
            cx, cy = size // 2, size // 2

            def animate_ripple(step=0):
                max_steps = 10  
                if step < max_steps:
                    canvas.delete("all")  
                    r1 = 4 + step * 3.5
                    thickness = max(1, int(3 - step * 0.15))
                    canvas.create_oval(cx - r1, cy - r1, cx + r1, cy + r1, outline=ring_color, width=thickness)
                    
                    if step >= 3:
                        r2 = 4 + (step - 3) * 3.5
                        canvas.create_oval(cx - r2, cy - r2, cx + r2, cy + r2, outline=ring_color, width=1)
                        
                    top.after(18, lambda: animate_ripple(step + 1))
                else:
                    top.destroy()
                    click_effect_lock.release()

            animate_ripple(0)
        except Exception:
            click_effect_lock.release()

    tk_root.after(0, create_overlay)


# -----------------------------------------
# MAIN GESTURE PROCESSING PIPELINE
# -----------------------------------------
def procesar_gestos(frame):
    """
    Processes the webcam frame using classical computer vision to handle face tracking,
    mouse movement, clicks, edge scrolling, virtual keyboard, emojis, pause, and drag-and-drop.
    """
    if frame is None or frame.size == 0:
        return frame

    global left_eye_counter, right_eye_counter, edge_scroll_counter
    global mouth_opening_counter, mouth_was_open, frames_since_last_opening
    global smile_counter, emoji_locked
    global system_paused, sustained_open_mouth_counter
    global drag_active, drag_closed_eyes_counter

    # Apply mirror effect to correct camera inversion
    frame = cv2.flip(frame, 1)
    h_frame, w_frame, _ = frame.shape
    
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    # ------------------------------------------
    # 1. PRIMARY FACE DETECTION & MOUTH ANALYSIS
    # ------------------------------------------
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.3, minNeighbors=5)
    
    if len(faces) == 0:
        return frame

    # Select ONLY the primary face (the largest one by area, meaning closest to the camera)
    # This prevents any interference if another person or object appears in the background.
    primary_face = max(faces, key=lambda f: f[2] * f[3])
    x, y, w, h = primary_face

    # Dynamic face bounding box color (Red = Paused, Orange = Dragging, Blue = Normal)
    if system_paused:
        face_box_color = (0, 0, 255)
    elif drag_active:
        face_box_color = (0, 165, 255)
    else:
        face_box_color = (255, 0, 0)
        
    cv2.rectangle(frame, (x, y), (x + w, y + h), face_box_color, 2)

    # Region of Interest (ROI) for eyes within the primary face
    roi_gray = gray[y:y + int(h/2), x:x + w]
    roi_color = frame[y:y + int(h/2), x:x + w]
    roi_gray = cv2.equalizeHist(roi_gray)
    
    eyes = eye_cascade.detectMultiScale(roi_gray, scaleFactor=1.1, minNeighbors=4)

    # --- Robust mouth contour & cavity analysis ---
    mouth_y1 = y + int(h * 0.68)
    mouth_y2 = y + int(h * 0.93)
    mouth_x1 = x + int(w * 0.28)
    mouth_x2 = x + int(w * 0.72)
    
    roi_mouth_gray = gray[mouth_y1:mouth_y2, mouth_x1:mouth_x2]
    cv2.rectangle(frame, (mouth_x1, mouth_y1), (mouth_x2, mouth_y2), (0, 255, 255), 1)

    mouth_currently_open = False

    if roi_mouth_gray.shape[0] > 10 and roi_mouth_gray.shape[1] > 10:
        blur_mouth = cv2.GaussianBlur(roi_mouth_gray, (5, 5), 0)
        _, thresh_mouth = cv2.threshold(blur_mouth, 45, 255, cv2.THRESH_BINARY_INV)
        contours, _ = cv2.findContours(thresh_mouth, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        max_cavity_height = 0
        for c in contours:
            if cv2.contourArea(c) > 40:
                _, _, _, contour_h = cv2.boundingRect(c)
                if contour_h > max_cavity_height:
                    max_cavity_height = contour_h
        
        opening_ratio = max_cavity_height / float(h)
        mouth_currently_open = (opening_ratio > 0.08)

    # --- Pause / Sleep Mode (Sustained open mouth) ---
    if mouth_currently_open:
        sustained_open_mouth_counter += 1
        cv2.putText(frame, f"Loading Pause ({sustained_open_mouth_counter}/{PAUSE_MOUTH_THRESHOLD})", (50, 170), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)
        
        if sustained_open_mouth_counter >= PAUSE_MOUTH_THRESHOLD:
            system_paused = not system_paused
            sustained_open_mouth_counter = 0
            if system_paused and drag_active:
                try:
                    pyautogui.mouseUp(button='left')
                except Exception:
                    pass
                drag_active = False
            try:
                winsound.Beep(800 if system_paused else 1200, 200)
            except Exception:
                pass
    else:
        sustained_open_mouth_counter = 0

    # --- Skip all actions if system is paused ---
    if system_paused:
        cv2.putText(frame, "--- SYSTEM PAUSED ---", (50, 90), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        cv2.putText(frame, "Keep mouth open to reactivate", (50, 130), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        return frame

    # ------------------------------------------
    # 2. FACIAL JOYSTICK (MOUSE MOVEMENT)
    # ------------------------------------------
    face_center_x = x + w // 2
    face_center_y = y + h // 2
    
    frame_center_x = w_frame // 2
    frame_center_y = h_frame // 2
    
    offset_x = face_center_x - frame_center_x
    offset_y = face_center_y - frame_center_y
    
    DEADZONE_X = 25
    DEADZONE_Y = 10 
    
    cursor_vel_x = 0
    cursor_vel_y = 0
    
    if abs(offset_x) > DEADZONE_X:
        cursor_vel_x = int((offset_x - np.sign(offset_x) * DEADZONE_X) * 0.6)
        
    if abs(offset_y) > DEADZONE_Y:
        cursor_vel_y = int((offset_y - np.sign(offset_y) * DEADZONE_Y) * 0.6)
        
    if cursor_vel_x != 0 or cursor_vel_y != 0:
        screen_width, screen_height = pyautogui.size()
        curr_x, curr_y = pyautogui.position()
        
        SAFE_MARGIN = 10
        target_x = curr_x + cursor_vel_x
        target_y = curr_y + cursor_vel_y
        
        target_x = max(SAFE_MARGIN, min(screen_width - SAFE_MARGIN, target_x))
        target_y = max(SAFE_MARGIN, min(screen_height - SAFE_MARGIN, target_y))
        
        pyautogui.moveTo(target_x, target_y, duration=0.0)

    # ------------------------------------------
    # 3. EYES DETECTION, WINKS & DRAG AND DROP
    # ------------------------------------------
    eyes = sorted(eyes, key=lambda e: e[0])
    
    if len(eyes) == 0:
        # No eyes visible (Sustained closed eyes -> Drag & Drop)
        left_eye_counter = 0
        right_eye_counter = 0
        
        drag_closed_eyes_counter += 1
        drag_state_text = "Dropping..." if drag_active else "Grabbing..."
        cv2.putText(frame, f"Drag & Drop [{drag_state_text}] ({drag_closed_eyes_counter}/{DRAG_FRAME_THRESHOLD})", (50, 50), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)
        
        if drag_closed_eyes_counter >= DRAG_FRAME_THRESHOLD:
            drag_active = not drag_active
            try:
                if drag_active:
                    pyautogui.mouseDown(button='left')
                    winsound.Beep(1000, 150)
                else:
                    pyautogui.mouseUp(button='left')
                    winsound.Beep(600, 150)
            except Exception:
                pass
            drag_closed_eyes_counter = 0
            
    else:
        drag_closed_eyes_counter = 0

        # IF DRAG MODE IS ACTIVE, BLOCK ALL OTHER ACTIONS (CLICKS, KEYBOARD, EMOJIS, SCROLL)
        if drag_active:
            cv2.putText(frame, "--- DRAG MODE ACTIVE ---", (50, 50), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)
            mouth_was_open = mouth_currently_open
            return frame

        # --- Virtual Keyboard Trigger (Double mouth opening) ---
        if mouth_opening_counter > 0:
            frames_since_last_opening += 1
            if frames_since_last_opening > DOUBLE_OPEN_WINDOW_THRESHOLD:
                mouth_opening_counter = 0
                frames_since_last_opening = 0

        if mouth_currently_open and not mouth_was_open:
            mouth_opening_counter += 1
            frames_since_last_opening = 0
            
            cv2.putText(frame, f"Mouth Gesture ({mouth_opening_counter}/2)", (50, 130), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            
            if mouth_opening_counter == 2:
                try:
                    os_name = platform.system()
                    if os_name == 'Windows':
                        os.system("start osk")
                    elif os_name == 'Darwin':
                        os.system("open /System/Library/CoreServices/Applications/Accessibility\\ Keyboard.app")
                except Exception:
                    pass
                
                cv2.putText(frame, "--- VIRTUAL KEYBOARD ACTIVATED ---", (50, 170), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                
                mouth_opening_counter = 0
                frames_since_last_opening = 0
                
        mouth_was_open = mouth_currently_open

        # --- Eye Winks (Left / Right Clicks) ---
        if len(eyes) >= 2:
            left_eye_counter = 0
            right_eye_counter = 0
            ojo_izq_bloqueado = False
            ojo_der_bloqueado = False
            for (ex, ey, ew, eh) in eyes:
                cv2.rectangle(roi_color, (ex, ey), (ex + ew, ey + eh), (0, 255, 0), 2)

        elif len(eyes) == 1:
            ex, ey, ew, eh = eyes[0]
            cv2.rectangle(roi_color, (ex, ey), (ex + ew, ey + eh), (0, 255, 255), 2)
            
            eye_center_x = ex + ew / 2
            half_face_width = w / 2
            
            if eye_center_x < half_face_width:
                right_eye_counter += 1
                left_eye_counter = 0
                cv2.putText(frame, f"Right Click ({right_eye_counter})", (50, 50), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)
                
                if right_eye_counter == FRAME_THRESHOLD:
                    pyautogui.click(button='right')
                    rx, ry = pyautogui.position()
                    show_click_effect(rx, ry, click_type="right")
                    right_eye_counter = 0
                    ojo_der_bloqueado = True
            else:
                left_eye_counter += 1
                right_eye_counter = 0
                cv2.putText(frame, f"Left Click ({left_eye_counter})", (50, 50), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
                
                if left_eye_counter == FRAME_THRESHOLD:
                    pyautogui.click(button='left')
                    lx, ly = pyautogui.position()
                    show_click_effect(lx, ly, click_type="left")
                    left_eye_counter = 0
                    ojo_izq_bloqueado = True
        # ------------------------------------------
        # 4. EDGE SCROLLING
        # ------------------------------------------
        screen_width, screen_height = pyautogui.size()
        mouse_x, mouse_y = pyautogui.position()
        BORDER_MARGIN = 60
        
        if mouse_y < BORDER_MARGIN:
            edge_scroll_counter += 1
            cv2.putText(frame, f"Loading Scroll Up ({edge_scroll_counter}/{EDGE_SCROLL_THRESHOLD})", (50, 130), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            if edge_scroll_counter >= EDGE_SCROLL_THRESHOLD:
                pyautogui.scroll(500)
                edge_scroll_counter = 4
        elif mouse_y > screen_height - BORDER_MARGIN:
            edge_scroll_counter += 1
            cv2.putText(frame, f"Loading Scroll Down ({edge_scroll_counter}/{EDGE_SCROLL_THRESHOLD})", (50, 130), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            if edge_scroll_counter >= EDGE_SCROLL_THRESHOLD:
                pyautogui.scroll(-500)
                edge_scroll_counter = 4
        else:
            edge_scroll_counter = 0

        # ------------------------------------------
        # 5. EMOJI PANEL (SUSTAINED SMILE)
        # ------------------------------------------
        smile_y1 = y + int(h * 0.60)
        smile_y2 = y + int(h * 0.90)
        smile_x1 = x + int(w * 0.20)
        smile_x2 = x + int(w * 0.80)
        
        lower_face_roi = gray[smile_y1:smile_y2, smile_x1:smile_x2]
        # lower_face_roi = gray[y + int(h*0.5):y + h, x:x + w]

        smiles = smile_cascade.detectMultiScale(lower_face_roi, scaleFactor=1.1, minNeighbors=45, minSize=(45, 15))
        
        if len(smiles) > 0:
            if not emoji_locked:
                smile_counter += 1
                cv2.putText(frame, f"Loading Emoji Panel ({smile_counter}/{SMILE_FRAME_THRESHOLD})", (50, 210), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                
                if smile_counter >= SMILE_FRAME_THRESHOLD:
                    try:
                        os_name = platform.system()
                        if os_name == 'Windows':
                            pyautogui.hotkey('win', '.')
                        elif os_name == 'Darwin':
                            pyautogui.hotkey('ctrl', 'command', 'space')
                    except Exception:
                        pass
                    emoji_locked = True
                    smile_counter = 0
        else:
            smile_counter = 0
            emoji_locked = False

    return frame