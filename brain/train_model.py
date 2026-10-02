"""
Face Recognition IoT Project - Model Training Script
Trains the OpenCV LBPH Face Recognizer on student enrolled dataset in data/
and exports weights to brain/face_model.yml and brain/labels.json.
"""

import sys
import os
from brain.model import FaceRecognizerModel, DATA_DIR, MODEL_PATH, LABELS_PATH

def main():
    print("=" * 60)
    print("  AUCA AI + IoT: TRAINING LBPH FACE RECOGNITION MODEL   ")
    print("=" * 60)
    print(f"Reading dataset from: {DATA_DIR}")
    print(f"Target model output:  {MODEL_PATH}")
    print(f"Target labels output: {LABELS_PATH}\n")

    if not os.path.exists(DATA_DIR):
        print(f"Error: {DATA_DIR} not found. Please run 'python -m brain.collect_data' first.")
        sys.exit(1)

    model = FaceRecognizerModel()
    success = model.train(DATA_DIR)

    if success:
        print("\n>> SUCCESS: Model successfully trained and ready for live webcam deployment!")
        print(">> Next step: Launch scanner with:")
        print("   python -m brain.scanner\n")
    else:
        print("\n>> ERROR: Training failed. Make sure you have at least one enrolled person folder in data/ with face images.")
        sys.exit(1)

if __name__ == "__main__":
    main()
