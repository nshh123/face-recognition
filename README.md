# Face Recognition IoT Project 👤🔒

**AUCA Software Innovation Center · AI + IoT Final Project**

This project uses the laptop webcam to analyze and scan faces in real-time, recognizes authorized individuals using **OpenCV LBPH Face Recognition**, sounds a security alert if an unregistered face/intruder is detected, broadcasts access telemetry to a **FastAPI Cloud Backend**, and actuates a physical **ESP32** equipped with an **I2C OLED screen**, **Green/Red Status LEDs**, an **Active Alarm Buzzer**, and a **Door Lock Servo**.

---

## 🏛️ System Architecture: The 3 Tiers

```
  [ TIER 1: THE BRAIN ]             [ TIER 2: THE CLOUD ]               [ TIER 3: THE BODY ]
     (Laptop Webcam)                  (FastAPI Server)                    (ESP32 + Actuators)
+-----------------------+         +----------------------+         +---------------------------+
| OpenCV Haar Cascade   |         | Single Truth Backend |         | ESP32 Microcontroller    |
|         +             | --POST->|  - GET /state        | <-GET-- |             +             |
| Lighting Equalization |         |  - POST /scan        |         | SSD1306 128x64 OLED Screen|
|         +             |         |  - POST /clear       |         |             +             |
| LBPH Face Classifier  |         |  - Live Web UI (/)   |         | Green & Red Status LEDs   |
|         +             |         |                      |         |             +             |
| Confidence Threshold  |         |                      |         | Buzzer & SG90 Door Servo  |
+-----------------------+         +----------------------+         +---------------------------+
```

### 1. The Brain (`brain/`)
- **Face Detection & Preprocessing (`model.py`)**:
  - Uses Haar Cascade (`haarcascade_frontalface_default.xml`) to detect faces in real-time.
  - Applies histogram equalization (`cv2.equalizeHist`) so lighting shifts do not break recognition.
  - Normalizes crops to standard $200 \times 200$ grayscale matrices.
- **LBPH Face Classifier (`model.py`)**:
  - Complies with project specification: *"Face recognition, not just detection: use OpenCV's LBPH recogniser and an enrolment step."*
  - Calculates Local Binary Pattern Histograms with distance scores (lower distance = closer match).
  - If distance $\le 68.0$, returns `status="authorized"` with the recognized person's name (e.g., `Sam`).
  - If distance $> 68.0$ (or unconfident), returns `status="alert"` and flags `UNKNOWN / INTRUDER`.
- **Face Enrolment Studio (`collect_data.py`)**:
  - Guides you to capture 30 face frames from multiple angles into `data/<name>/`.
  - Prompts you to immediately train the model upon finishing.
- **Model Training Pipeline (`train_model.py`)**:
  - Trains LBPH classifier across all enrolled identities and saves `face_model.yml` and `labels.json`.
- **Live Scanner & Security HUD (`scanner.py`)**:
  - Sci-Fi targeting reticle, live FPS counter, authorization banners, and instant cloud sync.

### 2. The Cloud (`cloud/`)
- **FastAPI Backend (`server.py`)**:
  - `GET /state`: Polled by ESP32 (and the fake body) for real-time actuation directives.
  - `POST /scan`: Receives scan results from the Brain; toggles green/red LEDs, buzzer, and servo door state.
  - `POST /clear`: Resets state and locks door (triggered by physical button or web UI).
  - `GET /`: High-tech dark mode dashboard featuring a virtual OLED display, live LED indicators, buzzer animations, door lock status, and historical access log.

### 3. The Body (`body/`)
- **Fake Board Simulator (`body/fake_board.py`)**:
  - Simulates the physical hardware in your terminal before wiring!
  - Displays virtual OLED, Green LED, Red Alert LED, Buzzer state, and Servo Angle (0° Locked vs 90° Open).
  - Press `c` + Enter to simulate the physical door-lock push button on GPIO 4.
- **Physical ESP32 Firmware (`body/esp32_face_monitor/esp32_face_monitor.ino`)**:
  - Connects to Wi-Fi.
  - Displays recognized name or flashing alert on SSD1306 I2C OLED (GPIO 21/22).
  - Lights up Green LED (GPIO 18) for authorized face; flashes Red LED (GPIO 19) for alert.
  - Sounds Buzzer (GPIO 5) on security alert.
  - Swings SG90 Servo (GPIO 13) to 90° (unlocked) or 0° (locked).
  - Hardware push button (GPIO 4) to lock/clear.

