import cv2
from gestures import procesar_gestos

def main():
    # Initialize the webcam (1 for external/USB, 0 for default integrated)
    cap = cv2.VideoCapture(1)
    
    if not cap.isOpened():
        print("Critical error: Could not open the webcam.")
        return

    print("---- Facial Control System Started ----")
    print("Press the 'q' key in the video window to exit.")

    while True:
        ret, frame = cap.read()
        
        # If the camera fails or there is no frame, exit safely
        if not ret or frame is None:
            print("Warning: Invalid frame or camera disconnected.")
            break

        # Initialize a default copy to avoid assignment errors
        processed_frame = frame

        # Process gestures through our gesture module
        try:
            processed_frame = procesar_gestos(frame)
        except Exception as e:
            print(f"Error during gesture processing: {e}")

        # Display the processed frame on screen safely
        if processed_frame is not None and processed_frame.size > 0:
            cv2.imshow('Webcam - Facial Control', processed_frame)

        # Exit condition: press the 'q' key
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Release the camera and close all OpenCV windows properly
    cap.release()
    cv2.destroyAllWindows()
    print("---- System Closed Successfully ----")

if __name__ == "__main__":
    main()