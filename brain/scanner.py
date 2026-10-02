"""
Face Recognition IoT Project - Live Webcam Scanner & Brain HUD
Tracks faces via laptop webcam, classifies identities using LBPH,
renders high-tech security HUD, and syncs status with Cloud Backend.

Controls:
  - [C]: Reset / Clear Access State (Lock door, turn off LEDs)
  - [F]: Toggle Fullscreen
  - [Q] or [ESC]: Quit Scanner
"""

import cv2
import time
import requests
import threading
import numpy as np
from brain.model import FaceRecognizerModel

CLOUD_URL = "http://localhost:8000"

def draw_corner_rect(img, pt1, pt2, color, thickness=2, d=15):
    """Draws high-tech sci-fi corner brackets around bounding box."""
    x1, y1 = pt1
    x2, y2 = pt2
    
    # Top-left
    cv2.line(img, (x1, y1), (x1 + d, y1), color, thickness)
    cv2.line(img, (x1, y1), (x1, y1 + d), color, thickness)
    # Top-right
    cv2.line(img, (x2, y1), (x2 - d, y1), color, thickness)
    cv2.line(img, (x2, y1), (x2, y1 + d), color, thickness)
    # Bottom-left
    cv2.line(img, (x1, y2), (x1 + d, y2), color, thickness)
    cv2.line(img, (x1, y2), (x1, y2 - d), color, thickness)
    # Bottom-right
    cv2.line(img, (x2, y2), (x2 - d, y2), color, thickness)
    cv2.line(img, (x2, y2), (x2, y2 - d), color, thickness)

