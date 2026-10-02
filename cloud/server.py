"""
Face Recognition IoT Project - Cloud Backend (Single Source of Truth)
FastAPI server managing system access state, ESP32 endpoints, and web dashboard.
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from typing import List, Optional
import time
import uvicorn

app = FastAPI(title="Face Recognition Cloud Backend", version="1.0.0")

class ScanPayload(BaseModel):
    name: str = Field(..., description="Recognized person name or 'UNKNOWN'")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score 0.0 to 1.0")
    status: str = Field(default="authorized", description="'authorized', 'alert', or 'cleared'")

class SystemState(BaseModel):
    name: str = "--"
    status: str = "idle"  # "authorized", "alert", "cleared", "idle"
    confidence: float = 0.0
    door_open: bool = False
    led_green: int = 0
    led_red: int = 0
    buzzer: int = 0
    updated_at: float = 0.0
    history: List[dict] = []

# In-memory single source of truth
state = SystemState(updated_at=time.time())

@app.get("/state")
def get_state():
    """Endpoint polled by ESP32 (and fake_board.py) to read current scan state and actuation signals."""
    return {
        "name": state.name,
        "status": state.status,
        "confidence": round(state.confidence, 3),
        "door_open": state.door_open,
        "led_green": state.led_green,
        "led_red": state.led_red,
        "buzzer": state.buzzer,
        "history": state.history,
        "updated_at": state.updated_at
    }

@app.post("/scan")
def post_scan(payload: ScanPayload):
    """Endpoint used by the Brain (laptop vision) to submit face recognition scan results."""
    global state
    now = time.time()
    
    if payload.status == "alert" or payload.name.upper() in ["UNKNOWN", "INTRUDER", "UNRECOGNIZED"]:
        state.name = "UNKNOWN INTRUDER"
        state.status = "alert"
        state.confidence = payload.confidence
        state.door_open = False
        state.led_green = 0
        state.led_red = 1
        state.buzzer = 1
    elif payload.status == "authorized":
        state.name = payload.name
        state.status = "authorized"
        state.confidence = payload.confidence
        state.door_open = True
        state.led_green = 1
        state.led_red = 0
        state.buzzer = 0
    else:
        state.name = payload.name
        state.status = payload.status
        state.confidence = payload.confidence
        state.door_open = False
        state.led_green = 0
        state.led_red = 0
        state.buzzer = 0

    state.updated_at = now
    entry = {
        "name": state.name,
        "status": state.status,
        "confidence": round(state.confidence, 3),
        "door": "OPEN" if state.door_open else "LOCKED",
        "time": time.strftime("%H:%M:%S", time.localtime(now))
    }
    state.history.insert(0, entry)
    state.history = state.history[:15]  # keep last 15 entries
    return {"message": "State updated", "current": get_state()}

@app.post("/clear")
def clear_state():
    """Endpoint called when physical reset button is pressed or via dashboard UI."""
    global state
    state.name = "--"
    state.status = "cleared"
    state.confidence = 0.0
    state.door_open = False
    state.led_green = 0
    state.led_red = 0
    state.buzzer = 0
    state.updated_at = time.time()
    return {"message": "System state cleared", "current": get_state()}

@app.get("/", response_class=HTMLResponse)
def dashboard():
    """Live web dashboard showing the virtual OLED screen, access LEDs, door gate, and telemetry history."""
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>IoT Face Recognition - Access & Security Dashboard</title>
        <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700;800&family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
        <style>
            :root {
                --bg: #0d1117;
                --card-bg: #161b22;
                --border: #30363d;
                --text-main: #c9d1d9;
                --text-dim: #8b949e;
                --accent: #58a6ff;
                --oled-bg: #03080e;
                --oled-text: #00f0ff;
                --led-green-on: #2ea043;
                --led-red-on: #f85149;
                --led-off: #21262d;
            }
            body {
                margin: 0;
                padding: 24px;
                font-family: 'Inter', sans-serif;
                background-color: var(--bg);
                color: var(--text-main);
            }
            .container {
                max-width: 950px;
                margin: 0 auto;
            }
            header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                border-bottom: 1px solid var(--border);
                padding-bottom: 16px;
                margin-bottom: 24px;
            }
            h1 {
                margin: 0;
                font-size: 24px;
                font-weight: 700;
                color: #fff;
            }
            .badge {
                padding: 4px 10px;
                border-radius: 12px;
                font-size: 12px;
                font-weight: 600;
                text-transform: uppercase;
            }
            .badge-live {
                background: rgba(46, 160, 67, 0.2);
                color: #3fb950;
                border: 1px solid #3fb950;
            }
            .grid {
                display: grid;
                grid-template-columns: 1.1fr 0.9fr;
                gap: 20px;
                margin-bottom: 24px;
            }
            .card {
                background: var(--card-bg);
                border: 1px solid var(--border);
                border-radius: 8px;
                padding: 20px;
            }
            .card-title {
                font-size: 13px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                color: var(--text-dim);
                margin-bottom: 16px;
                font-weight: 600;
            }
            /* OLED simulation */
            .oled-screen {
                background: var(--oled-bg);
                border: 3px solid #30363d;
                border-radius: 6px;
                height: 150px;
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: center;
                font-family: 'JetBrains Mono', monospace;
                box-shadow: inset 0 0 15px rgba(0, 240, 255, 0.15);
                position: relative;
                text-align: center;
                padding: 10px;
            }
            .oled-title {
                position: absolute;
                top: 8px;
                font-size: 11px;
                letter-spacing: 1px;
                color: #58a6ff;
            }
            .oled-name {
                font-size: 28px;
                font-weight: 800;
                color: var(--oled-text);
                text-shadow: 0 0 10px rgba(0, 240, 255, 0.7);
                text-transform: uppercase;
                margin-top: 10px;
            }
            .oled-sub {
                position: absolute;
                bottom: 8px;
                font-size: 11px;
                color: #8b949e;
            }
            /* Hardware Rack */
            .hardware-rack {
                display: flex;
                justify-content: space-around;
                align-items: center;
                height: 150px;
                padding: 0 10px;
            }
            .hw-unit {
                display: flex;
                flex-direction: column;
                align-items: center;
                gap: 8px;
            }
            .led-bulb {
                width: 40px;
                height: 40px;
                border-radius: 50%;
                background: var(--led-off);
                border: 2px solid #30363d;
                transition: all 0.25s ease;
            }
            .led-bulb.green-active {
                background: #3fb950;
                border-color: #56d364;
                box-shadow: 0 0 20px rgba(63, 185, 80, 0.9);
            }
            .led-bulb.red-active {
                background: #f85149;
                border-color: #ff7b72;
                box-shadow: 0 0 20px rgba(248, 81, 73, 0.9);
                animation: pulse-red 0.6s infinite alternate;
            }
            @keyframes pulse-red {
                from { transform: scale(1.0); }
                to { transform: scale(1.08); box-shadow: 0 0 28px rgba(248, 81, 73, 1.0); }
            }
            .buzzer-box {
                width: 40px;
                height: 40px;
                border-radius: 8px;
                background: var(--led-off);
                border: 2px solid #30363d;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 20px;
                transition: all 0.25s ease;
            }
            .buzzer-box.buzz-active {
                background: #d29922;
                border-color: #e3b341;
                box-shadow: 0 0 20px rgba(210, 153, 34, 0.9);
                animation: shake 0.2s infinite;
            }
            @keyframes shake {
                0% { transform: translate(1px, 1px) rotate(0deg); }
                20% { transform: translate(-1px, -2px) rotate(-1deg); }
                40% { transform: translate(-2px, 0px) rotate(1deg); }
                60% { transform: translate(2px, 1px) rotate(0deg); }
                80% { transform: translate(1px, -1px) rotate(1deg); }
                100% { transform: translate(1px, 1px) rotate(0deg); }
            }
            .door-indicator {
                font-family: 'JetBrains Mono', monospace;
                font-size: 14px;
                font-weight: 700;
                padding: 6px 12px;
                border-radius: 6px;
                border: 1px solid #30363d;
                background: #21262d;
            }
            .door-indicator.open {
                background: rgba(46, 160, 67, 0.2);
                color: #3fb950;
                border-color: #3fb950;
            }
            .door-indicator.locked {
                background: rgba(248, 81, 73, 0.2);
                color: #f85149;
                border-color: #f85149;
            }
            .hw-label {
                font-family: 'JetBrains Mono', monospace;
                font-size: 11px;
                font-weight: 700;
                color: var(--text-dim);
            }
            .hw-sub {
                font-size: 10px;
                color: #58a6ff;
            }
            /* Action bar */
            .btn-clear {
                background: #21262d;
                border: 1px solid var(--border);
                color: #f85149;
                font-weight: 600;
                padding: 8px 16px;
                border-radius: 6px;
                cursor: pointer;
                transition: background 0.15s;
            }
            .btn-clear:hover {
                background: #30363d;
            }
            /* History table */
            table {
                width: 100%;
                border-collapse: collapse;
                font-size: 13px;
            }
            th, td {
                padding: 10px 12px;
                text-align: left;
                border-bottom: 1px solid var(--border);
            }
            th {
                color: var(--text-dim);
                font-weight: 600;
            }
            .pill {
                display: inline-block;
                padding: 2px 8px;
                border-radius: 10px;
                font-size: 11px;
                font-weight: 600;
            }
            .pill-authorized { background: rgba(46, 160, 67, 0.2); color: #3fb950; }
            .pill-alert { background: rgba(218, 54, 51, 0.2); color: #f85149; }
            .pill-cleared { background: rgba(139, 148, 158, 0.2); color: #8b949e; }
            .pill-idle { background: rgba(139, 148, 158, 0.2); color: #8b949e; }
        </style>
    </head>
    <body>
        <div class="container">
            <header>
                <div>
                    <h1>AI Face Recognition Cloud</h1>
                    <div style="font-size: 13px; color: var(--text-dim); margin-top: 4px;">AI + IoT Architecture · Access Control & Intruder Telemetry</div>
                </div>
                <div style="display: flex; gap: 12px; align-items: center;">
                    <span class="badge badge-live">Live Sync</span>
                    <button class="btn-clear" onclick="clearBoard()">Reset System</button>
                </div>
            </header>

            <div class="grid">
                <!-- Virtual OLED Display -->
                <div class="card">
                    <div class="card-title">Virtual OLED (SSD1306 128x64)</div>
                    <div class="oled-screen">
                        <div class="oled-title">AI FACE MONITOR</div>
                        <div class="oled-name" id="oledName">--</div>
                        <div class="oled-sub" id="oledSub">STATUS: IDLE SCANNER</div>
                    </div>
                </div>

                <!-- Hardware Actuators -->
                <div class="card">
                    <div class="card-title">ESP32 Actuators & Indicators</div>
                    <div class="hardware-rack">
                        <div class="hw-unit">
                            <div class="led-bulb" id="ledGreen"></div>
                            <span class="hw-label">GREEN LED</span>
                            <span class="hw-sub">GPIO 18</span>
                        </div>
                        <div class="hw-unit">
                            <div class="led-bulb" id="ledRed"></div>
                            <span class="hw-label">RED LED</span>
                            <span class="hw-sub">GPIO 19</span>
                        </div>
                        <div class="hw-unit">
                            <div class="buzzer-box" id="buzzerIcon">🔊</div>
                            <span class="hw-label">BUZZER</span>
                            <span class="hw-sub">GPIO 5</span>
                        </div>
                        <div class="hw-unit">
                            <div class="door-indicator locked" id="doorGate">LOCKED (0°)</div>
                            <span class="hw-label">SERVO GATE</span>
                            <span class="hw-sub">GPIO 13</span>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Access History Log -->
            <div class="card">
                <div class="card-title">Real-time Recognition & Security Telemetry Log</div>
                <table>
                    <thead>
                        <tr>
                            <th>Time</th>
                            <th>Person / Subject</th>
                            <th>Status</th>
                            <th>Confidence</th>
                            <th>Door Servo</th>
                        </tr>
                    </thead>
                    <tbody id="historyBody">
                        <tr><td colspan="5" style="text-align: center; color: var(--text-dim);">No scans recorded yet. Look into the camera!</td></tr>
                    </tbody>
                </table>
            </div>
        </div>

        <script>
            async function updateUI() {
                try {
                    const res = await fetch('/state');
                    const data = await res.json();
                    
                    const oledName = document.getElementById('oledName');
                    const oledSub = document.getElementById('oledSub');
                    const ledGreen = document.getElementById('ledGreen');
                    const ledRed = document.getElementById('ledRed');
                    const buzzer = document.getElementById('buzzerIcon');
                    const doorGate = document.getElementById('doorGate');

                    oledName.innerText = data.name;
                    if (data.status === 'authorized') {
                        oledSub.innerText = `ACCESS GRANTED (${Math.round(data.confidence * 100)}%)`;
                        oledName.style.color = '#3fb950';
                    } else if (data.status === 'alert') {
                        oledSub.innerText = `SECURITY ALERT! (< 60% CONF)`;
                        oledName.style.color = '#f85149';
                    } else {
                        oledSub.innerText = `STATUS: READY & SCANNING`;
                        oledName.style.color = '#8b949e';
                    }

                    // Green LED
                    if (data.led_green === 1) {
                        ledGreen.classList.add('green-active');
                    } else {
                        ledGreen.classList.remove('green-active');
                    }

                    // Red LED
                    if (data.led_red === 1) {
                        ledRed.classList.add('red-active');
                    } else {
                        ledRed.classList.remove('red-active');
                    }

                    // Buzzer
                    if (data.buzzer === 1) {
                        buzzer.classList.add('buzz-active');
                    } else {
                        buzzer.classList.remove('buzz-active');
                    }

                    // Door Servo
                    if (data.door_open) {
                        doorGate.innerText = "UNLOCKED (90°)";
                        doorGate.className = "door-indicator open";
                    } else {
                        doorGate.innerText = "LOCKED (0°)";
                        doorGate.className = "door-indicator locked";
                    }

                    // Update History Table
                    const tbody = document.getElementById('historyBody');
                    if (tbody) {
                        if (data.history && data.history.length > 0) {
                            tbody.innerHTML = data.history.map(item => `
                                <tr>
                                    <td>${item.time}</td>
                                    <td style="font-size: 15px; font-weight: 700; color: ${item.status === 'authorized' ? '#58a6ff' : '#f85149'};">${item.name}</td>
                                    <td><span class="pill pill-${item.status}">${item.status.toUpperCase()}</span></td>
                                    <td>${Math.round(item.confidence * 100)}%</td>
                                    <td><span style="font-family: monospace; font-weight: 700; color: ${item.door === 'OPEN' ? '#3fb950' : '#8b949e'};">${item.door}</span></td>
                                </tr>
                            `).join('');
                        } else {
                            tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: var(--text-dim);">No scans recorded yet. Look into the camera!</td></tr>`;
                        }
                    }
                } catch (e) {
                    console.error("Poll error:", e);
                }
            }

            async function clearBoard() {
                await fetch('/clear', { method: 'POST' });
                updateUI();
            }

            setInterval(updateUI, 350);
            updateUI();
        </script>
    </body>
    </html>
    """
    return HTMLResponse(
        content=html_content,
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )

if __name__ == "__main__":
    print("Starting Face Recognition Cloud Server on http://0.0.0.0:8000 ...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
