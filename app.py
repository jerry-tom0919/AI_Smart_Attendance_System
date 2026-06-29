"""
AI Smart Attendance System
- Multi-face recognition using OpenCV LBPH
- Flask web server with real-time MJPEG stream
- Auto-marks absent after 9:15 AM and 1:00 PM cutoffs
"""

import cv2
import numpy as np
import pandas as pd
import os
import json
import pickle
import threading
import time
from datetime import datetime, date
from flask import Flask, Response, render_template, jsonify, request, redirect, url_for
from PIL import Image

app = Flask(__name__)

# ─────────────── CONFIG ───────────────
KNOWN_FACES_DIR = "known_faces"
MODEL_FILE = "face_model.yml"
LABELS_FILE = "face_labels.json"
ATTENDANCE_DIR = "attendance_logs"
CASCADE_PATH = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"

CUTOFF_MORNING = (9, 15)   # 9:15 AM
CUTOFF_AFTERNOON = (13, 0) # 1:00 PM

os.makedirs(KNOWN_FACES_DIR, exist_ok=True)
os.makedirs(ATTENDANCE_DIR, exist_ok=True)

# ─────────────── GLOBALS ───────────────
face_cascade = cv2.CascadeClassifier(CASCADE_PATH)
recognizer = cv2.face.LBPHFaceRecognizer_create()
label_map = {}          # id -> {name, department}
reverse_map = {}        # name -> id
model_trained = False
attendance_today = {}   # name -> {status, time, department}
lock = threading.Lock()
camera = None
camera_active = False
latest_frame = None
detection_log = []      # last N detections for live feed

# ─────────────── SAMPLE STUDENTS (demo data) ───────────────
STUDENTS = [
    {"name": "Sanjana",      "department": "AI&DS"},
    {"name": "Abinaya",      "department": "AI&DS"},
    {"name": "Rethiga",    "department": "AI&DS"},
    {"name": "Kathirmathi",   "department": "AI&DS"},
   
]

def get_today_file():
    return os.path.join(ATTENDANCE_DIR, f"attendance_{date.today()}.json")

def load_today_attendance():
    global attendance_today
    f = get_today_file()
    if os.path.exists(f):
        with open(f) as fh:
            attendance_today = json.load(fh)
    else:
        attendance_today = {}

def save_attendance():
    with open(get_today_file(), "w") as f:
        json.dump(attendance_today, f, indent=2)

def load_model():
    global recognizer, label_map, reverse_map, model_trained
    if os.path.exists(MODEL_FILE) and os.path.exists(LABELS_FILE):
        recognizer.read(MODEL_FILE)
        with open(LABELS_FILE) as f:
            label_map = {int(k): v for k, v in json.load(f).items()}
        reverse_map = {v["name"]: k for k, v in label_map.items()}
        model_trained = True
        print(f"[MODEL] Loaded with {len(label_map)} people.")
    else:
        model_trained = False

def train_model():
    global recognizer, label_map, reverse_map, model_trained
    faces, labels = [], []
    label_map = {}
    idx = 0
    for person_dir in os.listdir(KNOWN_FACES_DIR):
        person_path = os.path.join(KNOWN_FACES_DIR, person_dir)
        if not os.path.isdir(person_path):
            continue
        meta_file = os.path.join(person_path, "meta.json")
        if not os.path.exists(meta_file):
            continue
        with open(meta_file) as f:
            meta = json.load(f)
        label_map[idx] = {"name": meta["name"], "department": meta["department"]}
        for img_file in os.listdir(person_path):
            if not img_file.lower().endswith((".jpg", ".png")):
                continue
            img_path = os.path.join(person_path, img_file)
            img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
            if img is None:
                continue
            detected = face_cascade.detectMultiScale(img, 1.1, 5, minSize=(60, 60))
            for (x, y, w, h) in detected:
                face_roi = cv2.resize(img[y:y+h, x:x+w], (100, 100))
                faces.append(face_roi)
                labels.append(idx)
        idx += 1

    if not faces:
        model_trained = False
        return False

    recognizer.train(faces, np.array(labels))
    recognizer.save(MODEL_FILE)
    with open(LABELS_FILE, "w") as f:
        json.dump({str(k): v for k, v in label_map.items()}, f)
    reverse_map = {v["name"]: k for k, v in label_map.items()}
    model_trained = True
    print(f"[TRAIN] Model trained with {len(faces)} samples for {idx} people.")
    return True

