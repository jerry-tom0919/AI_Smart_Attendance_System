"""
setup_demo.py – Creates demo face folders for testing without a real camera.
Run this ONCE before starting the app if you want to test with dummy data.

Usage:
    python setup_demo.py
"""

import os
import json
import numpy as np
import cv2

KNOWN_FACES_DIR = "known_faces"
os.makedirs(KNOWN_FACES_DIR, exist_ok=True)

DEMO_STUDENTS = [
    {"name": "Arun Kumar",   "department": "CSE"},
    {"name": "Priya Devi",   "department": "ECE"},
    {"name": "Rahul Sharma", "department": "MECH"},
    {"name": "Sanjana Reddy","department": "IT"},
]

print("Creating demo face directories...")
for student in DEMO_STUDENTS:
    safe = student["name"].replace(" ", "_")
    path = os.path.join(KNOWN_FACES_DIR, safe)
    os.makedirs(path, exist_ok=True)
    meta_path = os.path.join(path, "meta.json")
    with open(meta_path, "w") as f:
        json.dump(student, f)
    print(f"  ✓ {student['name']} ({student['department']}) → {path}/")
    print(f"    → Add 5-10 face photos (JPG/PNG) to this folder, then run 'Train Model' in the dashboard.")

print("\n✓ Setup complete. Now:")
print("  1. Add face photos to each student folder in known_faces/")
print("  2. Run: python app.py")
print("  3. Open: http://localhost:5000")
print("  4. Click 'Train Model' button in the dashboard")
print("  5. Click 'Start Camera' to begin recognition")
