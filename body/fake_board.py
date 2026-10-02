"""
Face Recognition IoT Project - Fake Body (ESP32 Hardware Simulator)
Simulates what the physical ESP32, OLED Display, Access LEDs, Buzzer, and Door Servo
would do in your terminal before wiring physical hardware in the lab!

Controls:
  - Type 'c' + Enter to simulate pressing the physical reset/lock button on GPIO 4.
"""

import time
import requests
import sys
import threading

SERVER_URL = "http://localhost:8000"

def draw_board(name: str, status: str, confidence: float, door_open: bool, led_g: int, led_r: int, buzzer: int):
    """Render an ASCII representation of the SSD1306 OLED and hardware actuators."""
    green_icon = "[ON  *GREEN* ]" if led_g else "[    OFF     ]"
    red_icon   = "[ON  *RED*   ]" if led_r else "[    OFF     ]"
    buzz_icon  = "[🔊 BEEPING! ]" if buzzer else "[   SILENT   ]"
    door_str   = "UNLOCKED (90°)" if door_open else "LOCKED   ( 0°)"

    if status == "authorized":
        status_line = f"ACCESS GRANTED ({int(confidence * 100)}%)"
        disp_name = f">> {name.upper()} <<"
    elif status == "alert":
        status_line = "! INTRUDER ALERT !"
        disp_name = "** ACCESS DENIED **"
    elif status == "cleared":
        status_line = "SYSTEM RESET / LOCKED"
        disp_name = "-- IDLE --"
    else:
        status_line = "SCANNING FOR FACES..."
        disp_name = "-- READY --"

    print("\n" + "=" * 60)
    print("      VIRTUAL ESP32 FACE RECOGNITION TERMINAL (TIER 3)      ")
    print("=" * 60)
    print(" +--------------------------------------------------------+")
    print(" |                 AI FACE MONITOR (128x64)               |")
    print(" |                                                        |")
    print(f" |             {disp_name:^40}           |")
    print(" |                                                        |")
    print(f" |             {status_line:^40}           |")
    print(" +--------------------------------------------------------+")
    print("    GREEN LED (GPIO 18)          RED LED (GPIO 19)          ")
    print(f"     {green_icon:^18}          {red_icon:^18}     ")
    print("-" * 60)
    print("    BUZZER (GPIO 5)              SERVO DOOR (GPIO 13)       ")
    print(f"     {buzz_icon:^18}          [ {door_str:^14} ]     ")
    print("=" * 60)
    print(" [Simulate Hardware Button] Type 'c' and hit Enter to LOCK/CLEAR.")
    print("=" * 60 + "\n")

def input_listener():
    """Listen for user pressing 'c' to simulate physical button on GPIO 4."""
    while True:
        try:
            cmd = input().strip().lower()
            if cmd == 'c':
                print(">> [BUTTON TRIGGERED] Sending physical reset signal to cloud...")
                try:
                    requests.post(f"{SERVER_URL}/clear", timeout=1.0)
                except Exception as e:
                    print(f"Failed to send clear: {e}")
        except (EOFError, KeyboardInterrupt):
            break

def main():
    print("Starting Fake ESP32 Face Access Simulator...")
    print(f"Connecting to Cloud Backend at {SERVER_URL} ...")

    # Start button listener thread
    t = threading.Thread(target=input_listener, daemon=True)
    t.start()

    last_name = None
    last_status = None
    last_door = None

    while True:
        try:
            resp = requests.get(f"{SERVER_URL}/state", timeout=2.0)
            if resp.status_code == 200:
                data = resp.json()
                cur_name = data.get("name", "--")
                cur_status = data.get("status", "idle")
                conf = data.get("confidence", 0.0)
                door_open = data.get("door_open", False)
                led_g = data.get("led_green", 0)
                led_r = data.get("led_red", 0)
                buzzer = data.get("buzzer", 0)

                if (cur_name != last_name or cur_status != last_status or door_open != last_door):
                    draw_board(cur_name, cur_status, conf, door_open, led_g, led_r, buzzer)
                    last_name = cur_name
                    last_status = cur_status
                    last_door = door_open
            else:
                print(f"[Fake Board] Warning: Server returned HTTP {resp.status_code}")
        except requests.exceptions.ConnectionError:
            print("[Fake Board] Waiting for Cloud Server (server.py) to start...", end="\r")
        except Exception as e:
            print(f"[Fake Board] Error: {e}")

        time.sleep(0.35)

if __name__ == "__main__":
    main()
