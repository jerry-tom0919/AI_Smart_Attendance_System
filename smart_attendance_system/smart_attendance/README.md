# 🎓 AI Smart Attendance System

A real-time facial recognition attendance system built with Python, Flask, and OpenCV.

## ✨ Features

- 🎥 **Multi-face recognition** – Detects and recognizes multiple faces simultaneously
- ⏰ **Auto cutoff rules** – Present (before 9:15 AM), Late (9:15 AM–1:00 PM), Absent (after 1:00 PM)
- 📊 **Live dashboard** – Professional dark-themed UI with real-time stats
- 📋 **Attendance table** – Searchable [Name · Department · P/A/Late · Time] register
- 📁 **CSV export** – One-click export for the day's attendance
- 👤 **Face registration** – Upload photos to enroll new students
- 🔁 **Auto-refresh** – Dashboard updates every 4 seconds

## 🛠️ Tech Stack

| Layer       | Technology                          |
|-------------|-------------------------------------|
| Backend     | Python 3, Flask                     |
| Face AI     | OpenCV LBPH Face Recognizer         |
| Detection   | Haar Cascade (frontalface)          |
| Data        | Pandas, JSON                        |
| Frontend    | HTML5, CSS3, Vanilla JS             |
| Camera      | OpenCV VideoCapture (MJPEG stream)  |

## 📦 Installation

```bash
# 1. Clone / unzip project
cd smart_attendance

# 2. Install dependencies
pip install -r requirements.txt
# (Use opencv-contrib-python for LBPH recognizer support)

# 3. Run setup helper (creates demo face folders)
python setup_demo.py

# 4. Start the app
python app.py

# 5. Open browser
# http://localhost:5000
```

## 🚀 How to Use

### Step 1 – Register Faces
1. Click **"+ Register Face"** button in the header
2. Enter student name and department
3. Upload 5–10 clear front-facing photos
4. Click **"Register Student"**

### Step 2 – Train Model
1. Go back to the dashboard
2. Click **"⚙ Train Model"** button
3. Wait for success toast notification

### Step 3 – Start Recognition
1. Connect a webcam
2. Click **"▶ Start Camera"**
3. Face the camera – attendance is marked automatically!

### Attendance Rules
| Time              | Status   |
|-------------------|----------|
| Before 9:15 AM    | ✅ Present|
| 9:15 AM – 1:00 PM | ⚠ Late   |
| After 1:00 PM     | ✗ Absent  |

### Step 4 – Export
- Click **"↓ Export CSV"** to save attendance to `attendance_logs/`

## 📁 Project Structure

```
smart_attendance/
├── app.py                 ← Main Flask application
├── setup_demo.py          ← Demo setup helper
├── requirements.txt
├── face_model.yml         ← Trained LBPH model (auto-generated)
├── face_labels.json       ← Label map (auto-generated)
├── known_faces/           ← Student face image folders
│   └── Arun_Kumar/
│       ├── meta.json
│       ├── img_0.jpg
│       └── ...
├── attendance_logs/       ← Daily attendance JSON + CSV
│   └── attendance_2025-06-01.json
├── templates/
│   ├── index.html         ← Main dashboard
│   └── register.html      ← Face registration page
└── static/
    ├── css/style.css
    └── js/main.js
```

## ⚠️ Notes

- Uses **OpenCV LBPH** (Local Binary Pattern Histogram) – works offline, no GPU needed
- Minimum **5 photos per person** for decent accuracy; 10+ photos recommended
- Recognition confidence threshold: **< 70** (lower = more strict)
- Each recognized face has a **5-second cooldown** to avoid duplicate entries
- Works best with good lighting and front-facing camera

## 🔧 Customization

Edit in `app.py`:
```python
CUTOFF_MORNING   = (9, 15)   # Change morning cutoff
CUTOFF_AFTERNOON = (13, 0)   # Change afternoon cutoff

STUDENTS = [...]             # Add/edit default student list
```