---

## 🚀 Quickstart: Step-by-Step

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

---

### Step 2: Enrol Your Face & Retrain
Per the project rubric: *"Own your data. Faces ... you record and enrol them yourselves. You enrol your own face, and a friend's for the wrong face test."*

Run the face enrolment studio:
```bash
python -m brain.collect_data
```
1. Type your name (e.g. `Sam`).
2. Position your face inside the guide and press `[SPACE]` to start auto-capture (30 frames). Move your head slightly (tilt up, down, smile).
3. When prompted, type `Y` to automatically train the model.
4. *(Optional)* Run it again to enrol a friend's face for the authorized vs. unauthorized test!

*(To retrain anytime without re-capturing: `python -m brain.train_model`)*

---

### Step 3: Start the Cloud Server
Open a terminal in the project directory:
```bash
python -m uvicorn cloud.server:app --port 8000 --reload
```
Open **`http://localhost:8000`** in your browser to view the live dashboard.

---

### Step 4: Run the Fake Body (Virtual ESP32 Simulator)
Open a second terminal:
```bash
python -m body.fake_board
```
You will see the simulated OLED screen, Green/Red status lights, Buzzer, and Servo lock.

---

### Step 5: Launch the Brain (Live Webcam Scanner)
Open a third terminal:
```bash
python -m brain.scanner
```
- Stand in front of your webcam.
- Watch your face get recognized with your name and green HUD brackets!
- Have an unregistered person step in (or look away/cover part of face) to trigger the red **INTRUDER ALERT** and sounding buzzer!
- Watch the Cloud Dashboard and Fake Body react live in real time.

---

## 🔌 Hardware Wiring Guide (For Lab Day)

### 1. I2C OLED Display (SSD1306 128x64)
| OLED Pin | ESP32 Pin | Description |
|---|---|---|
| **VCC** | 3.3V | Power rail |
| **GND** | GND | Common ground |
| **SCL** | GPIO 22 | I2C Clock |
| **SDA** | GPIO 21 | I2C Data |

### 2. Status LEDs & Buzzer
| Component | ESP32 Pin | Resistor | Function |
|---|---|---|---|
| **Green LED** | **GPIO 18** | 220Ω in series with Anode (+) | Authorized Face (Access Granted) |
| **Red LED** | **GPIO 19** | 220Ω in series with Anode (+) | Unknown Face / Security Alert |
| **Active Buzzer** | **GPIO 5** | Direct (+) | Pulsing siren on Intruder Alert |

*All LED Cathodes (-) and Buzzer (-) connect to ESP32 GND rail.*

### 3. SG90 Door Servo & Reset Button
| Component | ESP32 Pin | Note |
|---|---|---|
| **Servo Signal** | **GPIO 13** | PWM control (0° Locked, 90° Open) |
| **Servo VCC** | 5V (or 3.3V) | Power rail |
| **Servo GND** | GND | Common ground |
| **Reset Button** | **GPIO 4** | Leg 1 to GPIO 4, Leg 2 to GND (`INPUT_PULLUP`) |

---

## 🎓 Grading Rubric Questions & Answers

### 1. Can you explain each tier in plain words?
- **The Brain**: OpenCV Haar Cascade detects the face region, equalizes brightness, and passes a $200 \times 200$ grayscale matrix to the LBPH classifier. If the mathematical texture pattern distance is below 68, it confirms the identity; otherwise, it marks an alert. It sends this decision via HTTP POST to the cloud.
- **The Cloud**: A FastAPI backend acting as the Single Source of Truth. It holds the current access state, maintains a security log, and provides `GET /state` for the ESP32 and a live HTML dashboard.
- **The Body**: An ESP32 that polls the cloud every 350ms, parses the JSON payload, drives the SSD1306 OLED display, switches the green/red LEDs, beeps the buzzer on alert, and turns the servo to unlock the door.

### 2. How does the system fail? (Failure Modes)
- **Photo spoofing**: LBPH looks at local 2D pixel contrasts. A high-resolution printed photo or phone screen holding an enrolled picture can trick a pure 2D recognizer because it lacks depth/liveness detection.
- **Extreme lighting differences**: Heavy shadows or backlight can distort the local binary patterns despite histogram equalization.
- **Pose angles**: Frontal Haar cascades lose detection accuracy if the subject turns their head beyond $\approx 35^\circ$.
- **Network drops**: If the Wi-Fi drops, the ESP32 retains its last state and attempts reconnection without hanging the main loop.
