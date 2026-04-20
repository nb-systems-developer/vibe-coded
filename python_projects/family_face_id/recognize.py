import cv2
import mediapipe as mp
import numpy as np
import os

# Threshold: Lower means stricter matching. 
# 3000-5000 is a good range for pixel-wise MSE.
MSE_THRESHOLD = 4000 

mp_face_detection = mp.solutions.face_detection
face_detection = mp_face_detection.FaceDetection(model_selection=0, min_detection_confidence=0.5)

def load_trained_data():
    if not os.path.exists('faces_data.npz'):
        print("No data found. Please run enroll.py first.")
        return None, None
    data = np.load('faces_data.npz', allow_pickle=True)
    return data['faces'], data['names']

def recognize_face(current_face, stored_faces, names):
    min_mse = float('inf')
    best_name = "Unknown"

    for i, stored_face in enumerate(stored_faces):
        # Calculate Mean Squared Error
        mse = np.mean((stored_face.astype("float") - current_face.astype("float")) ** 2)
        
        if mse < min_mse:
            min_mse = mse
            best_name = names[i]

    if min_mse > MSE_THRESHOLD:
        return "Unknown", min_mse
    return best_name, min_mse

def main():
    stored_faces, names = load_trained_data()
    if stored_faces is None: return

    cap = cv2.VideoCapture(0)

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret: break

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = face_detection.process(rgb_frame)

        if results.detections:
            for detection in results.detections:
                bboxC = detection.location_data.relative_bounding_box
                ih, iw, _ = frame.shape
                x, y, w, h = int(bboxC.xmin * iw), int(bboxC.ymin * ih), \
                             int(bboxC.width * iw), int(bboxC.height * ih)

                x, y = max(0, x), max(0, y)
                face_roi = frame[y:y+h, x:x+w]

                if face_roi.size > 0:
                    gray_face = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY)
                    resized_face = cv2.resize(gray_face, (100, 100))

                    name, confidence = recognize_face(resized_face, stored_faces, names)

                    # Display logic
                    color = (0, 255, 0) if name != "Unknown" else (0, 0, 255)
                    cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
                    cv2.putText(frame, f"{name}", (x, y - 10), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

        cv2.imshow("Family Recognition Mode", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
