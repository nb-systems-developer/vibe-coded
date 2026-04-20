import cv2
import mediapipe as mp
import numpy as np
import os

# Initialize MediaPipe Face Detection
mp_face_detection = mp.solutions.face_detection
face_detection = mp_face_detection.FaceDetection(model_selection=0, min_detection_confidence=0.5)

def save_face(name, face_img):
    data_file = 'faces_data.npz'
    faces = []
    names = []

    # Load existing data if it exists
    if os.path.exists(data_file):
        with np.load(data_file, allow_pickle=True) as data:
            faces = list(data['faces'])
            names = list(data['names'])

    faces.append(face_img)
    names.append(name)
    
    np.savez_compressed(data_file, faces=faces, names=names)
    print(f"✅ Successfully enrolled {name}!")

def main():
    cap = cv2.VideoCapture(0)
    name = input("Enter the person's name: ").strip()
    
    print("Look at the camera. Press 'S' to save or 'Q' to quit.")

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret: break

        # Convert to RGB for MediaPipe
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = face_detection.process(rgb_frame)

        if results.detections:
            for detection in results.detections:
                bboxC = detection.location_data.relative_bounding_box
                ih, iw, _ = frame.shape
                x, y, w, h = int(bboxC.xmin * iw), int(bboxC.ymin * ih), \
                             int(bboxC.width * iw), int(bboxC.height * ih)

                # Ensure coordinates are within frame
                x, y = max(0, x), max(0, y)
                face_roi = frame[y:y+h, x:x+w]

                if face_roi.size > 0:
                    # Draw visual feedback
                    cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                    
                    # Process face for storage
                    gray_face = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY)
                    resized_face = cv2.resize(gray_face, (100, 100))

                    cv2.imshow("Enrollment - Press 'S' to Save", frame)

                    key = cv2.waitKey(1) & 0xFF
                    if key == ord('s'):
                        save_face(name, resized_face)
                        cap.release()
                        cv2.destroyAllWindows()
                        return
                    elif key == ord('q'):
                        cap.release()
                        cv2.destroyAllWindows()
                        return

        cv2.imshow("Enrollment - Press 'S' to Save", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