class FaceScannerApp:
    def __init__(self, camera_index: int = 0):
        self.camera_index = camera_index
        self.model = FaceRecognizerModel()
        self.last_sync_time = 0
        self.sync_interval = 0.8  # minimum seconds between cloud posts
        self.last_sent_name = None
        self.last_sent_status = None
        self.cloud_online = False
        self.fullscreen = False

    def sync_to_cloud(self, name: str, confidence: float, status: str):
        """Asynchronously send recognition payload to Cloud Backend."""
        def _post():
            try:
                payload = {
                    "name": name,
                    "confidence": float(confidence),
                    "status": status
                }
                resp = requests.post(f"{CLOUD_URL}/scan", json=payload, timeout=1.0)
                self.cloud_online = (resp.status_code == 200)
            except Exception:
                self.cloud_online = False

        threading.Thread(target=_post, daemon=True).start()

    def clear_cloud(self):
        """Send clear command to cloud."""
        def _clear():
            try:
                requests.post(f"{CLOUD_URL}/clear", timeout=1.0)
            except Exception:
                pass
        threading.Thread(target=_clear, daemon=True).start()

    def run(self):
        cap = cv2.VideoCapture(self.camera_index)
        if not cap.isOpened():
            print(f"Error: Unable to open webcam at index {self.camera_index}")
            return

        window_name = "AI Face Recognition & Intruder Alert - Brain Tier"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

        print("\n" + "=" * 60)
        print("    AI FACE SCANNER & ACCESS CONTROL SYSTEM RUNNING     ")
        print("=" * 60)
        print(" Webcam active. Position face in front of the lens.")
        print(" Controls:")
        print("   [C] : Clear / Reset State")
        print("   [F] : Toggle Fullscreen")
        print("   [Q] : Quit")
        print("=" * 60 + "\n")

        prev_time = time.time()
        fps = 0.0

        while True:
            ret, frame = cap.read()
            if not ret:
                print("Failed to read webcam frame.")
                break

            # Mirror view for natural interaction
            frame = cv2.flip(frame, 1)
            h, w = frame.shape[:2]
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            now = time.time()

            # FPS calculation
            fps = 0.9 * fps + 0.1 * (1.0 / max(now - prev_time, 0.001))
            prev_time = now

            faces = self.model.detect_faces(gray)
            display = frame.copy()

            current_name = None
            current_status = None
            current_conf = 0.0

            if len(faces) > 0:
                # Prioritize largest face
                faces = sorted(faces, key=lambda f: f[2] * f[3], reverse=True)
                x, y, fw, fh = faces[0]
                face_roi = gray[y:y + fh, x:x + fw]

                name, conf, status = self.model.predict_face(face_roi)
                current_name = name
                current_status = status
                current_conf = conf

                # Color definitions: BGR
                if status == "authorized":
                    box_color = (80, 220, 100)    # Neon Green
                    tag_bg = (40, 140, 60)
                    status_text = f"AUTHORIZED: {name.upper()}"
                    sub_text = f"CONFIDENCE: {int(conf * 100)}% - ACCESS GRANTED"
                else:
                    box_color = (60, 60, 240)     # Alert Red
                    tag_bg = (30, 30, 180)
                    status_text = "SECURITY ALERT: UNKNOWN"
                    sub_text = "ACCESS DENIED - INTRUDER RECORDED"

                # Draw bounding box and brackets
                cv2.rectangle(display, (x, y), (x + fw, y + fh), box_color, 1)
                draw_corner_rect(display, (x, y), (x + fw, y + fh), box_color, thickness=3, d=20)

                # Name Tag Banner above face
                tag_y1 = max(0, y - 44)
                cv2.rectangle(display, (x, tag_y1), (x + fw, y), tag_bg, -1)
                cv2.putText(display, status_text, (x + 8, y - 24),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)
                cv2.putText(display, sub_text, (x + 8, y - 8),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.40, (220, 220, 220), 1)

                # If alert status, flash warning borders
                if status == "alert" and int(now * 4) % 2 == 0:
                    cv2.rectangle(display, (0, 0), (w, h), (0, 0, 255), 4)

                # Sync with Cloud Backend
                should_sync = (
                    (name != self.last_sent_name or status != self.last_sent_status)
                    or (now - self.last_sync_time >= self.sync_interval)
                )
                if should_sync:
                    self.sync_to_cloud(name, conf, status)
                    self.last_sent_name = name
                    self.last_sent_status = status
                    self.last_sync_time = now

            # Top Navigation Bar HUD
            cv2.rectangle(display, (0, 0), (w, 44), (16, 20, 25), -1)
            cv2.line(display, (0, 44), (w, 44), (48, 54, 61), 1)

            cv2.putText(display, "AI FACE RECOGNITION SYSTEM", (16, 28),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 240, 255), 2)

            cloud_status = "CLOUD: ONLINE" if self.cloud_online else "CLOUD: OFFLINE"
            cloud_color = (80, 220, 100) if self.cloud_online else (120, 120, 120)
            cv2.putText(display, f"{cloud_status} | FPS: {int(fps)}", (w - 220, 28),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.50, cloud_color, 1)

            # Bottom Controls Bar HUD
            cv2.rectangle(display, (0, h - 36), (w, h), (16, 20, 25), -1)
            cv2.line(display, (0, h - 36), (w, h - 36), (48, 54, 61), 1)
            cv2.putText(display, "[C] Clear/Reset  |  [F] Fullscreen  |  [Q] Quit", (16, h - 12),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.50, (180, 190, 200), 1)

            # Untrained warning if applicable
            if not self.model.is_trained:
                cv2.rectangle(display, (w // 2 - 250, 60), (w // 2 + 250, 100), (0, 50, 160), -1)
                cv2.putText(display, "! NO FACES ENROLLED ! RUN python -m brain.collect_data",
                            (w // 2 - 240, 86), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (255, 255, 255), 1)

            cv2.imshow(window_name, display)
            key = cv2.waitKey(1) & 0xFF

            if key == ord('q') or key == 27:
                break
            elif key == ord('c'):
                print(">> [USER CLEAR] Resetting cloud state...")
                self.clear_cloud()
                self.last_sent_name = None
                self.last_sent_status = "cleared"
            elif key == ord('f'):
                self.fullscreen = not self.fullscreen
                prop = cv2.WINDOW_FULLSCREEN if self.fullscreen else cv2.WINDOW_NORMAL
                cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, prop)

        cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    app = FaceScannerApp()
    app.run()