def mark_attendance(name, department):
    global attendance_today
    now = datetime.now()
    time_str = now.strftime("%I:%M:%S %p")
    h, m = now.hour, now.minute

    with lock:
        if name in attendance_today:
            return  # already marked

        if (h, m) <= CUTOFF_MORNING:
            status = "Present"
        elif (h, m) <= CUTOFF_AFTERNOON:
            status = "Late"
        else:
            status = "Absent"

        attendance_today[name] = {
            "department": department,
            "status": status,
            "time": time_str
        }
        detection_log.insert(0, {
            "name": name,
            "department": department,
            "status": status,
            "time": time_str
        })
        if len(detection_log) > 20:
            detection_log.pop()
        save_attendance()
        print(f"[ATTENDANCE] {name} ({department}) → {status} at {time_str}")

def auto_absent_unmarked():
    """Mark all unrecognized students as Absent at end of sessions."""
    now = datetime.now()
    h, m = now.hour, now.minute
    if (h > CUTOFF_AFTERNOON[0]) or (h == CUTOFF_AFTERNOON[0] and m >= CUTOFF_AFTERNOON[1]):
        with lock:
            for s in STUDENTS:
                if s["name"] not in attendance_today:
                    attendance_today[s["name"]] = {
                        "department": s["department"],
                        "status": "Absent",
                        "time": "—"
                    }
            save_attendance()

def camera_thread():
    global latest_frame, camera_active
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        # Use demo mode with blank frame
        camera_active = False
        return
    camera_active = True
    face_cooldown = {}  # name -> last marked time (avoid re-marking every frame)

    while camera_active:
        ret, frame = cap.read()
        if not ret:
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(80, 80))

        for (x, y, w, h) in faces:
            face_roi = cv2.resize(gray[y:y+h, x:x+w], (100, 100))
            label_id, confidence = -1, 999

            if model_trained:
                label_id, confidence = recognizer.predict(face_roi)

            if model_trained and confidence < 70 and label_id in label_map:
                info = label_map[label_id]
                name = info["name"]
                dept = info["department"]
                color = (0, 200, 80)
                text = f"{name} ({int(confidence)})"

                # Cooldown: mark once per 5s per person
                last = face_cooldown.get(name, 0)
                if time.time() - last > 5:
                    mark_attendance(name, dept)
                    face_cooldown[name] = time.time()
            else:
                name = "Unknown"
                color = (0, 80, 220)
                text = "Unknown"

            # Draw bounding box
            cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
            cv2.rectangle(frame, (x, y-30), (x+w, y), color, -1)
            cv2.putText(frame, text, (x+4, y-8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)

        # Timestamp overlay
        ts = datetime.now().strftime("%d %b %Y  %I:%M:%S %p")
        cv2.putText(frame, ts, (10, frame.shape[0]-12),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

        _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        latest_frame = buf.tobytes()
        time.sleep(0.03)

    cap.release()
    camera_active = False

def gen_frames():
    while True:
        if latest_frame:
            yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + latest_frame + b"\r\n")
        else:
            # Placeholder black frame
            blank = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(blank, "Camera not available", (140, 220),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (80, 80, 80), 2)
            cv2.putText(blank, "Start camera from dashboard", (110, 260),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (60, 60, 60), 1)
            _, buf = cv2.imencode(".jpg", blank)
            yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + buf.tobytes() + b"\r\n")
        time.sleep(0.05)

# ─────────────── ROUTES ───────────────

@app.route("/")
def index():
    load_today_attendance()
    now = datetime.now()
    session_info = "Morning Session" if now.hour < 13 else "Afternoon Session"
    cutoff = "9:15 AM" if now.hour < 13 else "1:00 PM"
    return render_template("index.html",
                           attendance=attendance_today,
                           students=STUDENTS,
                           session=session_info,
                           cutoff=cutoff,
                           model_trained=model_trained,
                           camera_active=camera_active,
                           today=date.today().strftime("%d %B %Y"))

