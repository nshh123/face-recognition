"""
Face Recognition IoT Project - Brain Model & Face Classifier
Handles face detection via Haar Cascade, normalization, LBPH model training,
and distance-based confidence thresholding.
Complies with requirement: "Face recognition, not just detection: use OpenCV's LBPH recogniser."
"""

import os
import json
import cv2
import numpy as np
from typing import Tuple, Optional, Dict

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
BRAIN_DIR = os.path.join(BASE_DIR, "brain")
DATA_DIR = os.path.join(BASE_DIR, "data")
MODEL_PATH = os.path.join(BRAIN_DIR, "face_model.yml")
LABELS_PATH = os.path.join(BRAIN_DIR, "labels.json")
CASCADE_PATH = os.path.join(BRAIN_DIR, "haarcascade_frontalface_default.xml")

# LBPH Distance Threshold (Lower is better match).
# Distances <= DISTANCE_THRESHOLD are considered known faces.
DISTANCE_THRESHOLD = 68.0

class FaceRecognizerModel:
    def __init__(self, model_path: str = MODEL_PATH, labels_path: str = LABELS_PATH):
        self.model_path = model_path
        self.labels_path = labels_path
        self.labels: Dict[int, str] = {}
        self.face_cascade = cv2.CascadeClassifier(CASCADE_PATH)
        self.recognizer = cv2.face.LBPHFaceRecognizer_create(
            radius=1,
            neighbors=8,
            grid_x=8,
            grid_y=8
        )
        self.is_trained = False
        self.load_model()

    def load_model(self) -> bool:
        """Loads trained LBPH model and label mapping if available."""
        if os.path.exists(self.model_path) and os.path.exists(self.labels_path):
            try:
                self.recognizer.read(self.model_path)
                with open(self.labels_path, "r", encoding="utf-8") as f:
                    raw_labels = json.load(f)
                    self.labels = {int(k): v for k, v in raw_labels.items()}
                self.is_trained = True
                print(f"[Brain Model] Successfully loaded face model with {len(self.labels)} identity(ies): {list(self.labels.values())}")
                return True
            except Exception as e:
                print(f"[Brain Model] Error loading existing model: {e}")
                self.is_trained = False
                return False
        else:
            print("[Brain Model] No trained model found yet. Run 'python -m brain.collect_data' to register your face!")
            self.is_trained = False
            return False

    def detect_faces(self, frame: np.ndarray):
        """
        Detects frontal faces in the input color or grayscale frame.
        Returns list of (x, y, w, h) bounding boxes.
        """
        if len(frame.shape) == 3:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        else:
            gray = frame

        faces = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.15,
            minNeighbors=5,
            minSize=(80, 80)
        )
        return faces

    def preprocess_face(self, gray_crop: np.ndarray, target_size=(200, 200)) -> np.ndarray:
        """
        Applies histogram equalization (for lighting resilience)
        and standardizes face crop resolution.
        """
        equalized = cv2.equalizeHist(gray_crop)
        resized = cv2.resize(equalized, target_size, interpolation=cv2.INTER_AREA)
        return resized

    def predict_face(self, gray_crop: np.ndarray) -> Tuple[str, float, str]:
        """
        Classifies cropped face region using LBPH distance score.
        Returns:
            (name, confidence, status)
            where status is 'authorized' (known) or 'alert' (unknown / intruder).
        """
        if not self.is_trained:
            return "UNREGISTERED", 0.0, "alert"

        processed = self.preprocess_face(gray_crop)
        label_id, distance = self.recognizer.predict(processed)

        # Convert LBPH distance (typically 0-120) to a 0.0 - 1.0 confidence score
        # 0 distance -> 100% confidence, 100 distance -> 0% confidence
        confidence = max(0.0, min(1.0, 1.0 - (distance / 100.0)))

        if distance <= DISTANCE_THRESHOLD and label_id in self.labels:
            name = self.labels[label_id]
            status = "authorized"
        else:
            name = "UNKNOWN"
            status = "alert"

        return name, confidence, status

    def train(self, data_dir: str = DATA_DIR) -> bool:
        """
        Trains LBPH face recognizer from images in data/<person_name>/.
        Saves weights to face_model.yml and mapping to labels.json.
        """
        if not os.path.exists(data_dir):
            print(f"[Brain Train] Data directory {data_dir} does not exist.")
            return False

        faces = []
        labels = []
        label_map = {}
        current_id = 0

        subdirs = sorted([d for d in os.listdir(data_dir) if os.path.isdir(os.path.join(data_dir, d))])
        if not subdirs:
            print("[Brain Train] No person subdirectories found in data/.")
            return False

        for name in subdirs:
            person_dir = os.path.join(data_dir, name)
            image_files = [f for f in os.listdir(person_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]

            if not image_files:
                continue

            label_map[current_id] = name
            print(f"[Brain Train] Loading {len(image_files)} sample(s) for '{name}' (ID: {current_id})...")

            for f in image_files:
                img_path = os.path.join(person_dir, f)
                img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
                if img is None:
                    continue

                processed = self.preprocess_face(img)
                faces.append(processed)
                labels.append(current_id)

            current_id += 1

        if len(faces) < 5:
            print("[Brain Train] Need at least 5 face samples across all enrolled persons to train.")
            return False

        print(f"[Brain Train] Training LBPH recognizer on {len(faces)} total face images across {len(label_map)} person(s)...")
        self.recognizer.train(faces, np.array(labels))

        # Save model and labels
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        self.recognizer.write(self.model_path)
        with open(self.labels_path, "w", encoding="utf-8") as f:
            json.dump({str(k): v for k, v in label_map.items()}, f, indent=2)

        self.labels = label_map
        self.is_trained = True
        print(f">> [Brain Train] Training complete! Model saved to {self.model_path}")
        return True
