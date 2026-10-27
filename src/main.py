import cv2
from gestures import procesar_gestos

def main():
    # Se crea el objeto que representa la fuente de video
    camara = cv2.VideoCapture(1)            # Cambia a 0, 1 o 2 para seleccionar la cámara correcta

    # Si no se ha podido acceder a la fuente de video se sale del programa
    if not camara.isOpened():
        print("No es posible abrir la cámara")
        exit()

    while True:
        # Se captura la imagen frame a frame
        ret, frame = camara.read()

        # Si la captura no se ha tomado correctamente se sale del bucle
        if not ret:
            print("No es posible obtener la imagen")
            break

        # Procesar los gestos en el frame
        frame_procesado = procesar_gestos(frame)

        # El frame procesado se muestra en pantalla
        cv2.imshow('webcam', frame_procesado)

        if cv2.waitKey(1) == ord('q'):
            break

    # Se libera la cámara y se cierra la ventana
    camara.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()