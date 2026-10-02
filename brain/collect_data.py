"""
Face Recognition IoT Project - Face Enrolment & Dataset Collector
Collects 30 face crops per person as required by AUCA AI+IoT project guidelines:
"Own your data. Faces ... you record and enrol them yourselves. No dataset, no project.
You enrol your own face, and a friend's for the wrong face test."
"""

import os
import cv2
import time
import numpy as np
from brain.model import FaceRecognizerModel, DATA_DIR, CASCADE_PATH

def collect_faces_for_person(name: str, target_count: int = 30, camera_index: int = 0):
    """Opens webcam and collects target_count face samples for a given name."""
    clean_name = name.strip().replace(" ", "_")
    person_dir = os.path.join(DATA_DIR, clean_name)
    os.makedirs(person_dir, exist_ok=True)

    existing_files = [f for f in os.listdir(person_dir) if f.lower().endswith(('.jpg', '.png'))]
    sample_index = len(existing_files)

    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        print(f"Error: Unable to access webcam on index {camera_index}")
        return False

    face_cascade = cv2.CascadeClassifier(CASCADE_PATH)
    print("\n" + "=" * 60)
    print(f"  ENROLLING FACE FOR: {clean_name}")
    print("=" * 60)
    print(" Instructions:")
    print("  - Look into the camera inside the green frame.")
    print("  - Press [SPACE] to toggle AUTO-CAPTURE.")
    print("  - Move slightly: tilt up, down, left, right, smile.")
    print("  - Press [Q] to abort or finish early.")
    print("=" * 60 + "\n")

    auto_capture = False
    last_capture_time = 0
    capture_interval = 0.22  # seconds between frames in auto-capture

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to grab camera frame.")
            break

        # Flip horizontally for natural mirror feel
        frame = cv2.flip(frame, 1)
        h, w = frame.shape[:2]
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        faces = face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.15,
            minNeighbors=5,
            minSize=(80, 80)
        )

        display_frame = frame.copy()
        now = time.time()

        # Draw reticle guide in center
        center_x, center_y = w // 2, h // 2
        cv2.circle(display_frame, (center_x, center_y), 130, (80, 80, 80), 1, cv2.LINE_AA)

        face_detected = len(faces) > 0
        if face_detected:
            # Pick the largest face (closest to camera)
            faces = sorted(faces, key=lambda f: f[2] * f[3], reverse=True)
            x, y, fw, fh = faces[0]

            # Bounding box
            box_color = (0, 255, 128) if auto_capture else (255, 200, 0)
            cv2.rectangle(display_frame, (x, y), (x + fw, y + fh), box_color, 2)
            cv2.putText(display_frame, f"{clean_name} (DETECTED)", (x, y - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, box_color, 2)

            # Auto capture trigger
            if auto_capture and (now - last_capture_time >= capture_interval):
                face_crop = gray[y:y + fh, x:x + fw]
                if face_crop.size > 0:
                    sample_index += 1
                    save_path = os.path.join(person_dir, f"face_{sample_index:03d}.jpg")
                    cv2.imwrite(save_path, face_crop)
                    last_capture_time = now
                    print(f"Captured [{sample_index}/{target_count}] -> {save_path}")

                    # Visual flash
                    cv2.rectangle(display_frame, (0, 0), (w, h), (255, 255, 255), 6)

                    if sample_index >= target_count:
                        print(f"\n>> Finished collecting {target_count} samples for {clean_name}!")
                        break

        # Header HUD
        cv2.rectangle(display_frame, (0, 0), (w, 48), (20, 24, 30), -1)
        cv2.putText(display_frame, f"ENROLLING: {clean_name.upper()} | SAMPLES: {sample_index}/{target_count}",
                    (16, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 240, 255), 2)

        # Footer Status
        status_text = "AUTO-CAPTURING... (Move head slightly)" if auto_capture else "PAUSED: Press [SPACE] to capture"
        status_color = (0, 255, 128) if auto_capture else (180, 180, 180)
        cv2.rectangle(display_frame, (0, h - 36), (w, h), (20, 24, 30), -1)
        cv2.putText(display_frame, status_text, (16, h - 12),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, status_color, 1)

        cv2.imshow("Face Enrolment Studio - AI + IoT", display_frame)
        key = cv2.waitKey(1) & 0xFF

        if key == ord(' '):
            auto_capture = not auto_capture
        elif key == ord('q') or key == 27:  # ESC or Q
            break

    cap.release()
    cv2.destroyAllWindows()
    return sample_index > 0

def main():
    print("\n" + "=" * 60)
    print("      AUCA AI + IoT: FACE ENROLMENT STUDIO (TIER 1)     ")
    print("=" * 60)
    name = input("Enter the person's name to enrol (e.g. Sam, Alice): ").strip()
    if not name:
        name = "Sam"

    target_count = input("Number of samples to capture [Default: 30]: ").strip()
    target_count = int(target_count) if target_count.isdigit() else 30

    success = collect_faces_for_person(name, target_count)

    if success:
        train_now = input("\nDo you want to train the model now with enrolled faces? [Y/n]: ").strip().lower()
        if train_now in ["", "y", "yes"]:
            model = FaceRecognizerModel()
            model.train()
            print("\n>> All set! You can now start the scanner with:")
            print("   python -m brain.scanner\n")

if __name__ == "__main__":
    main()