@app.route("/video_feed")
def video_feed():
    return Response(gen_frames(), mimetype="multipart/x-mixed-replace; boundary=frame")

@app.route("/api/attendance")
def api_attendance():
    load_today_attendance()
    auto_absent_unmarked()
    rows = []
    for s in STUDENTS:
        name = s["name"]
        if name in attendance_today:
            rows.append({
                "name": name,
                "department": attendance_today[name]["department"],
                "status": attendance_today[name]["status"],
                "time": attendance_today[name]["time"]
            })
        else:
            rows.append({"name": name, "department": s["department"], "status": "—", "time": "—"})
    return jsonify(rows)

@app.route("/api/detections")
def api_detections():
    return jsonify(detection_log[:10])

@app.route("/api/stats")
def api_stats():
    load_today_attendance()
    present = sum(1 for v in attendance_today.values() if v["status"] == "Present")
    late    = sum(1 for v in attendance_today.values() if v["status"] == "Late")
    absent  = sum(1 for v in attendance_today.values() if v["status"] == "Absent")
    total   = len(STUDENTS)
    return jsonify({"present": present, "late": late, "absent": absent,
                    "unmarked": total - present - late - absent, "total": total})

@app.route("/api/start_camera", methods=["POST"])
def start_camera():
    global camera_active
    if not camera_active:
        t = threading.Thread(target=camera_thread, daemon=True)
        t.start()
        time.sleep(1)
    return jsonify({"status": "started", "camera_active": camera_active})

@app.route("/api/stop_camera", methods=["POST"])
def stop_camera():
    global camera_active
    camera_active = False
    return jsonify({"status": "stopped"})

@app.route("/api/train", methods=["POST"])
def api_train():
    success = train_model()
    return jsonify({"success": success, "people": len(label_map)})

@app.route("/api/mark_absent", methods=["POST"])
def api_mark_absent():
    auto_absent_unmarked()
    return jsonify({"success": True})

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        dept = request.form.get("department", "").strip()
        files = request.files.getlist("photos")
        if not name or not dept or not files:
            return jsonify({"error": "Missing fields"}), 400

        safe_name = name.replace(" ", "_")
        person_dir = os.path.join(KNOWN_FACES_DIR, safe_name)
        os.makedirs(person_dir, exist_ok=True)

        with open(os.path.join(person_dir, "meta.json"), "w") as f:
            json.dump({"name": name, "department": dept}, f)

        count = 0
        for i, file in enumerate(files):
            if file and file.filename:
                img = Image.open(file.stream).convert("RGB")
                img.save(os.path.join(person_dir, f"img_{i}.jpg"))
                count += 1

        # Also add to STUDENTS list if not present
        if not any(s["name"] == name for s in STUDENTS):
            STUDENTS.append({"name": name, "department": dept})

        return jsonify({"success": True, "saved": count, "name": name})

    return render_template("register.html", departments=list({s["department"] for s in STUDENTS}))

@app.route("/export")
def export():
    load_today_attendance()
    auto_absent_unmarked()
    rows = []
    for s in STUDENTS:
        name = s["name"]
        if name in attendance_today:
            rows.append({"Name": name,
                         "Department": attendance_today[name]["department"],
                         "Status": attendance_today[name]["status"],
                         "Time": attendance_today[name]["time"]})
        else:
            rows.append({"Name": name, "Department": s["department"],
                         "Status": "Absent", "Time": "—"})
    df = pd.DataFrame(rows)
    path = os.path.join(ATTENDANCE_DIR, f"export_{date.today()}.csv")
    df.to_csv(path, index=False)
    return jsonify({"success": True, "file": path, "rows": len(df)})

if __name__ == "__main__":
    load_today_attendance()
    load_model()
    print("=" * 50)
    print("  AI Smart Attendance System")
    print("  http://127.0.0.1:5000")
    print("=" * 50)
    app.run(debug=False, threaded=True, host="0.0.0.0", port=5000)
